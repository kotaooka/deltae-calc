# README 用スクリーンショット（docs/screenshots/*.png）を撮り直す
#
# Google Fonts が読めない環境で撮ると日本語フォントが当たらず、中国語字形などの代替フォントで写る。
# これを防ぐため、Google Fonts への要求を fontsource のローカルファイルに差し替え、
# 読み込みを確認してから撮影する（読めていなければ中断）。
#
# 準備（任意の作業フォルダで）:
#   npm pack @fontsource/biz-udpgothic @fontsource/zen-kaku-gothic-new @fontsource/jetbrains-mono
#   上の3つの .tgz を展開（tar -xzf <ファイル> --one-top-level）
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
    "zen": ("zen-kaku-gothic-new", ["700", "900"]),
    "mono": ("jetbrains-mono", ["400", "600"]),
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
        return [document.fonts.check("15px 'BIZ UDPGothic'", "承認塗板"),
                document.fonts.check("900 28px 'Zen Kaku Gothic New'", "色差累積"),
                document.fonts.check("15px 'JetBrains Mono'", "0.85")]; }""")
    assert all(ok), f"フォント未読込: {ok}"
    return c, p


def settle(p):
    p.wait_for_timeout(400)
    p.evaluate("document.fonts.ready")


def shot(p, selector, name, pad=0):
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

    # デスクトップ（ライト）
    c, p = open_page(b, url, viewport={"width": 1180, "height": 900}, color_scheme="light")
    p.evaluate("window.scrollTo(0,0)")
    settle(p)
    p.screenshot(path=str(OUT / "overview.png"), clip={"x": 0, "y": 0, "width": 1180, "height": 900})
    shot(p, "section[aria-label='計算条件']", "conditions.png", pad=12)
    shot(p, "section[aria-label='判定']", "judge.png", pad=12)
    shot(p, "#multiRow", "angles.png", pad=12)
    shot(p, "section[aria-label='詳細']", "detail.png", pad=12)
    # 入力の形：差＋ターゲット（既定）と 3 試料の絶対値
    shot(p, "#tblIn", "input-diff.png", pad=10)
    p.click("#segAbs button[data-v='all']")
    shot(p, "#tblIn", "input-abs.png", pad=10)
    c.close()

    # スマホ（ダーク）：判定カードの先頭
    c, p = open_page(b, url, viewport={"width": 390, "height": 844}, device_scale_factor=2,
                     is_mobile=True, has_touch=True, color_scheme="dark")
    p.evaluate("""() => { const el = document.getElementById('banner');
        window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 12); }""")
    settle(p)
    p.screenshot(path=str(OUT / "mobile.png"))
    c.close()
    b.close()
print("docs/screenshots/*.png を書き出した")
