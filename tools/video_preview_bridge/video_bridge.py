"""Show Network external video preview bridge.

WHY THIS EXISTS
----------------
Neither NDI nor raw SMPTE ST 2110 video is browser-playable as-is (NDI needs
the proprietary NDI SDK; ST 2110 is uncompressed and not something a
<video>/<img> tag understands). Show Network's video_ip_supervision.py
deliberately never fabricates a preview URL for either. This script is the
*separate, external* piece that can legitimately produce one: it runs one
ffmpeg subprocess per configured source, captures whatever MJPEG output
that ffmpeg command produces, and re-serves it as a plain HTTP MJPEG stream
that any browser (and Show Network's set_preview_uri()) can use directly.

WHAT IS TESTED vs. WHAT IS NOT (read this before trusting a config)
---------------------------------------------------------------------
This file's own logic -- subprocess supervision with backoff, MJPEG frame
splitting/re-serving over HTTP, the /status JSON endpoint -- was tested
end-to-end using ffmpeg's synthetic `testsrc` generator, which needs no
special hardware or SDK. That plumbing works.

What was NOT tested, because doing so requires hardware/software this
environment does not have:
  - Actual NDI capture. Standard ffmpeg builds do NOT include NDI support
    (verified: a stock ffmpeg 6.1.1 here has no libndi_newtek). Capturing a
    real NDI source requires either an ffmpeg build compiled with the NDI
    SDK (several community build scripts exist; search "ffmpeg NDI build"),
    or a different capture tool entirely (e.g. GStreamer's ndisrc plugin).
    The example command below is written from public documentation of how
    such a build's -f libndi_newtek input is normally invoked, but it has
    not been run against a real NDI source here -- validate it yourself.
  - Actual SMPTE ST 2110 / RFC 4175 raw-video RTP decoding. Vanilla ffmpeg
    has no built-in RFC 4175 depacketizer as far as could be confirmed here;
    GStreamer (with the appropriate SMPTE/RTP plugins) is generally the more
    capable tool for this specific job. Treat the ST 2110 example command as
    a starting point to adapt, not a verified working command.

Every command in the config is exactly what you provide -- this script
never constructs or guesses an ffmpeg command line itself.

CONFIG FORMAT (JSON)
---------------------
{
  "http_host": "0.0.0.0",
  "http_port": 8090,
  "targets": [
    {
      "key": "ndi:CAM 1 (OBS)",
      "capture_cmd": ["ffmpeg", "-f", "libndi_newtek", "-i", "CAM 1 (OBS)",
                       "-r", "5", "-q:v", "5", "-f", "mjpeg", "-"],
      "restart_backoff_s": 3.0
    },
    {
      "key": "st2110:239.1.1.3:20000",
      "capture_cmd": ["ffmpeg", "-i", "rtp://239.1.1.3:20000",
                       "-r", "5", "-q:v", "5", "-f", "mjpeg", "-"],
      "restart_backoff_s": 3.0
    }
  ]
}

``key`` must exactly match the ``key`` field Show Network's
video_ip_supervision.py already assigned that source (visible in its
snapshot's ``video_ip_sources`` rows) -- this is how set_preview_uri()
knows which source a given preview belongs to.

USAGE
------
    python3 video_bridge.py --config bridge_config.json

Then, from Show Network (or any poller), GET http://<host>:<port>/status
and, for every healthy target, call:
    video_ip_supervision.set_preview_uri(
        key, f"http://<host>:<port>/preview/{quote(key)}",
        bridge_name="external_bridge:ffmpeg",
    )
video_ip_supervision.py already ships a ready-to-use poller for exactly
this -- see async_poll_preview_bridge() in that module.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

_LOGGER = logging.getLogger("video_preview_bridge")

_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"
_MAX_FRAME_BYTES = 8 * 1024 * 1024
_MIN_STABLE_UPTIME_S = 5.0


@dataclass
class BridgeTarget:
    key: str
    capture_cmd: list[str]
    restart_backoff_s: float = 3.0

    # -- runtime state -----------------------------------------------------
    process: asyncio.subprocess.Process | None = field(default=None, compare=False)
    task: asyncio.Task | None = field(default=None, compare=False)
    last_frame: bytes | None = field(default=None, compare=False)
    last_frame_at: float | None = field(default=None, compare=False)
    restarts: int = field(default=0, compare=False)
    last_error: str | None = field(default=None, compare=False)
    subscribers: set[asyncio.Queue] = field(default_factory=set, compare=False)

    def status(self, now: float) -> dict[str, Any]:
        age = None if self.last_frame_at is None else max(0.0, now - self.last_frame_at)
        return {
            "key": self.key,
            "running": self.process is not None and self.process.returncode is None,
            "restarts": self.restarts,
            "last_error": self.last_error,
            "last_frame_age_s": None if age is None else round(age, 1),
            "healthy": age is not None and age < 10.0,
            "subscriber_count": len(self.subscribers),
        }


async def _read_mjpeg_frames(stream: asyncio.StreamReader):
    """Yield complete JPEG frames from an ffmpeg -f mjpeg stdout stream."""
    buf = bytearray()
    while True:
        chunk = await stream.read(65536)
        if not chunk:
            return
        buf.extend(chunk)
        if len(buf) > _MAX_FRAME_BYTES:
            # Runaway/garbage stream: drop what we have and resync on the
            # next SOI rather than growing forever.
            _LOGGER.warning("MJPEG buffer exceeded safety limit, resyncing")
            buf.clear()
            continue
        while True:
            start = buf.find(_JPEG_SOI)
            if start < 0:
                buf.clear()
                break
            end = buf.find(_JPEG_EOI, start + 2)
            if end < 0:
                if start > 0:
                    del buf[:start]
                break
            frame = bytes(buf[start:end + 2])
            del buf[:end + 2]
            yield frame


class VideoPreviewBridge:
    def __init__(self, targets: list[BridgeTarget]) -> None:
        self.targets: dict[str, BridgeTarget] = {t.key: t for t in targets}
        self._stopping = False

    async def start(self) -> None:
        self._stopping = False
        for target in self.targets.values():
            target.task = asyncio.create_task(self._supervise(target), name=f"preview-bridge-{target.key}")

    async def stop(self) -> None:
        self._stopping = True
        for target in self.targets.values():
            if target.task:
                target.task.cancel()
            if target.process and target.process.returncode is None:
                target.process.kill()
        for target in self.targets.values():
            if target.task:
                await asyncio.gather(target.task, return_exceptions=True)

    async def _supervise(self, target: BridgeTarget) -> None:
        while not self._stopping:
            started_at = time.monotonic()
            try:
                target.process = await asyncio.create_subprocess_exec(
                    *target.capture_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                target.last_error = None
                assert target.process.stdout is not None
                async for frame in _read_mjpeg_frames(target.process.stdout):
                    target.last_frame = frame
                    target.last_frame_at = time.time()
                    for queue in list(target.subscribers):
                        if not queue.full():
                            queue.put_nowait(frame)
                await target.process.wait()
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001 -- must never kill the supervisor loop
                target.last_error = str(exc)
            finally:
                if target.process and target.process.returncode is None:
                    target.process.kill()
            if self._stopping:
                return
            target.restarts += 1
            uptime = time.monotonic() - started_at
            backoff = target.restart_backoff_s if uptime < _MIN_STABLE_UPTIME_S else 0.5
            _LOGGER.warning("Capture for %s exited, restarting in %.1fs (uptime was %.1fs)", target.key, backoff, uptime)
            await asyncio.sleep(backoff)

    def status_snapshot(self) -> dict[str, Any]:
        now = time.time()
        return {"targets": [t.status(now) for t in self.targets.values()]}


# ---------------------------------------------------------------------------
# Minimal HTTP server (stdlib-only: no extra dependency for a small bridge)
# ---------------------------------------------------------------------------

async def _handle_client(bridge: VideoPreviewBridge, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not line or line in (b"\r\n", b"\n"):
                break
        try:
            method, path, _version = request_line.decode("ascii", "replace").split()
        except ValueError:
            writer.close()
            return

        if method != "GET":
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            return

        if path == "/status":
            body = json.dumps(bridge.status_snapshot()).encode("utf-8")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
            )
            await writer.drain()
            return

        if path.startswith("/preview/"):
            key = unquote(path[len("/preview/"):])
            target = bridge.targets.get(key)
            if target is None:
                writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                return
            queue: asyncio.Queue = asyncio.Queue(maxsize=2)
            target.subscribers.add(queue)
            boundary = b"show-network-frame"
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: multipart/x-mixed-replace; boundary=" + boundary + b"\r\n"
                b"Cache-Control: no-cache\r\nConnection: close\r\n\r\n"
            )
            await writer.drain()
            try:
                if target.last_frame is not None:
                    await queue.put(target.last_frame)
                while True:
                    frame = await queue.get()
                    writer.write(
                        b"--" + boundary + b"\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
                    )
                    await writer.drain()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                target.subscribers.discard(queue)
            return

        writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
    except (asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def async_main(config_path: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    targets = [
        BridgeTarget(key=t["key"], capture_cmd=list(t["capture_cmd"]), restart_backoff_s=float(t.get("restart_backoff_s", 3.0)))
        for t in raw.get("targets", [])
    ]
    if not targets:
        _LOGGER.warning("No targets configured in %s; nothing to bridge", config_path)

    bridge = VideoPreviewBridge(targets)
    await bridge.start()

    host = raw.get("http_host", "0.0.0.0")
    port = int(raw.get("http_port", 8090))
    server = await asyncio.start_server(lambda r, w: _handle_client(bridge, r, w), host, port)
    _LOGGER.info("Video preview bridge listening on %s:%s (%d target(s))", host, port, len(targets))

    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Show Network external video preview bridge")
    parser.add_argument("--config", required=True, help="Path to a JSON config file (see module docstring)")
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args.config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
