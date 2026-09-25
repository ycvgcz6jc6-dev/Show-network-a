"""Opt-in low-bandwidth video preview for the Show Network panel.

This is deliberately not a Home Assistant camera/sensor platform. A media
subscription is created only while an authenticated user has a preview open.
The stream is downscaled and rate-limited before being returned as MJPEG.

SECURITY/RESOURCE fix (audit Z-08): the stream loop previously ran forever
until the client disconnected or ffmpeg exited on its own -- no maximum
session duration, no idle/stall timeout, no data cap. A forgotten-open
browser tab, or a source that stalls without ever closing the connection,
could keep an ffmpeg process (and its CPU/bandwidth) running indefinitely.
Both a hard session-duration cap and a per-read idle timeout are now
enforced; either one cleanly stops the stream and terminates ffmpeg.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from urllib.parse import unquote

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Hard cap on how long a single preview session may run, regardless of
# activity -- prevents a forgotten-open tab from streaming indefinitely.
MAX_SESSION_S = 900.0  # 15 minutes
# If no new data arrives from ffmpeg within this window, treat the source
# as stalled/dead and stop -- prevents a hung read() from blocking the
# session slot (and the per-entry lock) forever.
IDLE_TIMEOUT_S = 15.0


async def stream_preview_frames(proc_stdout, response_write, *, max_session_s: float = MAX_SESSION_S, idle_timeout_s: float = IDLE_TIMEOUT_S) -> dict:
    """Pump chunks from ``proc_stdout.read(n)`` to ``response_write(chunk)``
    until EOF, the session duration cap, or the idle timeout is hit.

    Factored out from the view so the duration/idle-timeout logic can be
    tested without needing a real aiohttp response or ffmpeg process (see
    the test suite this was validated against).  Returns a small summary
    dict for logging/diagnostics.
    """
    started = time.monotonic()
    bytes_sent = 0
    chunks_sent = 0
    stop_reason = "eof"
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= max_session_s:
            stop_reason = "max_session_duration"
            break
        remaining = max_session_s - elapsed
        try:
            chunk = await asyncio.wait_for(proc_stdout.read(16384), timeout=min(idle_timeout_s, remaining))
        except asyncio.TimeoutError:
            # A short residual `remaining` near the session boundary can
            # trigger this even when the source is fine (it just didn't
            # finish a read within the last sliver of session time left) --
            # only call it a genuine idle stall if we are NOT already at
            # the duration cap.
            if time.monotonic() - started >= max_session_s:
                stop_reason = "max_session_duration"
            else:
                stop_reason = "idle_timeout"
            break
        if not chunk:
            stop_reason = "eof"
            break
        await response_write(chunk)
        bytes_sent += len(chunk)
        chunks_sent += 1
    return {"stop_reason": stop_reason, "bytes_sent": bytes_sent, "chunks_sent": chunks_sent, "duration_s": time.monotonic() - started}


class VideoIPPreviewView(HomeAssistantView):
    url = "/api/dmx_monitor/video_ip_preview"
    name = "api:dmx_monitor:video_ip_preview"
    requires_auth = True

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass = request.app["hass"]
        entry_id = str(request.query.get("entry_id") or "")
        key = unquote(str(request.query.get("key") or ""))
        if not entry_id or not key:
            raise web.HTTPBadRequest(text="entry_id and key are required")

        values = hass.data.get(DOMAIN, {}).get(entry_id)
        coordinator = values.get("coordinator") if isinstance(values, dict) else None
        if coordinator is None:
            raise web.HTTPNotFound(text="Show Network entry not found")
        supervision = coordinator.video_ip_supervision
        if not supervision.enabled:
            raise web.HTTPForbidden(text="Video IP supervision is disabled")
        if not supervision.preview_enabled:
            raise web.HTTPForbidden(text="Low-quality preview is disabled in Show Network options")

        endpoint = supervision.endpoint(key)
        if endpoint is None or not endpoint.uri:
            raise web.HTTPNotFound(text="No playable URI for this endpoint")
        if endpoint.protocol not in {"RTSP", "SRT", "HTTP", "HTTPS"}:
            raise web.HTTPBadRequest(text="This protocol has no direct low-quality preview")
        if not supervision._interface_accepts(endpoint.host):
            raise web.HTTPForbidden(text="Endpoint is outside the selected Video IP network interface")

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise web.HTTPServiceUnavailable(text="ffmpeg is not available in this Home Assistant runtime")

        locks = hass.data.setdefault(f"{DOMAIN}_video_preview_locks", {})
        lock = locks.setdefault(entry_id, asyncio.Lock())
        if lock.locked():
            raise web.HTTPTooManyRequests(text="A low-quality preview is already active for this Show Network entry")

        await lock.acquire()
        args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
        if endpoint.protocol == "RTSP":
            args += ["-rtsp_transport", "tcp"]
        args += [
            "-i", endpoint.uri,
            "-an", "-sn", "-dn",
            "-vf", "scale=640:-2:force_original_aspect_ratio=decrease,fps=5",
            "-q:v", "12",
            "-f", "mpjpeg",
            "-boundary_tag", "frame",
            "pipe:1",
        ]
        proc = None
        response = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "multipart/x-mixed-replace; boundary=frame",
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "X-Show-Network-Preview": "low-quality",
                },
            )
            await response.prepare(request)
            assert proc.stdout is not None
            summary = await stream_preview_frames(proc.stdout, response.write)
            if summary["stop_reason"] in ("max_session_duration", "idle_timeout"):
                _LOGGER.info(
                    "Video IP preview for %s stopped (%s) after %.0fs, %d bytes",
                    key, summary["stop_reason"], summary["duration_s"], summary["bytes_sent"],
                )
            return response
        except asyncio.CancelledError:
            raise
        except (ConnectionResetError, BrokenPipeError):
            return response if response is not None else web.Response(status=499)
        except Exception as err:
            _LOGGER.debug("Video IP preview ended: %s", err)
            if request.transport is None or request.transport.is_closing():
                return web.Response(status=499)
            raise
        finally:
            if proc is not None and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            lock.release()


def async_register(hass) -> None:
    key = f"{DOMAIN}_video_preview_registered"
    if hass.data.get(key):
        return
    hass.http.register_view(VideoIPPreviewView)
    hass.data[key] = True
