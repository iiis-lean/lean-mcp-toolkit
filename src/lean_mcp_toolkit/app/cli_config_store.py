"""User-scoped config store for lean-cli-toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_BASE_URL = "http://127.0.0.1:18080"
DEFAULT_API_PREFIX = "/api/v1"


@dataclass(slots=True)
class CliConfig:
    default_base_url: str = DEFAULT_BASE_URL
    default_api_prefix: str = DEFAULT_API_PREFIX
    default_output: str = "json"
    default_timeout_seconds: int = 120

    def to_toml(self) -> str:
        lines = [
            f'default_base_url = "{self.default_base_url}"',
            f'default_api_prefix = "{self.default_api_prefix}"',
            f'default_output = "{self.default_output}"',
            f"default_timeout_seconds = {int(self.default_timeout_seconds)}",
            "",
        ]
        return "\n".join(lines)


class CliConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (Path.home() / ".config" / "lean-cli-toolkit" / "config.toml")

    def load(self) -> CliConfig:
        if not self.path.is_file():
            return CliConfig()
        data = tomllib.loads(self.path.read_text(encoding="utf-8"))
        return CliConfig(
            default_base_url=str(data.get("default_base_url") or DEFAULT_BASE_URL),
            default_api_prefix=str(data.get("default_api_prefix") or DEFAULT_API_PREFIX),
            default_output=str(data.get("default_output") or "json"),
            default_timeout_seconds=int(data.get("default_timeout_seconds") or 120),
        )

    def save(self, cfg: CliConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(cfg.to_toml(), encoding="utf-8")

    def set_value(self, key: str, value: str) -> CliConfig:
        cfg = self.load()
        normalized = key.strip().replace("-", "_")
        if normalized == "default_base_url":
            cfg.default_base_url = str(value)
        elif normalized == "default_api_prefix":
            cfg.default_api_prefix = str(value)
        elif normalized == "default_output":
            cfg.default_output = str(value)
        elif normalized == "default_timeout_seconds":
            cfg.default_timeout_seconds = int(value)
        else:
            raise KeyError(f"unsupported config key: {key}")
        self.save(cfg)
        return cfg
