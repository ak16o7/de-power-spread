"""Shared fixtures: a synthetic world in a temp folder, wired into config and env."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from dps import config, hf, synthetic

DAYS = 150


def _wire(mp: pytest.MonkeyPatch, root: Path) -> None:
    mp.setattr(config, "DATA_DIR", str(root / "data"))
    mp.setattr(config, "REPORTS_DIR", str(root / "reports"))
    mp.setattr(config, "SIGNALS_DIR", str(root / "signals"))
    mp.setattr(config, "LIVE_DIR", str(root / "live"))
    mp.setattr(config, "README", str(root / "README.md"))
    mp.setenv("DPS_HF_LOCAL", str(root / "hf"))
    hf.weather.cache_clear()
    hf.capacity.cache_clear()


def _world(tmp_path_factory, name: str, alpha: bool):
    root = tmp_path_factory.mktemp(name)
    start = config.START
    end = start + timedelta(days=DAYS)
    synthetic.make(root / "data", root / "hf", start, end, alpha=alpha, seed=7)
    return root, start, end


@pytest.fixture(scope="session")
def planted_world(tmp_path_factory):
    return _world(tmp_path_factory, "planted", alpha=True)


@pytest.fixture(scope="session")
def noise_world(tmp_path_factory):
    return _world(tmp_path_factory, "noise", alpha=False)


@pytest.fixture
def planted(planted_world, monkeypatch):
    root, start, end = planted_world
    _wire(monkeypatch, root)
    yield root, start, end
    hf.weather.cache_clear()
    hf.capacity.cache_clear()


@pytest.fixture
def noise(noise_world, monkeypatch):
    root, start, end = noise_world
    _wire(monkeypatch, root)
    yield root, start, end
    hf.weather.cache_clear()
    hf.capacity.cache_clear()


@pytest.fixture
def tmp_world(tmp_path, monkeypatch):
    """A fresh, writable copy of a small synthetic world (for tests that modify data)."""
    start = config.START
    end = start + timedelta(days=60)
    synthetic.make(tmp_path / "data", tmp_path / "hf", start, end, alpha=True, seed=3)
    _wire(monkeypatch, tmp_path)
    yield tmp_path, start, end
    hf.weather.cache_clear()
    hf.capacity.cache_clear()
