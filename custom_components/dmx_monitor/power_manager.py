"""Dormant Power Manager contracts.

This module is deliberately isolated from Show Network's monitoring/control
runtime.  It defines the future power-control model and output backends, but
NEVER opens a socket/serial port or registers a Home Assistant service while
Power Manager is disabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

ENABLED = False


class PowerOutput(StrEnum):
    """Future output transport for the Power Manager only."""

    SACN = "sacn"
    ARTNET = "artnet"
    ENTTEC = "enttec"


@dataclass(frozen=True, slots=True)
class PowerOutputConfig:
    """Configuration contract for a future Power Manager output.

    This is intentionally separate from the receive-only DMX monitor.  No
    implementation is selected automatically and no output is sent here.
    """

    output: PowerOutput
    universe: int = 1
    host: str = ""
    port: int | None = None
    enttec_device: str = ""
    priority: int = 100
    source_name: str = "Show Network Power Manager"

    def __post_init__(self) -> None:
        if not 1 <= self.universe <= 63999:
            raise ValueError("universe must be 1..63999")
        if not 1 <= self.priority <= 200:
            raise ValueError("sACN priority must be 1..200")
        if self.port is not None and not 1 <= self.port <= 65535:
            raise ValueError("port must be 1..65535")
        if self.output in (PowerOutput.SACN, PowerOutput.ARTNET) and not self.host.strip():
            raise ValueError("host is required for network DMX output")
        if self.output is PowerOutput.ENTTEC and not self.enttec_device.strip():
            raise ValueError("enttec_device is required for ENTTEC output")


@dataclass(frozen=True, slots=True)
class PowerChannel:
    channel: int
    name: str = ""
    on_value: int = 255
    off_value: int = 0
    on_delay_s: float = 0.0
    off_delay_s: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.channel <= 512:
            raise ValueError("DMX channel must be 1..512")
        if not 0 <= self.on_value <= 255 or not 0 <= self.off_value <= 255:
            raise ValueError("DMX values must be 0..255")
        if self.on_delay_s < 0 or self.off_delay_s < 0:
            raise ValueError("delays cannot be negative")


@dataclass(frozen=True, slots=True)
class PowerSequence:
    """A future sequenced power preset, independent of monitored DMX."""

    universe: int
    channels: tuple[PowerChannel, ...] = field(default_factory=tuple)
    output: PowerOutputConfig | None = None
    enabled: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.universe <= 63999:
            raise ValueError("universe must be a positive sACN/Art-Net universe")
        if len({c.channel for c in self.channels}) != len(self.channels):
            raise ValueError("duplicate DMX channel")
        if self.output is not None and self.output.universe != self.universe:
            raise ValueError("output universe must match sequence universe")

    @property
    def active(self) -> bool:
        return ENABLED and self.enabled


def available_outputs() -> tuple[PowerOutput, ...]:
    """Return future output choices without touching any hardware/network."""
    return tuple(PowerOutput)

class PowerOutputPipeline:
    """Dormant latest-value output buffer for future Power Manager transport.

    A power frame is state, not an event: if several updates arrive while the
    transport is busy, only the newest frame is retained.  One worker is used;
    no task is created per DMX update.  This class never opens a network or
    serial resource by itself.
    """

    def __init__(self, sender, interval_s: float = 0.05) -> None:
        import asyncio
        self.sender = sender
        self.interval_s = max(0.02, float(interval_s))
        self._latest: bytes | None = None
        self._task = None
        self._stopping = False
        self.received = 0
        self.coalesced = 0
        self.sent = 0
        self.errors = 0

    def push_nowait(self, frame: bytes) -> None:
        import asyncio
        if self._stopping:
            return
        frame = bytes(frame[:512]).ljust(512, b"\0")
        self.received += 1
        if self._latest is not None:
            self.coalesced += 1
        self._latest = frame
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="show-network-power-output")

    async def _worker(self) -> None:
        while self._latest is not None and not self._stopping:
            frame = self._latest
            self._latest = None
            result = None
            try:
                result = self.sender(frame)
                if asyncio.iscoroutine(result):
                    await result
                self.sent += 1
            except asyncio.CancelledError:
                if asyncio.iscoroutine(result):
                    result.close()
                raise
            except Exception:
                self.errors += 1
            if self._latest is not None and not self._stopping:
                await asyncio.sleep(self.interval_s)

    async def async_stop(self) -> None:
        import asyncio
        self._stopping = True
        self._latest = None
        task = self._task
        self._task = None
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def snapshot(self) -> dict[str, int]:
        return {"received": self.received, "coalesced": self.coalesced, "sent": self.sent, "errors": self.errors}
