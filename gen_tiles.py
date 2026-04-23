#!/usr/bin/env python3
"""
全国スコア PNG (japan_*.png) → 地理参照付き GeoTIFF → XYZ ラスタタイル生成

都道府県別PNGのモザイクではなく全国1枚PNGを使うことで境界の重複を排除。
出力: docs/tiles/{mode}/{z}/{x}/{y}.png  (Leaflet L.tileLayer 互換)
     例: tiles/total/7/112/50.png
"""
import subprocess, shutil
from pathlib import Path

DOCS  = Path(__file__).parent / "docs"
WORK  = Path(__file__).parent / "tmp_geo"
TILES = DOCS / "tiles"
Z_MIN, Z_MAX = 5, 9

# 全国 bounds (都道府県 bounds の union から算出)
JAPAN_SOUTH =  24.0453
JAPAN_NORTH =  45.5576
JAPAN_WEST  = 126.0000
JAPAN_EAST  = 146.0000

# スコアモード → PNGファイル名
MODE_FILES = {
    "total":     "japan_total.png",
    "slope":     "japan_slope.png",
    "grid_dist": "japan_grid_dist.png",
    "dist_line": "japan_dist_line.png",
    "sub_dist":  "japan_sub_dist.png",
    "land_use":  "japan_land_use.png",
    "elevation": "japan_elevation.png",
}

WORK.mkdir(exist_ok=True)

for mode, png_name in MODE_FILES.items():
    png = DOCS / png_name
    if not png.exists():
        print(f"SKIP {png_name}: ファイルなし")
        continue

    print(f"\n── {mode} ({png_name}) ──────────────────────")

    # Step 1: GeoTIFF 変換
    tif = WORK / f"{mode}.tif"
    cmd = [
        "gdal_translate",
        "-a_srs", "EPSG:4326",
        "-a_ullr",
        str(JAPAN_WEST), str(JAPAN_NORTH),
        str(JAPAN_EAST), str(JAPAN_SOUTH),
        "-of", "GTiff",
        str(png), str(tif),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  gdal_translate error: {r.stderr.strip()[:120]}")
        continue
    print(f"  GeoTIFF 生成: {tif.name}")

    # Step 2: XYZ タイル生成
    out_dir = TILES / mode
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    cmd_tiles = [
        "gdal2tiles.py",
        "--xyz",
        "-z", f"{Z_MIN}-{Z_MAX}",
        "-r", "bilinear",
        "--processes=4",
        "--no-kml",
        str(tif), str(out_dir),
    ]
    print(f"  タイル生成中 (z{Z_MIN}-{Z_MAX}) ...")
    r = subprocess.run(cmd_tiles, text=True)
    if r.returncode != 0:
        print(f"  gdal2tiles error")
        continue

    for f in out_dir.glob("*.html"):
        f.unlink()

    n = sum(1 for _ in out_dir.rglob("*.png"))
    mb = sum(f.stat().st_size for f in out_dir.rglob("*.png")) / 1e6
    print(f"  完了: {n} タイル, {mb:.1f}MB → tiles/{mode}/")

# 作業ディレクトリ削除
shutil.rmtree(WORK)

total_n  = sum(1 for _ in TILES.rglob("*.png"))
total_mb = sum(f.stat().st_size for f in TILES.rglob("*.png")) / 1e6
print(f"\n=== 全モード完了: {total_n} タイル, {total_mb:.1f}MB ===")
