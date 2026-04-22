#!/usr/bin/env python3
"""
既存スコアPNG → 地理参照付き GeoTIFF → XYZ ラスタタイル生成

出力: docs/tiles/{z}/{x}/{y}.png  (Leaflet L.tileLayer 互換)
"""
import json, subprocess, shutil, math
from pathlib import Path

DOCS = Path(__file__).parent / "docs"
WORK = Path(__file__).parent / "tmp_geo"
TILES = DOCS / "tiles"
PREFS_JSON = DOCS / "prefectures.json"
Z_MIN, Z_MAX = 5, 9      # zoom 5-9

WORK.mkdir(exist_ok=True)

prefs = json.loads(PREFS_JSON.read_text())

# ── Step 1: 各 PNG に地理参照を付けて GeoTIFF に変換 ─────────────
geotiffs = []
areas = {}
for key, meta in prefs.items():
    png = DOCS / f"{key}.png"
    if not png.exists():
        continue
    bounds = meta["bounds"]  # [[south, west], [north, east]]
    south, west = bounds[0]
    north, east = bounds[1]
    area = (north - south) * (east - west)
    areas[key] = area

# 大きい面積から先に処理 → VRT では後から追加したものが重複エリアで優先されるため
# 小エリア(より詳細)が最終的に優先
sorted_keys = sorted(areas, key=lambda k: areas[k], reverse=True)

for key in sorted_keys:
    meta = prefs[key]
    png = DOCS / f"{key}.png"
    bounds = meta["bounds"]
    south, west = bounds[0]
    north, east = bounds[1]
    out_tif = WORK / f"{key}.tif"
    if out_tif.exists():
        geotiffs.append(str(out_tif))
        continue
    cmd = [
        "gdal_translate",
        "-a_srs", "EPSG:4326",
        "-a_ullr", str(west), str(north), str(east), str(south),
        "-of", "GTiff",
        str(png), str(out_tif)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        geotiffs.append(str(out_tif))
        print(f"  GeoTIFF: {key}")
    else:
        print(f"  SKIP {key}: {r.stderr.strip()[:80]}")

print(f"\n{len(geotiffs)} GeoTIFF 生成完了")

# ── Step 2: VRT モザイク構築 ───────────────────────────────────
vrt_path = WORK / "mosaic.vrt"
cmd_vrt = ["gdalbuildvrt", "-overwrite", "-resolution", "highest",
           str(vrt_path)] + geotiffs
r = subprocess.run(cmd_vrt, capture_output=True, text=True)
if r.returncode != 0:
    print("VRT error:", r.stderr[:200]); exit(1)
print(f"VRT 構築完了: {vrt_path}")

# ── Step 3: XYZ タイル生成 ──────────────────────────────────────
if TILES.exists():
    shutil.rmtree(TILES)
TILES.mkdir()

cmd_tiles = [
    "gdal2tiles.py",
    "--xyz",
    "-z", f"{Z_MIN}-{Z_MAX}",
    "-r", "near",
    "--processes=4",
    "--no-kml",
    str(vrt_path), str(TILES)
]
print(f"\nタイル生成中 (z{Z_MIN}-{Z_MAX}) ...")
r = subprocess.run(cmd_tiles, text=True)
if r.returncode != 0:
    print("tiles error"); exit(1)

# 不要なHTMLファイルを削除
for f in TILES.glob("*.html"):
    f.unlink()

n_tiles = sum(1 for _ in TILES.rglob("*.png"))
size_mb = sum(f.stat().st_size for f in TILES.rglob("*.png")) / 1e6
print(f"\n完了: {n_tiles} タイル, {size_mb:.1f}MB → docs/tiles/")

# tmp ディレクトリ削除
shutil.rmtree(WORK)
