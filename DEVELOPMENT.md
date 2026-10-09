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
```

## 更新して公開する手順

1. `index.html` などを編集する
2. `sw.js` の `VERSION` を上げる（上げないと、インストール済みの PWA に古い版が残る）。公開するファイルを増やしたら `ASSETS` にも足す
3. 画面が変わったら、スクリーンショットを撮り直す（下記）
4. `main` に push すると GitHub Pages に反映される

## 計算式

| 式 | 内容 |
|---|---|
| CIE76 | ΔE\*ab = √(ΔL\*² + Δa\*² + Δb\*²) |
| CIE94 | √((ΔL\*/kL·SL)² + (ΔC\*/SC)² + (ΔH\*/SH)²)、SC = 1 + K1·C\*、SH = 1 + K2·C\*（C\* は基準側）。塗装・一般は kL=1, K1=0.045, K2=0.015、繊維は kL=2, K1=0.048, K2=0.014 |
| CMC(l:c) | 基準側の L\*・C\*・h で SL・SC・SH を決める式（[HunterLab の資料](https://support.hunterlab.com/hc/en-us/article_attachments/201440465)） |
| CIEDE2000 | CIE 142-2001（ISO/CIE 11664-6）。kL・kC・kH を変更可 |
| フロップインデックス | FI = 2.69 (L\*15° − L\*110°)^1.11 / L\*45°^0.86（[X-Rite MA シリーズの定義](https://www.xrite.com/service-support/Definition_of_Flop_Index)）。ΔFI は試料 − 基準 |

- 差は「試料 − 基準」。CIE94 と CMC は基準側の値で重みが決まるため、基準と試料を入れ替えると値が変わる
- 「差のみ」の入力では、ターゲットを原点とした相対座標で計算する。CIE76 は平行移動で値が変わらないため正確に求まるが、それ以外の式と FI は絶対値が必要
- 「単純加算」は 2 段の色差の和、「二乗和平方根」は √(ΔE₁² + ΔE₂²)。CIE76 では実際の値が単純加算を超えないが、CIE94・CMC・CIEDE2000 は距離の公理を満たさないため、わずかに超えることがある
- 積み上がり／打ち消しの判定は、2 段の差のベクトル（L\*a\*b\* 空間）のなす角で行う（cos > 0.5 で積み上がり、< −0.5 で打ち消し）
- a\*b\* 平面の許容範囲は、基準の L\* を固定した断面で ΔE = 許容差 となる境界を、5° 刻みに二分法で求めて描いている

## 検証

- CIEDE2000：Sharma らの[公式テストデータ](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/) 34 組と 4 桁一致（基準・試料の入替も含む）
- CIE94（塗装・一般、繊維）・CMC（2:1、1:1）・CIEDE2000：colour-science 0.4.7 と乱数 300 組で照合し、最大差 4×10⁻¹⁴
- FI：L\*15°=118.2、L\*45°=58.1、L\*110°=30.5 で 11.73（手計算と一致）

計算部分は `index.html` の `/*MATH-START*/` から `/*MATH-END*/` の間にまとめてあり、Node.js で切り出して試験できる。

## 画像の作り直し

### スクリーンショット（docs/screenshots/）

Google Fonts が読めない環境で撮ると、日本語に中国語字形などの代替フォントが当たる。`tools/screenshots.py` は Google Fonts への要求を fontsource のローカルファイルに差し替え、フォントが読み込まれたことを確認してから撮影する（読めていなければ中断する）。

```powershell
# 任意の作業フォルダで
npm pack @fontsource/biz-udpgothic @fontsource/zen-kaku-gothic-new @fontsource/jetbrains-mono
Get-ChildItem *.tgz | ForEach-Object { tar -xzf $_.Name --one-top-level }
pip install playwright
python -m playwright install chromium
# リポジトリのフォルダで
python tools/screenshots.py <フォント展開先フォルダ>
```

撮影はサンプル値（シルバーメタリック、5 角度、差＋ターゲット、CIEDE2000）で行う。

### アイコンと og.png

```powershell
python tools/make_images.py <Noto Sans CJK の .ttc があるフォルダ>
```

`.ttc` は日本語・中国語・韓国語の字形を 1 ファイルに持つので、スクリプトは日本語版（index=0）を明示して選ぶ。
