"""Command execution models for diagnostics runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out
