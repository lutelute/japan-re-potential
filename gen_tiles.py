#!/usr/bin/env python3
"""
XYZタイル生成 — 全国概観 + 都道府県別詳細

STEP 1: 全国概観 (z5-9, 全7モード)
  → docs/tiles/{mode}/{z}/{x}/{y}.png

STEP 2: 都道府県別詳細 (z5-11, total モード)
  → docs/{pref}/tiles_total/{z}/{x}/{y}.png
  kanto-re-potential と同じパス構造。都道府県選択時に高解像度で表示。

実行環境: サーバー (pws-160core) 推奨
依存: gdal_translate, gdal2tiles.py, Pillow, numpy
"""
import json, subprocess, shutil
from pathlib import Path
import numpy as np
from PIL import Image

DOCS       = Path(__file__).parent / "docs"
WORK       = Path(__file__).parent / "tmp_geo"
PREFS_JSON = DOCS / "prefectures.json"

Z_OVERVIEW = "5-9"   # 全国概観
Z_PREF     = "5-12"  # 都道府県別詳細 (total モード, ~31m/px@z12@35°N)

JAPAN = dict(south=24.0453, west=126.0, north=45.5576, east=146.0)

MODE_JAPAN_PNGS = {
    "slope":     "japan_slope.png",
    "grid_dist": "japan_grid_dist.png",
    "dist_line": "japan_dist_line.png",
    "sub_dist":  "japan_sub_dist.png",
    "land_use":  "japan_land_use.png",
    "elevation": "japan_elevation.png",
}

WORK.mkdir(exist_ok=True)
prefs = json.loads(PREFS_JSON.read_text())


# ── ヘルパー ──────────────────────────────────────────────────

def gdal_translate(src, dst, west, north, east, south):
    r = subprocess.run([
        "gdal_translate", "-a_srs", "EPSG:4326",
        "-a_ullr", str(west), str(north), str(east), str(south),
        "-of", "GTiff", str(src), str(dst)
    ], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    gdal_translate error: {r.stderr[:120]}")
    return r.returncode == 0

def gdal2tiles(tif, out_dir, z_range, processes=4):
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([
        "gdal2tiles.py", "--xyz",
        "-z", z_range,
        "-r", "bilinear",
        f"--processes={processes}",
        "--no-kml",
        str(tif), str(out_dir)
    ], capture_output=True, text=True)
    for f in out_dir.glob("*.html"):
        f.unlink()
    if r.returncode != 0:
        print(f"    gdal2tiles error: {r.stderr[:120]}")
    return r.returncode == 0

def count_tiles(d):
    return sum(1 for _ in d.rglob("*.png"))

def size_mb(d):
    return sum(f.stat().st_size for f in d.rglob("*.png")) / 1e6


# ══════════════════════════════════════════════════════════════
# STEP 1: 全国概観タイル (z5-9, 全7モード)
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print(f"STEP 1: 全国概観タイル ({Z_OVERVIEW})")
print("=" * 60)

# total: 都道府県PNG合成
print("\n── total (都道府県別PNG大→小順合成) ──")
RES = 0.003
CW = int((JAPAN["east"]  - JAPAN["west"])  / RES)
CH = int((JAPAN["north"] - JAPAN["south"]) / RES)
canvas = np.zeros((CH, CW, 4), dtype=np.uint8)

def area(key):
    b = prefs[key]["bounds"]
    return (b[1][0]-b[0][0]) * (b[1][1]-b[0][1])

sorted_keys = sorted(
    [k for k in prefs if (DOCS/f"{k}.png").exists()],
    key=area, reverse=True
)
for key in sorted_keys:
    b = prefs[key]["bounds"]
    s, w, n, e = b[0][0], b[0][1], b[1][0], b[1][1]
    r0 = max(0,  int((JAPAN["north"] - n) / RES))
    r1 = min(CH, int((JAPAN["north"] - s) / RES))
    c0 = max(0,  int((w - JAPAN["west"])  / RES))
    c1 = min(CW, int((e - JAPAN["west"])  / RES))
    if r1 <= r0 or c1 <= c0:
        continue
    img   = Image.open(DOCS / f"{key}.png").convert("RGBA")
    patch = np.array(img.resize((c1-c0, r1-r0), Image.LANCZOS))
    canvas[r0:r1, c0:c1] = patch
    print(f"  {key}")

comp_png = WORK / "composite_total.png"
comp_tif = WORK / "composite_total.tif"
Image.fromarray(canvas, "RGBA").save(comp_png)
print(f"合成PNG: {CW}x{CH}px")

if gdal_translate(comp_png, comp_tif, JAPAN["west"], JAPAN["north"], JAPAN["east"], JAPAN["south"]):
    out_dir = DOCS / "tiles" / "total"
    if out_dir.exists(): shutil.rmtree(out_dir)
    gdal2tiles(comp_tif, out_dir, Z_OVERVIEW)
    print(f"  → {count_tiles(out_dir)} tiles, {size_mb(out_dir):.1f}MB")

# その他モード
for mode, png_name in MODE_JAPAN_PNGS.items():
    png = DOCS / png_name
    if not png.exists():
        print(f"\nSKIP {mode}: {png_name} なし"); continue
    print(f"\n── {mode} ──")
    tif = WORK / f"overview_{mode}.tif"
    if gdal_translate(png, tif, JAPAN["west"], JAPAN["north"], JAPAN["east"], JAPAN["south"]):
        out_dir = DOCS / "tiles" / mode
        if out_dir.exists(): shutil.rmtree(out_dir)
        gdal2tiles(tif, out_dir, Z_OVERVIEW)
        print(f"  → {count_tiles(out_dir)} tiles, {size_mb(out_dir):.1f}MB")


# ══════════════════════════════════════════════════════════════
# STEP 2: 都道府県別詳細タイル (z5-11, total モード)
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"STEP 2: 都道府県別詳細タイル ({Z_PREF}, total モード)")
print("=" * 60)

total_pref_tiles = 0
for key, meta in prefs.items():
    src_png = DOCS / f"{key}.png"
    if not src_png.exists():
        print(f"  SKIP {key}: PNG なし"); continue

    b = meta["bounds"]
    s, w, n, e = b[0][0], b[0][1], b[1][0], b[1][1]

    tif     = WORK / f"{key}_total.tif"
    out_dir = DOCS / key / "tiles_total"

    if not gdal_translate(src_png, tif, w, n, e, s):
        continue
    if out_dir.exists(): shutil.rmtree(out_dir)
    gdal2tiles(tif, out_dir, Z_PREF)

    n_tiles = count_tiles(out_dir)
    total_pref_tiles += n_tiles
    print(f"  {key}: {n_tiles} tiles")

# 一時ファイル削除
shutil.rmtree(WORK)

print("\n" + "=" * 60)
overview_tiles = count_tiles(DOCS / "tiles")
overview_mb    = size_mb(DOCS / "tiles")
print(f"STEP1 全国概観: {overview_tiles} tiles, {overview_mb:.1f}MB")
print(f"STEP2 都道府県別: {total_pref_tiles} tiles")
grand_mb = overview_mb + sum(
    f.stat().st_size for key in prefs
    for f in (DOCS / key / "tiles_total").rglob("*.png")
    if (DOCS / key / "tiles_total").exists()
) / 1e6
print(f"総合計: {overview_tiles + total_pref_tiles} tiles, {grand_mb:.1f}MB")
