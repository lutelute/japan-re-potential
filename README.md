# japan-re-potential

全国47都道府県の再生可能エネルギーポテンシャル適地評価ツール (GIS-MCDA/AHP)

[kanto-re-potential](https://github.com/lutelute/kanto-re-potential) の全日本拡張版。

## 概要

GIS-MCDA (AHP) 手法により、日本全国の太陽光発電適地を評価。
送電線距離・傾斜・土地利用・変電所距離・標高・系統距離の多基準を重み付けし、
5m/10m/30m解像度で適地スコアを算出する。

- 47都道府県対応（北海道は14振興局に分割、計60ユニット）
- 160コア計算サーバーによる並列バッチ処理
- Overpass API指数バックオフによるOSMデータ取得

## AHP評価基準

| 基準 | 重み | データソース |
|---|---|---|
| 送電線(154kV以上)距離 | **25%** | [All-Japan-Grid](https://github.com/lutelute/All-Japan-Grid) |
| 傾斜 | **20%** | SRTM DEM 30m |
| 変電所(66kV以上)距離 | **15%** | All-Japan-Grid |
| 土地利用 | **15%** | 国土数値情報 + OSM |
| 標高 | **10%** | SRTM DEM |
| 道路距離 | 10% | OSM |
| 保護区域 | 5% | 国土数値情報 |

## 使い方

```bash
pip install numpy rasterio scipy geopandas shapely folium requests

# 単県実行
python3 src/batch_all_japan.py -p fukui --resolution 30

# 全国バッチ実行 (5m解像度)
export ALL_JAPAN_GRID_DIR=/path/to/All-Japan-Grid/data
python3 src/batch_all_japan.py --resolution 5 --resume --workers 4
```

## データソース

| レイヤー | ソース | 形式 |
|---|---|---|
| 送電線・変電所 | [All-Japan-Grid](https://github.com/lutelute/All-Japan-Grid) (OSM由来) | GeoJSON |
| 土地利用 | 国土数値情報 L03-b + OSM Overpass | GeoTIFF / JSON |
| 傾斜・標高 | SRTM DEM (NASA) 30m | HGT |
| 行政区域 | 国土数値情報 N03 | Shapefile |

## 関連プロジェクト

- [kanto-re-potential](https://github.com/lutelute/kanto-re-potential) - 関東版（オリジナル）
- [All-Japan-Grid](https://github.com/lutelute/All-Japan-Grid) - 全国電力系統GISデータ
- [all-japan-traffic-grid](https://github.com/lutelute/all-japan-traffic-grid) - 交通ネットワーク

## 参考文献

- Al Garni & Awasthi (2017), Applied Energy - GIS-AHP solar site selection
- Doorga et al. (2019), Renewable Energy - Multi-criteria GIS solar farm modelling
- Shorabeh et al. (2019), Renewable Energy - Risk-based MCDA for solar in Iran
