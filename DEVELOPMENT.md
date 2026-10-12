# 開発者向けの情報

## ファイル構成

```
index.html             本体（計算・描画をすべて含む。外部依存は Google Fonts のみ）
manifest.webmanifest   PWA の設定
sw.js                  Service Worker（オフライン用のキャッシュ）
icons/                 アプリのアイコン
og.png                 SNS 共有用の画像（1200×630）
docs/screenshots/      README 用のスクリーンショット
tools/make_images.py   icons/ と og.png を作り直すスクリプト（Noto Sans CJK JP を使用）
tools/screenshots.py   docs/screenshots/ を撮り直すスクリプト
tests/                 計算の照合テスト（test.js）、Sharma らの公式テストデータ（sharma.js）、colour-science の参照値（reference.json / make_reference.py）
.github/workflows/     push のたびに照合テストを実行する設定
```

## 更新して公開する手順

1. `index.html` などを編集する
2. 計算部分を変えたら `node tests/test.js` で照合する
3. `sw.js` の `VERSION` を上げる（上げないと、インストール済みの PWA に古い版が残る）。公開するファイルを増やしたら `ASSETS` にも足す
4. 画面が変わったら、スクリーンショットを撮り直す（下記）
5. `main` に push すると GitHub Pages に反映される

## 計算式

| 式 | 内容 |
|---|---|
| CIE76 | ΔE\*ab = √(ΔL\*² + Δa\*² + Δb\*²) |
| CIE94 | √((ΔL\*/kL·SL)² + (ΔC\*/SC)² + (ΔH\*/SH)²)、SC = 1 + K1·C\*、SH = 1 + K2·C\*（C\* は基準側）。塗装・一般は kL=1, K1=0.045, K2=0.015、繊維は kL=2, K1=0.048, K2=0.014 |
| CMC(l:c) | 基準側の L\*・C\*・h で SL・SC・SH を決める式（[HunterLab の資料](https://support.hunterlab.com/hc/en-us/article_attachments/201440465)） |
| CIEDE2000 | CIE 142-2001（ISO/CIE 11664-6）。kL・kC・kH を変更可 |
| 中間色 | A と B を結ぶ線分 M(s) = A + s(B − A) 上で、ΔE(M→A) / (ΔE(M→A) + ΔE(M→B)) = t となる s を二分法（60 回）で求める。M を基準として計算する。CIE76 では s = t（単純な内分点） |
| フロップインデックス | FI = 2.69 (L\*15° − L\*110°)^1.11 / L\*45°^0.86（[X-Rite MA シリーズの定義](https://www.xrite.com/service-support/Definition_of_Flop_Index)）。ΔFI は試料 − 基準 |

- 差は「後の試料 − 前の試料」。CIE94 と CMC は基準側（前の試料）の値で重みが決まるため、基準と試料を入れ替えると値が変わる
- 判定する組み合わせは、n 試料のとき各段 i → i+1（n − 1 組）と累積 A → k（k = C 以降、n − 2 組）
- 入力値は内部では常に全試料の L\*a\*b\* として持ち、入力の形（差のみ・差＋1 試料・全試料）は表示と編集の仕方だけを変える。差を編集すると、絶対値の試料を動かさずに前後の試料を動かす
- 「差のみ」の入力では、A を原点とした相対座標で計算する。CIE76 は平行移動で値が変わらないため正確に求まるが、それ以外の式と FI は絶対値が必要
- 「単純加算」は 2 段の色差の和、「二乗和平方根」は √(ΔE₁² + ΔE₂²)。CIE76 では実際の値が単純加算を超えないが、CIE94・CMC・CIEDE2000 は距離の公理を満たさないため、わずかに超えることがある
- 積み上がり／打ち消しの判定は L\*a\*b\* 空間の差のベクトルで行う。段が 2 つのときはなす角（cos > 0.5 で積み上がり、< −0.5 で打ち消し）、3 つ以上のときは向きのそろい具合 η = |Σv| / Σ|v|（η ≥ 0.85 で積み上がり、η ≤ √Σ|v|² / Σ|v| で打ち消し）
- a\*b\* 平面の許容範囲は、基準の L\* を固定した断面で ΔE = 許容差 となる境界を、5° 刻みに二分法で求めて描いている

## 検証

```powershell
node tests/test.js              # 不一致があれば終了コード 1
pip install colour-science
python tests/make_reference.py  # 参照値 tests/reference.json を作り直す
```

計算部分は `index.html` の `/*MATH-START*/` から `/*MATH-END*/` の間にまとめてあり、テストはここを切り出して実行する。push のたびに GitHub Actions で、コミット済みの参照値との照合と、最新の colour-science で参照値を作り直しての照合の両方を行う。

| 対象 | 照合先 | 件数 | 判定 |
|---|---|---|---|
| CIEDE2000 | Sharma らの[公式テストデータ](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/) 34 組（基準・試料の入替も含む） | 68 | 公表値（小数 4 桁）の丸め幅 ±0.00005 以内 |
| CIE76・CIE94（塗装・一般、繊維）・CMC（2:1、1:1）・CIEDE2000（kL = 1、2） | colour-science の計算値、乱数 300 組 × 7 式 | 2,100 | 差 1×10⁻⁹ 以下（実際の最大差は 5×10⁻¹⁴ 程度） |
| FI | 手計算（L\*15°=118.2、L\*45°=58.1、L\*110°=30.5 で 11.73）と、L\*45° = 0・L\*15° < L\*110° の扱い | 3 | 一致 |
| 中間色 | ΔE(M→A) / (ΔE(M→A) + ΔE(M→B)) と指定の比、乱数 500 組 × 4 式 × 比 3 種 | 6,000 | 差 1×10⁻⁹ 以下 |

- CMC は色相角 164°・345° で T が、L\* = 16 で SL が不連続に変わる。M がこの位置に来ると比が飛び、指定の比ちょうどになる点がない。二分法は飛びの位置に収束するので、テストでは前後の比が指定の比をはさんでいれば正しいとみなす（乱数 6,000 件中 1 件、比の差 3×10⁻⁵）

## 画像の作り直し

### スクリーンショット（docs/screenshots/）

Google Fonts が読めない環境で撮ると、日本語に中国語字形などの代替フォントが当たる。`tools/screenshots.py` は Google Fonts への要求を fontsource のローカルファイルに差し替え、フォントが読み込まれたことを確認してから撮影する（読めていなければ中断する）。

```powershell
# 任意の作業フォルダで
npm pack @fontsource/biz-udpgothic @fontsource/ibm-plex-mono
Get-ChildItem *.tgz | ForEach-Object { tar -xzf $_.Name --one-top-level }
pip install playwright
python -m playwright install chromium
# リポジトリのフォルダで
python tools/screenshots.py <フォント展開先フォルダ>
```

撮影はサンプル値で行う（色差の累積：シルバーメタリック、5 角度、差＋A の絶対値、CIEDE2000。中間色：赤のソリッド塗装、単一条件）。

### アイコンと og.png

```powershell
python tools/make_images.py <Noto Sans CJK の .ttc があるフォルダ>
```

`.ttc` は日本語・中国語・韓国語の字形を 1 ファイルに持つので、スクリプトは日本語版（index=0）を明示して選ぶ。
