"""Puts the repository root on sys.path so `python tests/test_x.py` can import esp_figure. ROOT = repo root."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
