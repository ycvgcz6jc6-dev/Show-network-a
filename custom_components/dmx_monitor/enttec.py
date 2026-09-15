"""Receive-only ENTTEC DMX USB input support.

Supports the documented DMX USB PRO serial protocol for DMX input. This module
never sends DMX or RDM packets. It only sends the documented receive-mode
configuration request (label 8) so the interface reports incoming DMX frames.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import logging
from time import monotonic

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    serial = None
    list_ports = None

_LOGGER = logging.getLogger(__name__)
START = 0x7E
END = 0xE7
LABEL_RECEIVED_DMX = 5
LABEL_RECEIVE_ON_CHANGE = 8
LABEL_GET_SERIAL = 10

@dataclass(frozen=True)
class EnttecPort:
    device: str
    description: str
    manufacturer: str | None = None
    serial_number: str | None = None
    vid: int | None = None
    pid: int | None = None


def discover_ports() -> list[EnttecPort]:
    if list_ports is None:
        return []
    result: list[EnttecPort] = []
    for p in list_ports.comports():
        text = " ".join(x for x in (p.manufacturer, p.description, p.product) if x)
        # Do not require an FTDI VID: some adapters expose generic USB strings.
        if "enttec" in text.lower() or p.vid in {0x0403}:
            result.append(EnttecPort(p.device, p.description or p.device, p.manufacturer, p.serial_number, p.vid, p.pid))
    return result


def _frame(label: int, payload: bytes = b"") -> bytes:
    length = len(payload)
    return bytes((START, label, length & 0xFF, (length >> 8) & 0xFF)) + payload + bytes((END,))


class EnttecDmxInput:
    """Single-universe receive-only ENTTEC DMX USB input."""

    def __init__(self, device: str, model: str = "auto", on_frame=None) -> None:
        self.device = device
        self.model = model
        self._serial = None
        self._task: asyncio.Task | None = None
        self._callback_task: asyncio.Task | None = None
        self._pending_callback: bytes | None = None
        self._buffer = bytearray()
        self.values = bytes(512)
        self.valid = False
        self.error_flags = 0
        self.frames = 0
        self.last_frame = None
        self.last_update = None
        self.serial_number = None
        self.connected = False
        self.on_frame = on_frame

    async def start(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is required for ENTTEC DMX USB input")
        try:
            self._serial = await asyncio.to_thread(serial.Serial, self.device, 57600, timeout=0.2)
            self.connected = True
            # Label 8 is the documented receive-mode request. It does not transmit
            # DMX/RDM on the 5-pin output; it configures the widget to report input.
            await asyncio.to_thread(self._serial.write, _frame(LABEL_RECEIVE_ON_CHANGE, b"\x00"))
            self._task = asyncio.create_task(self._reader(), name=f"enttec-dmx-{self.device}")
        except Exception:
            await self.stop()
            raise

    async def stop(self) -> None:
        for task_name in ("_task", "_callback_task"):
            task = getattr(self, task_name)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
                setattr(self, task_name, None)
        self._pending_callback = None
        if self._serial:
            await asyncio.to_thread(self._serial.close)
            self._serial = None
        self.connected = False

    async def _reader(self) -> None:
        while True:
            chunk = await asyncio.to_thread(self._serial.read, 1024)
            if chunk:
                self._buffer.extend(chunk)
                self._parse()

    def _parse(self) -> None:
        while True:
            try:
                start = self._buffer.index(START)
            except ValueError:
                self._buffer.clear()
                return
            if start:
                del self._buffer[:start]
            if len(self._buffer) < 5:
                return
            label = self._buffer[1]
            length = self._buffer[2] | (self._buffer[3] << 8)
            total = 5 + length
            if len(self._buffer) < total:
                return
            if self._buffer[total - 1] != END:
                del self._buffer[0]
                continue
            payload = bytes(self._buffer[4:4 + length])
            del self._buffer[:total]
            if label == LABEL_RECEIVED_DMX:
                self._consume_dmx(payload)
            elif label == LABEL_GET_SERIAL and len(payload) >= 4:
                self.serial_number = int.from_bytes(payload[:4], "little")

    def _consume_dmx(self, payload: bytes) -> None:
        if not payload:
            return
        self.error_flags = payload[0]
        if self.error_flags:
            self.valid = False
            return
        dmx = payload[1:513]
        self.values = bytes(dmx) + bytes(max(0, 512 - len(dmx)))
        self.valid = True
        self.frames += 1
        self.last_frame = monotonic()
        self.last_update = self.last_frame
        if self.on_frame:
            # Async callbacks are coalesced to one latest-value worker so a
            # slow consumer cannot create one task per incoming DMX frame.
            self._pending_callback = self.values
            if self._callback_task is None or self._callback_task.done():
                self._callback_task = asyncio.create_task(
                    self._callback_worker(), name=f"enttec-callback-{self.device}"
                )

    async def _callback_worker(self) -> None:
        while self._pending_callback is not None:
            values = self._pending_callback
            self._pending_callback = None
            result = self.on_frame(values) if self.on_frame else None
            if asyncio.iscoroutine(result):
                await result

    def snapshot(self) -> dict:
        return {
            "enttec_connected": self.connected,
            "enttec_device": self.device,
            "enttec_model": self.model,
            "enttec_frames": self.frames,
            "enttec_valid": self.valid,
            "enttec_error_flags": self.error_flags,
            "enttec_serial_number": self.serial_number,
            "enttec_active_channels": sum(1 for v in self.values if v),
            "enttec_values": self.values,
        }
