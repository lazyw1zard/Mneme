from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG_PATH = Path("~/.config/mneme/config.toml")


@dataclass(frozen=True)
class MemoryTagConfig:
    default_ttl_seconds: int = 7 * 24 * 60 * 60
    default_call_ttl: int = 32
    active_limit: int = 20
    high_valence_threshold: float = 0.7


@dataclass(frozen=True)
class ReviewPressureConfig:
    enabled: bool = True
    call_seq_interval: int = 10
    trigger_on_high_valence: bool = True
    trigger_on_interval: bool = True
    packet_limit: int = 6


@dataclass(frozen=True)
class StorageConfig:
    state_dir: Path = field(default_factory=lambda: Path("~/.local/state/mneme").expanduser())


@dataclass(frozen=True)
class MnemeConfig:
    memory_tag: MemoryTagConfig = field(default_factory=MemoryTagConfig)
    review_pressure: ReviewPressureConfig = field(default_factory=ReviewPressureConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


def default_config_path() -> Path:
    explicit = os.environ.get("MNEME_CONFIG")
    if explicit:
        return Path(explicit).expanduser()
    return DEFAULT_CONFIG_PATH.expanduser()


def load_mneme_config(path: str | Path | None = None) -> MnemeConfig:
    target = Path(path).expanduser() if path is not None else default_config_path()
    if not target.exists():
        return MnemeConfig()
    data = tomllib.loads(target.read_text(encoding="utf-8"))

    memory_tag_raw = data.get("memory_tag", {}) or {}
    review_pressure_raw = data.get("review_pressure", {}) or {}
    storage_raw = data.get("storage", {}) or {}

    memory_tag = MemoryTagConfig(
        default_ttl_seconds=int(memory_tag_raw.get("default_ttl_seconds", MemoryTagConfig.default_ttl_seconds)),
        default_call_ttl=int(memory_tag_raw.get("default_call_ttl", MemoryTagConfig.default_call_ttl)),
        active_limit=int(memory_tag_raw.get("active_limit", MemoryTagConfig.active_limit)),
        high_valence_threshold=float(
            memory_tag_raw.get("high_valence_threshold", MemoryTagConfig.high_valence_threshold)
        ),
    )
    review_pressure = ReviewPressureConfig(
        enabled=bool(review_pressure_raw.get("enabled", ReviewPressureConfig.enabled)),
        call_seq_interval=int(review_pressure_raw.get("call_seq_interval", ReviewPressureConfig.call_seq_interval)),
        trigger_on_high_valence=bool(
            review_pressure_raw.get("trigger_on_high_valence", ReviewPressureConfig.trigger_on_high_valence)
        ),
        trigger_on_interval=bool(
            review_pressure_raw.get("trigger_on_interval", ReviewPressureConfig.trigger_on_interval)
        ),
        packet_limit=int(review_pressure_raw.get("packet_limit", ReviewPressureConfig.packet_limit)),
    )
    storage = StorageConfig(
        state_dir=Path(str(storage_raw.get("state_dir", StorageConfig().state_dir))).expanduser(),
    )
    _validate_config(memory_tag=memory_tag, review_pressure=review_pressure)
    return MnemeConfig(memory_tag=memory_tag, review_pressure=review_pressure, storage=storage)


def _validate_config(*, memory_tag: MemoryTagConfig, review_pressure: ReviewPressureConfig) -> None:
    if memory_tag.default_ttl_seconds <= 0:
        raise ValueError("memory_tag.default_ttl_seconds must be positive")
    if memory_tag.default_call_ttl <= 0:
        raise ValueError("memory_tag.default_call_ttl must be positive")
    if memory_tag.active_limit <= 0:
        raise ValueError("memory_tag.active_limit must be positive")
    if not 0.0 <= memory_tag.high_valence_threshold <= 1.0:
        raise ValueError("memory_tag.high_valence_threshold must be between 0.0 and 1.0")
    if review_pressure.call_seq_interval <= 0:
        raise ValueError("review_pressure.call_seq_interval must be positive")
    if review_pressure.packet_limit <= 0:
        raise ValueError("review_pressure.packet_limit must be positive")
