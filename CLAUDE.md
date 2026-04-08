# japan-re-potential

全国47都道府県の再エネポテンシャル適地評価GISツール。
[kanto-re-potential](https://github.com/lutelute/kanto-re-potential) を全日本に拡張。

## プロジェクト構成

```
src/
  batch_all_japan.py      # 全国バッチオーケストレーター (--workers並列)
  config.py               # 47都道府県定義 (bbox, SRTMタイル, 電力エリア)
  raster_score.py         # ラスタベース適地スコア計算 (5m/10m/30m)
  fetch_osm_land_use.py   # OSM土地利用データ取得 (Overpass API)
  extract_grid.py         # All-Japan-Gridから送電線・変電所抽出
  download_land_data.py   # SRTM DEM等のデータダウンロード
  slope_analysis.py       # DEM傾斜解析
  mesh_suitability.py     # メッシュ適地評価 (関東版互換)
  build_integrated_map.py # 統合マップ生成
  build_map.py            # 基本マップ
  build_potential_layer.py # REPOSポテンシャルレイヤー
  congestion_simulation.py # pandapower潮流計算
  extract_tochigi_grid.py  # 栃木県系統データ抽出 (レガシー)
scripts/
  server_setup.sh         # サーバー環境セットアップ
  check_progress.sh       # 計算進捗確認
docs_alljapan/            # 全国計算結果 (都道府県別PNG + index.html)
docs/                     # 関東版ドキュメント
output/                   # 計算出力 (gitignore)
data/                     # GISデータ (gitignore)
```

## 依存関係

- Python 3.10+
- numpy, rasterio, scipy, geopandas, shapely, folium, requests
- [All-Japan-Grid](https://github.com/lutelute/All-Japan-Grid) データ

## 計算実行 (160coreサーバー)

```bash
cd ~/projects/japan-re-potential
export ALL_JAPAN_GRID_DIR=~/All-Japan-Grid-ref/data

# 単県テスト
python3 src/batch_all_japan.py -p fukui --resolution 30

# 全国実行 (5m)
python3 src/batch_all_japan.py --resolution 5 --resume 2>&1 | tee logs/batch_main.log
```

## 計算サーバー

- pws-160core (Tailscale: 100.104.225.55)
- サーバー上のパス: `~/projects/kanto-re-potential/` (旧名のまま)
- output: 9.9GB (全都道府県計算済み)
