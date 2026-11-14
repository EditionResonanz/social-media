#!/usr/bin/env python3
"""slides.py – Bauprogramm für die TikTok-Slideshows von @editionresonanz (V1, 14.11.2026).

Aus einer Textdatei (tiktok/<sprache>/JJJJ-MM-TT.json) werden fertige JPGs 1080 x 1920.

Befehle (Aufruf aus dem Archiv-Hauptordner):
  python3 werkzeug/slides.py build  tiktok/en/2026-11-16.json   -> tiktok/en/2026-11-16/01.jpg …
  python3 werkzeug/slides.py sheet  tiktok/en/2026-11-16.json   -> tiktok/en/2026-11-16/uebersicht.jpg (Freigabebogen)
  python3 werkzeug/slides.py safe   BILD.jpg AUSGABE.jpg         -> Kontrollbild mit roten TikTok-Sperrzonen
  python3 werkzeug/slides.py check  tiktok/en/2026-11-16.json   -> prüft Wortzahlen und Pflichtteile

Aufbau der Textdatei (Beispiel):
{
  "date": "2026-11-16", "time": "18:07", "format": "F1", "lang": "en",
  "title": "Christmas Eve 1914 vs. Christmas Eve 2026",          # TikTok-Titel, max. 90 Zeichen
  "caption": "… Beschreibung mit Hashtags …",
  "slides": [
    {"split": {"l": {"img": "vorrat/x.jpg", "fx": 0.5, "label": "CHRISTMAS EVE 1914", "text": "…"},
               "r": {"img": "vorrat/y.jpg", "fx": 0.5, "label": "CHRISTMAS EVE 2026", "text": "…"}}},
    {"img": "vorrat/z.jpg", "fx": 0.5, "fy": 0.5, "zoom": 1.0, "text": "…", "hook": true,
     "bubbles": [{"text": "…", "x": 300, "y": 900, "w": 420, "tail": "down"}]},
    {"book": "en"}
  ]
}
fx/fy: Bildausschnitt (0 = links/oben, 1 = rechts/unten), zoom > 1 schneidet enger.
Sperrzonen (frei lassen): oben 8 %, unten 18 %, rechts 14 % Breite zwischen 45 % und 85 % Höhe.
Benötigt: pip install playwright pillow; python3 -m playwright install chromium.
"""
import json, pathlib, re, sys, tempfile, shutil
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

W, H = 1080, 1920
HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / "fonts"
ROOT = HERE.parent
SAFE_TOP, SAFE_BOTTOM = int(H * .08), int(H * .82)
RSTRIP = (int(W * .86), int(H * .45), W, int(H * .85))
NAVY, GOLD, GOLD_HI, CREAM = "#0b1f3a", "#e7c376", "#f5d791", "#f3eedf"

BOOK = {
    "en": {"cover": "vorrat/buch_cover_en.jpg", "kicker": "A true story",
           "title": "The First to Stand Up", "author": "Bernd Blasius",
           "lines": ["Auch auf Deutsch: <i>Wer zuerst aufsteht</i>",
                     "Aussi en français : <i>Le Premier à se lever</i>"],
           "bg": "vorrat/heute_buch_im_karton_en.jpg"},
}


