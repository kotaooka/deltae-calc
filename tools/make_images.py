# アイコン（icons/*.png）と SNS 共有用画像（og.png）を作り直す
#
# 文字は画像に焼き込むので、日本語フォントは Noto Sans CJK JP を使う。
# .ttc は日本語・中国語・韓国語の字形を1ファイルに持つため、index=0（JP）を明示して選ぶ。
# 実行: python tools/make_images.py [Noto Sans CJK のフォルダ]
#   既定は /usr/share/fonts/opentype/noto（Windows なら NotoSansCJK-*.ttc を置いたフォルダを指定）
import math, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parent.parent
FONT_DIR = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/opentype/noto")
SS = 4  # 縮小前の倍率（アンチエイリアス用）

ACCENT = (44, 90, 134)
TP, PP, TT = (76, 196, 162), (239, 169, 62), (234, 111, 166)


def font(weight, size):
    f = ImageFont.truetype(str(FONT_DIR / f"NotoSansCJK-{weight}.ttc"), size, index=0)
    assert f.getname()[0] == "Noto Sans CJK JP", f.getname()
    return f


def arrow(d, p0, p1, color, w, head):
    """p0 から p1 への矢印（先端は p1）"""
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    tip = p1
    base = (tip[0] - head * math.cos(ang), tip[1] - head * math.sin(ang))
    d.line([p0, base], fill=color, width=w)
    left = (base[0] + head * 0.55 * math.sin(ang), base[1] - head * 0.55 * math.cos(ang))
    right = (base[0] - head * 0.55 * math.sin(ang), base[1] + head * 0.55 * math.cos(ang))
    d.polygon([tip, left, right], fill=color)


def dashed_ellipse(d, box, color, w, n=40):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    rx, ry = (box[2] - box[0]) / 2, (box[3] - box[1]) / 2
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 0.55) / n
        pts = [(cx + rx * math.cos(a0 + (a1 - a0) * k / 6), cy + ry * math.sin(a0 + (a1 - a0) * k / 6)) for k in range(7)]
        d.line(pts, fill=color, width=w)


def motif(d, ox, oy, s, line_w, with_axes=True, bg=None, dot=0.055, head=2.6, show_total=True,
          pts=((0.42, 0.60), (0.60, 0.44), (0.74, 0.24)), ell=(0.40, 0.46, 0.40, 0.30)):
    """a*b* 平面の図：許容範囲の楕円、A → B → C の矢印。s は 1 辺の長さ"""
    c, p, x = [(ox + s * u, oy + s * v) for u, v in pts]   # 試料 A・B・C
    r = s * dot
    if with_axes:
        d.line([(ox + s * 0.08, c[1]), (ox + s * 0.92, c[1])], fill=(255, 255, 255, 90), width=max(2, line_w // 2))
        d.line([(c[0], oy + s * 0.08), (c[0], oy + s * 0.92)], fill=(255, 255, 255, 90), width=max(2, line_w // 2))
    dashed_ellipse(d, (c[0] - s * ell[0], c[1] - s * ell[1], c[0] + s * ell[2], c[1] + s * ell[3]), (255, 255, 255, 170), max(2, line_w // 2))

    def seg(a, b, col, w, hd):
        # 点の縁から縁まで（矢じりの先は相手の点の縁に当てる）
        L = math.dist(a, b); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        gap = r + w * 0.6
        arrow(d, (a[0] + ux * gap, a[1] + uy * gap), (b[0] - ux * gap, b[1] - uy * gap), col, w, hd)
    if show_total:
        seg(c, x, (*TT, 255), max(2, line_w // 2), line_w * head * 0.8)
    seg(c, p, (*TP, 255), line_w, line_w * head)
    seg(p, x, (*PP, 255), line_w, line_w * head)
    for q in (c, p, x):
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=(255, 255, 255), outline=bg or ACCENT, width=max(2, line_w // 3))
    return c, p, x


def icon(size, maskable=False, apple=False):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    if maskable or apple:
        d.rectangle([0, 0, S, S], fill=ACCENT)
        pad = S * (0.18 if maskable else 0.10)
    else:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=S * 0.19, fill=ACCENT)
        pad = S * 0.08
    motif(d, pad, pad, S - 2 * pad, int(S * 0.035), dot=0.06, head=1.6, show_total=False,
          pts=((0.26, 0.74), (0.50, 0.50), (0.74, 0.26)), ell=(0.20, 0.60, 0.58, 0.18))
    return im.resize((size, size), Image.LANCZOS)


def og():
    W, H = 1200 * 2, 630 * 2
    im = Image.new("RGB", (W, H))
    top, bot = (38, 78, 124), (28, 60, 100)
    for yy in range(H):
        t = yy / H
        ImageDraw.Draw(im).line([(0, yy), (W, yy)], fill=tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    d = ImageDraw.Draw(im, "RGBA")
    k = 2
    d.text((72 * k, 106 * k), "QC Workbench", font=font("Regular", 26 * k), fill=(225, 234, 244))
    d.text((70 * k, 158 * k), "色差累積ビューア", font=font("Bold", 74 * k), fill=(255, 255, 255))
    sub = font("Regular", 28 * k)
    d.text((72 * k, 266 * k), "色を引き継いだときの色差の累積と、", font=sub, fill=(225, 234, 244))
    d.text((72 * k, 310 * k), "2 色の中間色を図で確かめる", font=sub, fill=(225, 234, 244))
    pill = font("Regular", 22 * k)
    rows = [["CIE76 / CIE94", "CMC", "CIEDE2000"], ["5 角度", "フロップインデックス", "中間色"]]
    y = 404 * k
    for row in rows:
        x = 72 * k
        for t in row:
            tw = d.textlength(t, font=pill)
            w = tw + 44 * k
            d.rounded_rectangle([x, y, x + w, y + 46 * k], radius=23 * k, fill=(255, 255, 255, 30), outline=(255, 255, 255, 110), width=2 * k)
            d.text((x + 22 * k, y + 8 * k), t, font=pill, fill=(255, 255, 255))
            x += w + 14 * k
        y += 64 * k
    # 右側の図
    s = 430 * k
    c, p, x = motif(d, 735 * k, 110 * k, s, 7 * k, bg=top)
    lab = font("Bold", 24 * k)
    d.text((c[0] + 22 * k, c[1] + 8 * k), "A", font=lab, fill=(255, 255, 255))
    d.text((p[0] + 24 * k, p[1] + 2 * k), "B", font=lab, fill=(255, 255, 255))
    d.text((x[0] + 24 * k, x[1] - 14 * k), "C", font=lab, fill=(255, 255, 255))
    d.text((735 * k + s * 0.92 - 40 * k, c[1] + 8 * k), "a*", font=lab, fill=(225, 234, 244))
    d.text((c[0] - 34 * k, 110 * k + s * 0.06), "b*", font=lab, fill=(225, 234, 244))
    return im.resize((1200, 630), Image.LANCZOS)


if __name__ == "__main__":
    (REPO / "icons").mkdir(exist_ok=True)
    icon(192).save(REPO / "icons/icon-192.png")
    icon(512).save(REPO / "icons/icon-512.png")
    icon(512, maskable=True).save(REPO / "icons/icon-maskable-512.png")
    icon(180, apple=True).save(REPO / "icons/apple-touch-icon.png")
    og().save(REPO / "og.png", optimize=True)
    print("icons/*.png と og.png を書き出した")
