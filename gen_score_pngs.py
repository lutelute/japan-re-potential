"""各都道府県のスコアRGBA TIFからPNG + bounds JSONを生成

変更点:
- Resampling.nearest で半透明フリンジを防止
- alpha を 0/255 にバイナリ化（中間値なし）
- palette mode (8-bit) で圧縮率向上
"""
import json, numpy as np, rasterio
from pathlib import Path
from rasterio.enums import Resampling
from PIL import Image
import sys
sys.path.insert(0, "src")
from config import PREFECTURES

out_dir = Path("docs_alljapan")
out_dir.mkdir(exist_ok=True)

bounds_data = {}

for key, cfg in PREFECTURES.items():
    rgba_5m = Path(f"output/{key}/score_total_5m_rgba.tif")
    rgba_30m = Path(f"output/{key}/score_total_rgba.tif")
    tif = rgba_5m if rgba_5m.exists() else rgba_30m if rgba_30m.exists() else None

    if tif is None:
        print(f"SKIP {key}: no RGBA TIF")
        continue

    try:
        with rasterio.open(tif) as ds:
            b = ds.bounds
            bounds_data[key] = {
                "name_ja": cfg["name_ja"],
                "bounds": [[b.bottom, b.left], [b.top, b.right]],
                "center": cfg["center"],
                "grid_area": cfg["grid_area"],
            }
            h, w = ds.height, ds.width
            max_px = 2000
            if w > max_px:
                scale = max_px / w
                new_w = max_px
                new_h = int(h * scale)
            else:
                new_w, new_h = w, h

            # nearest-neighbor resampling to prevent semi-transparent edge pixels
            data_resized = ds.read(
                out_shape=(4, new_h, new_w),
                resampling=Resampling.nearest
            )

        # Binarize alpha: anything > 0 becomes 255 (no semi-transparent pixels)
        alpha = data_resized[3]
        alpha[alpha > 0] = 255
        data_resized[3] = alpha

        rgba_arr = np.moveaxis(data_resized, 0, -1)
        img = Image.fromarray(rgba_arr, "RGBA")

        # Convert to palette mode for smaller file size (6 colors + transparent)
        img = img.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        img = img.convert("RGBA")  # back to RGBA for proper transparency in PNG

        png_path = out_dir / f"{key}.png"
        img.save(png_path, optimize=True)
        size_kb = png_path.stat().st_size / 1024
        print(f"OK {key}: {new_w}x{new_h} -> {size_kb:.0f}KB")

    except Exception as e:
        print(f"ERROR {key}: {e}")

json_path = out_dir / "prefectures.json"
with open(json_path, "w") as f:
    json.dump(bounds_data, f, indent=2, ensure_ascii=False)

total_mb = sum(f.stat().st_size for f in out_dir.glob("*.png")) / 1024 / 1024
print(f"\nSaved {json_path} ({len(bounds_data)} prefectures)")
print(f"Total PNG size: {total_mb:.1f} MB")