# ------------------------------------------------------------------ Bilder vorbereiten
def cover_crop(src, w, h, fx=.5, fy=.5, zoom=1.0):
    im = Image.open(ROOT / src).convert("RGB")
    sw, sh = im.size
    scale = max(w / sw, h / sh) * zoom
    nw, nh = round(sw * scale), round(sh * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = round((nw - w) * fx)
    y = round((nh - h) * fy)
    return im.crop((x, y, x + w, y + h))


def prep_background(s, tmp, i):
    """Erzeugt das fertige Hintergrundbild einer Folie als JPG im Temp-Ordner."""
    out = tmp / f"bg{i}.jpg"
    if "split" in s:
        L, R = s["split"]["l"], s["split"]["r"]
        a = cover_crop(L["img"], W // 2, H, L.get("fx", .5), L.get("fy", .5), L.get("zoom", 1))
        b = cover_crop(R["img"], W // 2, H, R.get("fx", .5), R.get("fy", .5), R.get("zoom", 1))
        im = Image.new("RGB", (W, H))
        im.paste(a, (0, 0)); im.paste(b, (W // 2, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((W // 2 - 3, 0, W // 2 + 2, H), fill=(245, 215, 145))
    elif "book" in s:
        cfg = BOOK[s["book"]]
        im = cover_crop(cfg["bg"], W, H, .5, .5, 1.15).filter(ImageFilter.GaussianBlur(16))
        im = ImageEnhance.Brightness(im).enhance(.55)
    else:
        im = cover_crop(s["img"], W, H, s.get("fx", .5), s.get("fy", .5), s.get("zoom", 1))
    im.save(out, quality=95)
    return out


# ------------------------------------------------------------------ HTML
def css():
    def ff(name, file, weight, style="normal"):
        return (f"@font-face{{font-family:'{name}';font-weight:{weight};font-style:{style};"
                f"src:url('{(FONTS / file).as_uri()}')}}")
    return "".join([
        ff("Mont", "montserrat-latin-700-normal.woff2", 700), ff("Mont", "montserrat-latin-800-normal.woff2", 800),
        ff("MontX", "montserrat-latin-ext-700-normal.woff2", 700), ff("MontX", "montserrat-latin-ext-800-normal.woff2", 800),
        ff("Lora", "lora-normal.woff2", "400 700"), ff("Lora", "lora-italic.woff2", "400 700", "italic"),
        ff("Cinzel", "cinzel-600.woff2", 600),
    ]) + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;position:relative;overflow:hidden;font-family:Mont,MontX,sans-serif}}
.bg{{position:absolute;inset:0;width:{W}px;height:{H}px}}
.box{{position:absolute;text-align:center}}
.t{{display:inline;background:rgba(255,255,255,.95);color:#111;font-weight:800;line-height:1.42;
    padding:.12em .38em;border-radius:.28em;-webkit-box-decoration-break:clone;box-decoration-break:clone;
    box-shadow:0 6px 24px rgba(0,0,0,.25)}}
.hook .t{{font-size:74px;line-height:1.36}}
.norm .t{{font-size:54px}}
.half .t{{font-size:42px;line-height:1.45}}
.chip{{display:inline-block;background:{NAVY};color:{GOLD_HI};font-weight:800;letter-spacing:.06em;
     font-size:36px;padding:14px 26px;border-radius:14px;box-shadow:0 6px 20px rgba(0,0,0,.35);margin-bottom:22px}}
.cta{{display:inline-block;margin-top:34px;background:{NAVY};color:{GOLD_HI};font-weight:800;font-size:44px;
     padding:16px 30px;border-radius:16px;box-shadow:0 6px 20px rgba(0,0,0,.35)}}
.bub{{position:absolute;background:#fff;color:#111;font-weight:700;font-size:40px;line-height:1.3;text-align:center;
     padding:26px 30px;border-radius:44px;box-shadow:0 8px 26px rgba(0,0,0,.3)}}
.bub:after{{content:"";position:absolute;width:0;height:0;border:24px solid transparent}}
.bub.down:after{{left:50%;bottom:-44px;margin-left:-24px;border-top-color:#fff}}
.bub.down-left:after{{left:22%;bottom:-44px;border-top-color:#fff}}
.bub.down-right:after{{right:22%;bottom:-44px;border-top-color:#fff}}
.bub.up:after{{left:50%;top:-44px;margin-left:-24px;border-bottom-color:#fff}}
.book-k{{font-family:Lora;font-style:italic;color:{GOLD_HI};font-size:58px;text-shadow:0 3px 14px rgba(0,0,0,.6)}}
.book-t{{font-weight:800;color:#fff;font-size:52px;line-height:1.2;text-shadow:0 3px 16px rgba(0,0,0,.7)}}
.book-a{{font-family:Lora;color:{CREAM};font-size:38px;margin-top:8px;text-shadow:0 3px 12px rgba(0,0,0,.7)}}
.book-l{{font-family:Lora;color:{CREAM};font-size:32px;line-height:1.45;text-shadow:0 2px 10px rgba(0,0,0,.8)}}
.book-l i{{color:{GOLD_HI}}}
"""


def slide_html(s, bg):
    body = f'<img class="bg" src="{bg.as_uri()}">'
    if "split" in s:
        for side, x0 in (("l", 0), ("r", W // 2)):
            p = s["split"][side]
            big = ' style="font-size:50px;padding:20px 30px"' if s.get("hook") else ""
            body += (f'<div class="box half" style="left:{x0 + 26}px;width:{W // 2 - 52}px;top:{SAFE_TOP + 30}px">'
                     f'<div class="chip"{big}>{p["label"]}</div><br>'
                     + (f'<span class="t">{p["text"]}</span>' if p.get("text") else "") + "</div>")
    elif "book" in s:
        c = BOOK[s["book"]]
        cover = (ROOT / c["cover"]).as_uri()
        body += (f'<div class="box" style="left:0;right:0;top:{SAFE_TOP + 40}px"><div class="book-k">{c["kicker"]}</div></div>'
                 f'<img src="{cover}" style="position:absolute;left:{(W - 580) // 2}px;top:{SAFE_TOP + 150}px;width:580px;'
                 f'border-radius:6px;box-shadow:0 30px 80px rgba(0,0,0,.65)">'
                 f'<div class="box" style="left:150px;width:760px;top:1268px"><div class="book-t">{c["title"]}</div>'
                 f'<div class="book-a">{c["author"]}</div>'
                 f'<div class="book-l" style="margin-top:30px">{"<br>".join(c["lines"])}</div></div>')
    else:
        cls = "hook" if s.get("hook") else "norm"
        if s.get("text"):
            top = s.get("top", SAFE_TOP + 40)
            cta = f'<br><div class="cta">{s["cta"]}</div>' if s.get("cta") else ""
            body += (f'<div class="box {cls}" style="left:80px;width:{W - 160}px;top:{top}px">'
                     f'<span class="t">{s["text"]}</span>{cta}</div>')
    for b in s.get("bubbles", []):
        w = b.get("w", 440)
        body += (f'<div class="bub {b.get("tail", "down")}" style="left:{b["x"] - w // 2}px;top:{b["y"]}px;width:{w}px">'
                 f'{b["text"]}</div>')
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css()}</style></head><body>{body}</body></html>"


def render(pages, outdir):
    """pages: list of (html_path, out_jpg)"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H})
        for html, out in pages:
            pg.goto(html.as_uri()); pg.wait_for_timeout(250)
            pg.evaluate("document.fonts.ready")
            png = out.with_suffix(".png"); pg.screenshot(path=str(png))
            Image.open(png).convert("RGB").save(out, quality=92, optimize=True, progressive=True); png.unlink()
        b.close()


# ------------------------------------------------------------------ Prüfungen
def words(t):
    return len(re.sub(r"<[^>]+>", " ", t or "").split())


def check(spec):
    probs = []
    sl = spec["slides"]
    if not 6 <= len(sl) <= 8: probs.append(f"{len(sl)} Bilder (Soll 6–8)")
    if "book" not in sl[-1]: probs.append("letztes Bild ist nicht das Buch")
    first = sl[0]
    t0 = first.get("text") or " ".join(first.get("split", {}).get(k, {}).get("label", "") for k in "lr")
    if words(t0) > 8: probs.append(f"Bild 1 hat {words(t0)} Wörter (max. 8)")
    for i, s in enumerate(sl, 1):
        texts = [s.get("text", "")] + [b["text"] for b in s.get("bubbles", [])]
        if "split" in s: texts += [s["split"][k].get("text", "") for k in "lr"]
        for t in texts:
            if words(t) > 14: probs.append(f"Bild {i}: {words(t)} Wörter (max. 14): {t[:40]}…")
    if len(spec.get("title", "")) > 90: probs.append("Titel länger als 90 Zeichen")
    cap = spec.get("caption", "")
    if "comment" not in cap.lower(): probs.append("Beschreibung ohne Aufforderung zum Kommentieren")
    if "#buchtok" not in cap: probs.append("#buchtok fehlt")
    n = len(re.findall(r"#\w+", cap))
    if not 5 <= n <= 8: probs.append(f"{n} Hashtags (Soll 5–7 + #buchtok)")
    return probs


# ------------------------------------------------------------------ Befehle
def build(specfile):
    specfile = pathlib.Path(specfile).resolve()
    spec = json.loads(specfile.read_text())
    out = specfile.with_suffix(""); out.mkdir(exist_ok=True)
    for f in out.glob("[0-9][0-9].jpg"): f.unlink()
    tmp = pathlib.Path(tempfile.mkdtemp())
    pages = []
    for i, s in enumerate(spec["slides"], 1):
        bg = prep_background(s, tmp, i)
        html = tmp / f"s{i}.html"; html.write_text(slide_html(s, bg), encoding="utf-8")
        pages.append((html, out / f"{i:02d}.jpg"))
    render(pages, out)
    shutil.rmtree(tmp)
    for p in check(spec): print("WARNUNG:", p)
    print("ok", out, len(pages), "Bilder")
    return out


def safe(inp, outp):
    im = Image.open(inp).convert("RGB").resize((W, H)); d = ImageDraw.Draw(im, "RGBA")
    for r in ((0, 0, W, SAFE_TOP), (0, SAFE_BOTTOM, W, H), RSTRIP):
        d.rectangle(r, fill=(255, 0, 0, 70), outline=(255, 0, 0, 255), width=5)
    im.save(outp, quality=88)


def sheet(specfile):
    """Freigabebogen: alle Bilder als Vorschau, darunter Titel und Beschreibung (fürs Handy)."""
    specfile = pathlib.Path(specfile).resolve()
    spec = json.loads(specfile.read_text())
    d = specfile.with_suffix("")
    files = sorted(d.glob("[0-9][0-9].jpg"))
    cols, tw = 4, 300
    th = tw * H // W
    rows = (len(files) + cols - 1) // cols
    from playwright.sync_api import sync_playwright
    thumbs = "".join(f'<div class="th"><img src="{f.as_uri()}"><span>{i}</span></div>' for i, f in enumerate(files, 1))
    cap = spec.get("caption", "").replace("\n", "<br>")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><style>{css()}
    body{{width:{cols * (tw + 16) + 40}px;height:auto;background:#f3eedf;padding:24px;font-family:Mont,MontX,sans-serif;overflow:visible}}
    .th{{display:inline-block;position:relative;margin:0 16px 16px 0}} .th img{{width:{tw}px;height:{th}px;border-radius:10px;display:block}}
    .th span{{position:absolute;left:8px;top:8px;background:#0b1f3a;color:#f5d791;font-weight:800;font-size:22px;padding:4px 12px;border-radius:8px}}
    h1{{font-size:30px;margin:8px 0 6px}} .meta{{font-size:22px;color:#555;margin-bottom:14px}}
    .cap{{font-family:Lora;font-size:24px;line-height:1.45;background:#fff;padding:18px 22px;border-radius:12px;width:{cols * (tw + 16) - 16}px}}
    </style></head><body>
    <h1>{spec.get('date', '')} · {spec.get('format', '')} · {spec.get('time', '')} Uhr</h1>
    <div class="meta">Titel: {spec.get('title', '')} <span style="color:#0b1f3a">{spec.get('titleScore', '')}</span></div>
    <div class="meta">Erster Kommentar: {spec.get('firstComment', '–')}</div>
    <div>{thumbs}</div><div class="cap">{cap}</div></body></html>"""
    tmp = pathlib.Path(tempfile.mkdtemp()); hp = tmp / "sheet.html"; hp.write_text(html, encoding="utf-8")
    out = d / "uebersicht.jpg"
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": cols * (tw + 16) + 40, "height": 800})
        pg.goto(hp.as_uri()); pg.wait_for_timeout(400)
        png = tmp / "s.png"; pg.screenshot(path=str(png), full_page=True)
        Image.open(png).convert("RGB").save(out, quality=88)
        b.close()
    shutil.rmtree(tmp)
    print("ok", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit()
    if a[0] == "build": build(a[1])
    elif a[0] == "sheet": sheet(a[1])
    elif a[0] == "safe": safe(a[1], a[2])
    elif a[0] == "check":
        p = check(json.loads(pathlib.Path(a[1]).read_text())); print("\n".join(p) or "alles ok")
    else: print(__doc__)
