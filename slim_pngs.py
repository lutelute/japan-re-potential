#!/usr/bin/env python3
"""既存スコアPNGを最大512pxに縮小して軽量化"""
from PIL import Image
from pathlib import Path

docs = Path(__file__).parent / "docs"
MAX_W = 512

total_before = total_after = 0
for p in sorted(docs.glob("*.png")):
    before = p.stat().st_size
    total_before += before
    img = Image.open(p).convert("RGBA")
    w, h = img.size
    if w > MAX_W:
        new_w = MAX_W
        new_h = int(h * MAX_W / w)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    img.save(p, optimize=True)
    after = p.stat().st_size
    total_after += after
    print(f"  {p.name}: {before//1024}KB → {after//1024}KB")

print(f"\n合計: {total_before/1e6:.1f}MB → {total_after/1e6:.1f}MB ({100*(1-total_after/total_before):.0f}%削減)")
