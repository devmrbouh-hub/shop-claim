"""Tests for Excel → YAML catalog import."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORT_SCRIPT = REPO_ROOT / "catalog" / "import" / "import-offers-from-xlsx.py"
TEMPLATE_XLSX = REPO_ROOT / "catalog" / "import" / "offers-template.xlsx"


def _resolve_market_dir() -> Path | None:
    cherno = os.environ.get("CHERNO_ROOT")
    if cherno:
        candidate = Path(cherno) / "Instance_1" / "ExpansionMod" / "Market"
        if candidate.is_dir():
            return candidate
    mono = REPO_ROOT.parent.parent / "Instance_1" / "ExpansionMod" / "Market"
    if mono.is_dir():
        return mono
    standalone = Path("D:/Cherno/Instance_1/ExpansionMod/Market")
    if standalone.is_dir():
        return standalone
    return None


def test_import_from_template_xlsx(tmp_path: Path):
    pytest.importorskip("openpyxl")
    market_dir = _resolve_market_dir()
    if market_dir is None:
        pytest.skip("CHERNO_ROOT market dir not found (Instance_1/ExpansionMod/Market)")
    offers_out = tmp_path / "offers.yaml"
    profiles_out = tmp_path / "vehicle_profiles.yaml"
    result = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--input",
            str(TEMPLATE_XLSX),
            "--offers-out",
            str(offers_out),
            "--profiles-out",
            str(profiles_out),
            "--market-dir",
            str(market_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(IMPORT_SCRIPT.parent),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    data = yaml.safe_load(offers_out.read_text(encoding="utf-8"))
    offers = {str(k): v for k, v in data["offers"].items()}
    assert len(offers) >= 1
    assert "12345" not in offers
    assert "12346" not in offers
    assert "12350" not in offers
    assert "12351" not in offers

    types = {o.get("type") for o in offers.values()}
    assert "container" in types

    profiles = yaml.safe_load(profiles_out.read_text(encoding="utf-8"))["profiles"]
    assert isinstance(profiles, dict)
