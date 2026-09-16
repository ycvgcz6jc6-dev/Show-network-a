"""Opt-in low-bandwidth video preview for the Show Network panel.

This is deliberately not a Home Assistant camera/sensor platform. A media
subscription is created only while an authenticated user has a preview open.
The stream is downscaled and rate-limited before being returned as MJPEG.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from urllib.parse import unquote

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
            while True:
                chunk = await proc.stdout.read(16384)
                if not chunk:
                    break
                await response.write(chunk)
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
