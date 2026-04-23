#!/usr/bin/env python3
"""
都道府県別スコアPNG → Python合成（オーバーラップ完全除去）→ XYZ タイル生成

アルゴリズム:
  1. 全国キャンバスを透明で初期化
  2. 都道府県PNGを「大面積→小面積」の順に上書き貼り付け
     （小エリアが最後なので自境界ボックス内をすべて支配 → 隣接県のブリードなし）
  3. キャンバスをGeoTIFFに変換し gdal2tiles.py でXYZタイル生成

その他モード(slope/grid_dist/…)は japan_*.png を使用。

出力: docs/tiles/{mode}/{z}/{x}/{y}.png
"""
import json, subprocess, shutil
from pathlib import Path
import numpy as np
from PIL import Image

DOCS  = Path(__file__).parent / "docs"
WORK  = Path(__file__).parent / "tmp_geo"
TILES = DOCS / "tiles"
PREFS_JSON = DOCS / "prefectures.json"

Z_MIN, Z_MAX = 5, 10    # 拡大しても粗くならないよう z10 まで生成

# 全国 bounds (都道府県 bounds の union)
JAPAN = dict(south=24.0453, west=126.0, north=45.5576, east=146.0)

# total モード以外の全国PNG
MODE_FILES = {
    "slope":     "japan_slope.png",
    "grid_dist": "japan_grid_dist.png",
    "dist_line": "japan_dist_line.png",
    "sub_dist":  "japan_sub_dist.png",
    "land_use":  "japan_land_use.png",
    "elevation": "japan_elevation.png",
}

WORK.mkdir(exist_ok=True)
prefs = json.loads(PREFS_JSON.read_text())

# ── total モード: 都道府県PNG合成 ─────────────────────────────────
print("── total (都道府県別PNG合成) ──────────────────────────────")

# キャンバス解像度: 約350m/px (zoom9タイルと同等)
RES = 0.003   # °/px  ≈ 333m/px
CW = int((JAPAN["east"]  - JAPAN["west"])  / RES)   # ~6667
CH = int((JAPAN["north"] - JAPAN["south"]) / RES)   # ~7167
canvas = np.zeros((CH, CW, 4), dtype=np.uint8)

# 面積で降順ソート → 大エリア先行、小エリアが最後に上書き
def area(key):
    b = prefs[key]["bounds"]
    return (b[1][0]-b[0][0]) * (b[1][1]-b[0][1])

sorted_keys = sorted(
    [k for k in prefs if (DOCS/f"{k}.png").exists()],
    key=area, reverse=True
)

for key in sorted_keys:
    meta = prefs[key]
    b    = meta["bounds"]
    s, w, n, e = b[0][0], b[0][1], b[1][0], b[1][1]

    # キャンバス上のピクセル座標 (row=0 が北端)
    r0 = max(0,  int((JAPAN["north"] - n) / RES))
    r1 = min(CH, int((JAPAN["north"] - s) / RES))
    c0 = max(0,  int((w - JAPAN["west"])   / RES))
    c1 = min(CW, int((e - JAPAN["west"])   / RES))
    if r1 <= r0 or c1 <= c0:
        continue

    img = Image.open(DOCS / f"{key}.png").convert("RGBA")
    patch = np.array(img.resize((c1-c0, r1-r0), Image.LANCZOS))
    # アルファ=0 のピクセルも含めて上書き → 小エリアが境界ボックスを完全支配
    canvas[r0:r1, c0:c1] = patch
    print(f"  {key}: canvas[{r0}:{r1}, {c0}:{c1}]")

# PNG → GeoTIFF → tiles
comp_png = WORK / "composite_total.png"
comp_tif = WORK / "composite_total.tif"
Image.fromarray(canvas, "RGBA").save(comp_png)
print(f"  合成PNG保存: {comp_png}  ({CW}x{CH}px)")

r = subprocess.run([
    "gdal_translate", "-a_srs", "EPSG:4326",
    "-a_ullr",
    str(JAPAN["west"]), str(JAPAN["north"]),
    str(JAPAN["east"]), str(JAPAN["south"]),
    "-of", "GTiff",
    str(comp_png), str(comp_tif)
], capture_output=True, text=True)
if r.returncode != 0:
    print("gdal_translate error:", r.stderr[:200]); exit(1)
print(f"  GeoTIFF生成: {comp_tif}")

out_dir = TILES / "total"
if out_dir.exists(): shutil.rmtree(out_dir)
out_dir.mkdir(parents=True)

r = subprocess.run([
    "gdal2tiles.py", "--xyz",
    "-z", f"{Z_MIN}-{Z_MAX}",
    "-r", "bilinear",
    "--processes=4", "--no-kml",
    str(comp_tif), str(out_dir)
], text=True)
if r.returncode != 0:
    print("gdal2tiles error"); exit(1)

for f in out_dir.glob("*.html"): f.unlink()
n  = sum(1 for _ in out_dir.rglob("*.png"))
mb = sum(f.stat().st_size for f in out_dir.rglob("*.png")) / 1e6
print(f"  完了: {n} タイル, {mb:.1f}MB → tiles/total/")

# ── その他モード: japan_*.png → GeoTIFF → tiles ───────────────────
for mode, png_name in MODE_FILES.items():
    png = DOCS / png_name
    if not png.exists():
        print(f"\nSKIP {mode}: {png_name} なし"); continue

    print(f"\n── {mode} ({png_name}) ──────────────────────────────")
    tif = WORK / f"{mode}.tif"
    r = subprocess.run([
        "gdal_translate", "-a_srs", "EPSG:4326",
        "-a_ullr",
        str(JAPAN["west"]), str(JAPAN["north"]),
        str(JAPAN["east"]), str(JAPAN["south"]),
        "-of", "GTiff", str(png), str(tif)
    ], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  error: {r.stderr[:120]}"); continue

    out_dir = TILES / mode
    if out_dir.exists(): shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    r = subprocess.run([
        "gdal2tiles.py", "--xyz",
        "-z", f"{Z_MIN}-{Z_MAX}",
        "-r", "bilinear",
        "--processes=4", "--no-kml",
        str(tif), str(out_dir)
    ], text=True)
    if r.returncode != 0:
        print(f"  gdal2tiles error"); continue

    for f in out_dir.glob("*.html"): f.unlink()
    n  = sum(1 for _ in out_dir.rglob("*.png"))
    mb = sum(f.stat().st_size for f in out_dir.rglob("*.png")) / 1e6
    print(f"  完了: {n} タイル, {mb:.1f}MB → tiles/{mode}/")

shutil.rmtree(WORK)

total_n  = sum(1 for _ in TILES.rglob("*.png"))
total_mb = sum(f.stat().st_size for f in TILES.rglob("*.png")) / 1e6
print(f"\n=== 全モード完了: {total_n} タイル, {total_mb:.1f}MB ===")
