"""Read the website's index.html and list every piece of text in page order (headings, paragraphs, list rows,
captions, buttons, placeholders) plus the images, as JSON for make_website_docx.js, so the site's text can be edited
in Word. Images are shrunk copies (the originals stay as they are). The header menu and the scripts are left out:
the menu repeats the section titles. Photo strips become one line listing their days.
Usage: python website_to_blocks.py <website folder> <out folder>     (writes blocks.json and img/ in <out folder>)
"""
import json
import os
import sys
from html.parser import HTMLParser

from PIL import Image

site, out = sys.argv[1:3]
os.makedirs(os.path.join(out, "img"), exist_ok=True)
BLOCK = {"h1", "h2", "h3", "h4", "p", "li", "figcaption"}
VOID = {"img", "br", "meta", "link", "input"}


def web_copy(src):
    """Shrunk copy for the Word file, and its size in px."""
    im = Image.open(os.path.join(site, src))
    im.thumbnail((1100, 1100), Image.LANCZOS)
    name = src.replace("/", "_")
    path = os.path.join(out, "img", name)
    (im.convert("RGB").save(path, "JPEG", quality=85) if name.lower().endswith(".jpg") else im.save(path, "PNG"))
    return path, im.size


class Walk(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.stack, self.cur, self.skip, self.fmt = [], [], None, 0, []
        self.strip, self.pair = None, None

    def start_block(self, kind, **extra):
        self.end_block()
        self.cur = dict(kind=kind, runs=[], **extra)

    def end_block(self):
        if self.cur and "".join(r["t"] for r in self.cur["runs"]).strip():
            self.blocks.append(self.cur)
        self.cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "").split()
        if tag not in VOID:
            self.stack.append((tag, cls))
        if self.skip or tag in ("head", "script") or (tag == "header" and "top" in cls):
            if tag not in VOID:
                self.skip += 1
            return
        marker = {"intro": "[Opening screen]", "map": "[Section buttons on the opening screen]"}.get(cls[0] if cls else "")
        if tag == "footer":
            marker = "[Footer, at the bottom of the page]"
        if marker:                                           # where on the page the next text is
            self.end_block()
            self.blocks.append(dict(kind="note", runs=[dict(t=marker)]))
        if "strip" in cls:                                   # photo strip: one line of day labels
            self.strip = []
            return
        if "pair" in cls or "thumbs" in cls:                # side-by-side pictures (timeline thumbnails too)
            self.pair = dict(imgs=[], caps=[])
            return
        if tag == "img":
            if self.strip is not None:
                return
            path, (w, h) = web_copy(a["src"])
            if self.pair is not None:
                self.pair["imgs"].append(dict(path=path, w=w, h=h))
            else:
                self.end_block()
                self.blocks.append(dict(kind="img", path=path, w=w, h=h))
            return
        if tag == "br" and self.cur:
            self.cur["runs"].append(dict(t="\n"))
            return
        if self.strip is not None or (self.pair is not None and tag == "figcaption"):
            return
        if tag in BLOCK:
            ordered = any(t == "ol" for t, _ in self.stack[:-1])
            kind = {"li": "num" if ordered else "bullet"}.get(tag, tag)
            if "phase" in cls:
                kind = "label"
            self.start_block(kind)
        elif tag == "div" and cls and cls[0] in ("kicker", "label", "who", "placeholder", "warn", "lab"):
            self.start_block({"placeholder": "todo", "warn": "p", "lab": "label"}.get(cls[0], "label" if cls[0] in ("kicker", "label") else "p"))
        elif tag == "a" and "btn" in cls:
            self.start_block("button")
        elif tag == "div" and "grp" in cls:
            self.start_block("p")
        elif tag == "span" and "lab" in cls:
            self.fmt.append("bold")
        if tag in ("b", "strong", "h4"):
            self.fmt.append("bold")
        elif tag == "i":
            self.fmt.append("italic")
        elif tag == "span" and "todo" in cls:
            self.fmt.append("todo")
        elif tag == "span" and "num" in cls:
            self.fmt.append("num")
        elif tag == "span" and "what" in cls and self.cur and self.cur["runs"]:
            self.cur["runs"].append(dict(t=": "))
        elif tag == "a" and self.cur and self.cur["kind"] == "p" and self.cur["runs"] and \
                any("grp" in c for _, c in self.stack) and not self.cur["runs"][-1]["t"].endswith(": "):
            self.cur["runs"][-1]["t"] = self.cur["runs"][-1]["t"].rstrip()
            self.cur["runs"].append(dict(t="  ·  "))

    def handle_endtag(self, tag):
        if not self.stack:
            return
        t, cls = self.stack.pop()
        if self.skip:
            self.skip -= 1
            return
        if "strip" in cls:
            self.end_block()
            self.blocks.append(dict(kind="note", runs=[dict(t="[Photo strip: " + ", ".join(self.strip) + "]")]))
            self.strip = None
            return
        if "pair" in cls or "thumbs" in cls:
            self.end_block()
            self.blocks.append(dict(kind="pair", imgs=self.pair["imgs"]))
            caps = self.pair["caps"]
            if caps:
                text = (f"Left: {caps[0]}   Right: {caps[1]}" if len(caps) == 2 else
                        "Photos, in order: " + " | ".join(caps))
                self.blocks.append(dict(kind="figcaption", runs=[dict(t=text)]))
            self.pair = None
            return
        if self.fmt and ((t in ("b", "strong", "h4") and "bold" in self.fmt) or (t == "i" and "italic" in self.fmt) or
                         (t == "span" and ("todo" in cls or "num" in cls or "lab" in cls))):
            self.fmt.pop()
            if t == "span" and "lab" in cls and self.cur:
                self.cur["runs"].append(dict(t=": "))
        if t in BLOCK or (t == "div" and cls and cls[0] in ("kicker", "label", "who", "placeholder", "warn", "grp")) or \
                (t == "a" and "btn" in cls):
            if self.strip is None and not (self.pair is not None and t == "figcaption"):
                self.end_block()

    def handle_data(self, data):
        if self.skip:
            return
        text = " ".join(data.split())
        if not text:
            if data and self.cur and self.cur["runs"] and not self.cur["runs"][-1]["t"].endswith((" ", "\n")):
                self.cur["runs"].append(dict(t=" "))
            return
        lead = " " if data[:1].isspace() and self.cur and self.cur["runs"] and not self.cur["runs"][-1]["t"].endswith((" ", "\n", ": ")) else ""
        trail = " " if data[-1:].isspace() else ""
        if self.strip is not None:
            if any(t == "figcaption" for t, _ in self.stack):
                self.strip.append(text)
            return
        if self.pair is not None and any(t == "figcaption" for t, _ in self.stack):
            self.pair["caps"].append(text)
            return
        if self.cur is None:
            return
        f = self.fmt[-1] if self.fmt else ""
        self.cur["runs"].append(dict(t=lead + text + (" " if f == "num" else trail), bold=f in ("bold", "num"),
                                     italic=f == "italic", todo=f == "todo"))


w = Walk()
w.feed(open(os.path.join(site, "index.html"), encoding="utf-8").read())
w.end_block()
json.dump(w.blocks, open(os.path.join(out, "blocks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(w.blocks), "blocks;", sum(b["kind"] in ("img", "pair") for b in w.blocks), "pictures")
