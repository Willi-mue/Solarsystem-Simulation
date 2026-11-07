"""Wiedergabe-Steuerung: Pause und Simulationsgeschwindigkeit. Ohne GUI."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config


@dataclass
class Playback:
    paused: bool = False
    speed_index: int = field(
        default_factory=lambda: config.SPEEDS_MINUTES.index(config.DEFAULT_SPEED_MINUTES)
    )

    @property
    def minutes_per_frame(self) -> int:
        return config.SPEEDS_MINUTES[self.speed_index]

    @property
    def seconds_per_frame(self) -> float:
        return self.minutes_per_frame * 60.0

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def faster(self) -> None:
        self.speed_index = min(self.speed_index + 1, len(config.SPEEDS_MINUTES) - 1)

    def slower(self) -> None:
        self.speed_index = max(self.speed_index - 1, 0)
