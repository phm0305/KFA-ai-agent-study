"""Write backup/dart_corps.csv: listed companies only (stock_code, corp_code, corp_name).

dart_corp() reads this small file from GitHub so members skip the 3.6 MB corpCode.xml.
Run from the repo root with DART_API_KEY in .env: python tools/make_dart_corps.py
"""

import csv
from pathlib import Path

from collect import download_dart_corps, get_key

ROOT = Path(__file__).resolve().parent.parent

corps = download_dart_corps(get_key("DART_API_KEY"))
out = ROOT / "backup" / "dart_corps.csv"
with out.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(["stock_code", "corp_code", "corp_name"])
    for code in sorted(corps):
        writer.writerow([code, *corps[code]])
print(f"wrote {out.relative_to(ROOT)} ({len(corps)} rows, {out.stat().st_size} bytes)")
