"""Audyt kontrastu WCAG 4,5:1 dla pulpit-szkol.

Używa zewnętrznego skanera audit_contrast.py (nie jest częścią repozytorium). Katalog
ze skanerem wskazuje zmienna środowiskowa AUDIT_CONTRAST_DIR
i dodaje własne tokeny kolorów aplikacji z src/main.css. Wspólnego narzędzia nie zmienia.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
AUDIT_DIR = os.environ.get("AUDIT_CONTRAST_DIR")
if not AUDIT_DIR:
    sys.exit("Ustaw AUDIT_CONTRAST_DIR na katalog z audit_contrast.py")
sys.path.insert(0, AUDIT_DIR)

import audit_contrast as ac  # noqa: E402

ac.PALETTE.update({
    "bs": "#0f6b5c",
    "bsdark": "#0b5247",
    "bs-50": "#e6f4f1",
    "bs-100": "#cde9e3",
    "lav": "#edf2f1",
    "ink": "#1a2422",
    "crit": "#c8203c",
    "high": "#b8400c",
    "mid": "#1d4ed8",
    "low": "#4b5563",
})

total = 0
files = sorted((APP / "src").rglob("*.tsx"))
for path in files:
    for line in ac.scan_file(path, 4.5):
        total += 1
        print(line)
print(f"Przeskanowano plików: {len(files)}. Par poniżej 4,5:1: {total}")
sys.exit(1 if total else 0)
