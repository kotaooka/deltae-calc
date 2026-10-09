# README 用スクリーンショット（docs/screenshots/*.png）を撮り直す
#
# Google Fonts が読めない環境で撮ると日本語フォントが当たらず、中国語字形などの代替フォントで写る。
# これを防ぐため、Google Fonts への要求を fontsource のローカルファイルに差し替え、
# 読み込みを確認してから撮影する（読めていなければ中断）。
#
# 準備（任意の作業フォルダで）:
#   npm pack @fontsource/biz-udpgothic @fontsource/ibm-plex-mono
#   上の2つの .tgz を展開（tar -xzf <ファイル> --one-top-level）
#   pip install playwright && python -m playwright install chromium
# 実行:
#   python tools/screenshots.py <フォント展開先フォルダ>
#   （Chromium の場所を指定する場合は環境変数 CHROME_PATH）
import os, pathlib, sys
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
FONTS = pathlib.Path(sys.argv[1])
OUT = REPO / "docs/screenshots"
OUT.mkdir(parents=True, exist_ok=True)

PKGS = {
    "biz": ("biz-udpgothic", ["400", "700"]),
    "mono": ("ibm-plex-mono", ["500", "600"]),
}
DIRS, CSS = {}, ""
for tag, (name, weights) in PKGS.items():
    files = next(FONTS.glob(f"fontsource-{name}-*/package/files"))
    DIRS[tag] = files
    for w in weights:
        CSS += (files.parent / f"{w}.css").read_text(encoding="utf-8").replace("./files/", f"https://fonts.gstatic.com/local/{tag}/")


# Google Fonts の CSS を fontsource の CSS（unicode-range 分割済み）に差し替え、ローカルのファイルを返す
def route_fonts(route):
    url = route.request.url
    if "fonts.googleapis.com" in url:
        route.fulfill(status=200, content_type="text/css", body=CSS)
    elif "fonts.gstatic.com/local/" in url:
        tag, name = url.split("/local/", 1)[1].split("/", 1)
        ctype = "font/woff2" if name.endswith("woff2") else "font/woff"
        route.fulfill(status=200, content_type=ctype, body=(DIRS[tag] / name).read_bytes(),
                      headers={"Access-Control-Allow-Origin": "*"})
    else:
        route.continue_()


def open_page(browser, url, **ctx):
    # 毎回新しい状態（保存された入力なし＝サンプル値）で開く
    c = browser.new_context(service_workers="block", **ctx)
    p = c.new_page()
    p.route("**/*", route_fonts)
    p.goto(url)
    p.wait_for_load_state("networkidle")
    ok = p.evaluate("""async () => { await document.fonts.ready;
        return [document.fonts.check("15px 'BIZ UDPGothic'", "範囲を貼り付け"),
                document.fonts.check("700 28px 'BIZ UDPGothic'", "測定値"),
                document.fonts.check("500 15px 'IBM Plex Mono'", "0.85")]; }""")
    assert all(ok), f"フォント未読込: {ok}"
    return c, p


def settle(p):
    p.wait_for_timeout(400)
    p.evaluate("document.fonts.ready")


def shot(p, selector, name, pad=0):
    # 固定ヘッダーが部分撮影に写り込まないよう、撮影中はヘッダーの固定を外す
    p.add_style_tag(content="header.top{position:static!important}")
    el = p.locator(selector).first
    el.scroll_into_view_if_needed()
    settle(p)
    if pad:
        box = el.bounding_box()
        p.screenshot(path=str(OUT / name), full_page=True,
                     clip={"x": max(0, box["x"] - pad), "y": max(0, box["y"] + p.evaluate("scrollY") - pad),
                           "width": box["width"] + pad * 2, "height": box["height"] + pad * 2})
    else:
        el.screenshot(path=str(OUT / name))


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
    url = (REPO / "index.html").as_uri()

    # デスクトップ（ライト）：色差の累積（サンプル値：シルバーメタリック、5 角度、差＋A の絶対値、CIEDE2000）
    c, p = open_page(b, url, viewport={"width": 1180, "height": 900}, color_scheme="light")
    p.evaluate("window.scrollTo(0,0)")
    settle(p)
    p.screenshot(path=str(OUT / "overview.png"), clip={"x": 0, "y": 0, "width": 1180, "height": 900})
    shot(p, "section[aria-label='計算条件']", "conditions.png", pad=12)
    shot(p, "section[aria-label='測定値']", "input-diff.png", pad=12)
    shot(p, "section[aria-label='判定']", "judge.png", pad=12)
    shot(p, "#accMulti", "angles.png", pad=12)
    shot(p, "#p-acc section[aria-label='詳細']", "detail.png", pad=12)
    # 全試料の絶対値の入力
    p.click("#segAccMode button[data-v='all']")
    shot(p, "#accIn", "input-abs.png", pad=10)
    # 試料を 4 つに増やし、D の差を入れた状態の判定
    p.click("#segAccMode button[data-v='anchor']")
    p.click("#nPlus")
    for col, v in ((9, "-0.6"), (11, "0.2")):  # 15° の D − C（ΔL*, Δb*）
        sel = f"input[data-tab='acc'][data-r='0'][data-col='{col}']"
        p.fill(sel, v)
        p.dispatch_event(sel, "input")
    shot(p, "section[aria-label='判定']", "judge4.png", pad=12)
    c.close()

    # 中間色（単一条件の赤のソリッド塗装のサンプル）
    c, p = open_page(b, url + "#mid", viewport={"width": 1180, "height": 900}, color_scheme="light")
    p.click("#segGeom button[data-v='single']")
    shot(p, "#p-mid section[aria-label='2色の測定値']", "mid-input.png", pad=12)
    shot(p, "#p-mid section[aria-label='中間色の結果']", "mid.png", pad=12)
    c.close()

    # スマホ（ダーク）：判定カードの先頭
    c, p = open_page(b, url, viewport={"width": 390, "height": 844}, device_scale_factor=2,
                     is_mobile=True, has_touch=True, color_scheme="dark")
    p.evaluate("""() => { const el = document.getElementById('accBanner');
        const h = document.querySelector('header.top').getBoundingClientRect().height;
        window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - h - 12); }""")
    settle(p)
    p.screenshot(path=str(OUT / "mobile.png"))
    c.close()
    b.close()
print("docs/screenshots/*.png を書き出した")
