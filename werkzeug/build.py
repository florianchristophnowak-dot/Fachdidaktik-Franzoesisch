#!/usr/bin/env python3
"""Erzeugt die Website der Enzyklopädie Fachdidaktik Französisch aus den Markdown-Dateien in inhalt/.

Ergebnis ist eine einzige HTML-Datei mit allen Einträgen, Schriften und Funktionen. Sie dient als
Startseite der Website (index.html) und zugleich als Offline-Fassung zum Herunterladen.

Aufruf (im Repository):
    python3 werkzeug/build.py                 # schreibt nach _site/
    python3 werkzeug/build.py --out ausgabe   # anderer Zielordner
Nur Python-Standardbibliothek. GitHub Actions ruft das Skript bei jeder Änderung auf.
"""
import argparse
import base64
import datetime
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TITLE = "Enzyklopädie Fachdidaktik Französisch"
OFFLINE_NAME = "enzyklopaedie-fachdidaktik-franzoesisch.html"
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

RUBRIC_SLUGS = {
    "Auf einen Blick": "blick",
    "Haltung": "haltung",
    "Handlungshinweise": "handlung",
    "Best Practice Französisch": "praxis",
    "Stolpersteine": "stolpersteine",
    "Beobachten und beraten": "beobachten",
    "Reflexionsfragen": "reflexion",
    "Bezüge": "bezuege",
    "Forschungslage": "forschung",
    "Querverweise": "querverweise",
    "Bibliografie": "bibliografie",
}

CODE = r"[A-H][1-9](?![0-9A-Za-zÄÖÜäöüß])"
SIEHE_RE = re.compile(
    r"(siehe\s+(?:auch\s+)?)(" + CODE + r"(?:\s*(?:,|und|sowie|oder|bzw\.)\s*" + CODE + r")*)"
)
CODE_RE = re.compile(CODE)
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+(?:\([^\s)]*\)[^\s)]*)*)\)")

WARNUNGEN = []


def warn(msg, path=None):
    WARNUNGEN.append((msg, path))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        loc = " file=%s" % path if path else ""
        print("::warning%s::%s" % (loc, msg))
    else:
        print("Hinweis: %s%s" % (msg, " (%s)" % path if path else ""), file=sys.stderr)


def slugify(text):
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "abschnitt"


def deutsches_datum(ts):
    d = datetime.datetime.fromtimestamp(ts, tz=berlin())
    return "%d. %s %d" % (d.day, MONATE[d.month - 1], d.year)


def berlin():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Berlin")
    except Exception:
        return datetime.timezone(datetime.timedelta(hours=1))


class Renderer:
    """Kleiner Markdown-Renderer für die Formen, die in den Einträgen vorkommen."""

    def __init__(self, known_codes):
        self.known = set(known_codes)
        self.refs_found = []

    # ---------- inline ----------
    def inline(self, s):
        s = (s.replace("\\[", "\x00LB\x00").replace("\\]", "\x00RB\x00")
              .replace("\\*", "\x00AST\x00").replace("\\|", "\x00PIPE\x00"))
        s = html.escape(s, quote=False)
        s = LINK_RE.sub(
            lambda m: '<a class="ext" href="%s" target="_blank" rel="noopener">%s</a>'
            % (m.group(2).replace('"', "%22"), m.group(1)),
            s,
        )
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", s)
        s = (s.replace("\x00LB\x00", "[").replace("\x00RB\x00", "]")
              .replace("\x00AST\x00", "*").replace("\x00PIPE\x00", "|"))
        return self.link_refs(s)

    def link_refs(self, s):
        parts = re.split(r"(<[^>]+>)", s)
        depth_a = 0
        out = []
        for p in parts:
            if p.startswith("<"):
                if re.match(r"<a\b", p):
                    depth_a += 1
                elif p.startswith("</a"):
                    depth_a = max(0, depth_a - 1)
                out.append(p)
                continue
            if depth_a:
                out.append(p)
                continue
            out.append(SIEHE_RE.sub(self._siehe, p))
        return "".join(out)

    def _siehe(self, m):
        def code_link(cm):
            code = cm.group(0)
            if code in self.known:
                self.refs_found.append(code)
                return '<a class="ref" href="#%s" data-ref="%s">%s</a>' % (code.lower(), code, code)
            return '<span class="ref-missing" title="Kein Eintrag mit diesem Kürzel">%s</span>' % code
        return m.group(1) + CODE_RE.sub(code_link, m.group(2))

    # ---------- blocks ----------
    @staticmethod
    def split_row(line):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|") and not line.endswith("\\|"):
            line = line[:-1]
        cells = re.split(r"(?<!\\)\|", line)
        return [c.strip() for c in cells]

    @staticmethod
    def is_sep(line):
        return bool(re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", line.strip()))

    def is_block_start(self, lines, i):
        line = lines[i]
        if re.match(r"^[-*] ", line) or re.match(r"^\d+\. ", line):
            return True
        if line.startswith("|") and i + 1 < len(lines) and self.is_sep(lines[i + 1]):
            return True
        return False

    def render(self, md):
        lines = md.strip("\n").split("\n")
        out = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if line.startswith("|") and i + 1 < n and self.is_sep(lines[i + 1]):
                header = self.split_row(line)
                i += 2
                rows = []
                while i < n and lines[i].startswith("|"):
                    rows.append(self.split_row(lines[i]))
                    i += 1
                out.append(self.table(header, rows))
                continue
            if re.match(r"^[-*] ", line):
                items = []
                while i < n and (re.match(r"^[-*] ", lines[i]) or (
                        items and lines[i].strip() and not self.is_block_start(lines, i))):
                    if re.match(r"^[-*] ", lines[i]):
                        items.append(lines[i][2:].strip())
                    else:
                        items[-1] += " " + lines[i].strip()
                    i += 1
                out.append("<ul>" + "".join("<li>%s</li>" % self.inline(x) for x in items) + "</ul>")
                continue
            m = re.match(r"^(\d+)\. ", line)
            if m:
                start = int(m.group(1))
                items = []
                while i < n and (re.match(r"^\d+\. ", lines[i]) or (
                        items and lines[i].strip() and not self.is_block_start(lines, i))):
                    if re.match(r"^\d+\. ", lines[i]):
                        items.append(re.sub(r"^\d+\. ", "", lines[i]).strip())
                    else:
                        items[-1] += " " + lines[i].strip()
                    i += 1
                attr = "" if start == 1 else ' start="%d"' % start
                out.append("<ol%s>" % attr + "".join("<li>%s</li>" % self.inline(x) for x in items) + "</ol>")
                continue
            hm = re.match(r"^#{3,6} (.+)$", line)
            if hm:
                out.append('<h4 class="sub">%s</h4>' % self.inline(hm.group(1).strip()))
                i += 1
                continue
            para = [line.strip()]
            i += 1
            while i < n and lines[i].strip() and not self.is_block_start(lines, i) and not lines[i].startswith("#"):
                para.append(lines[i].strip())
                i += 1
            text = " ".join(para)
            if re.fullmatch(r"\*\*[^*]+\*\*", text):
                out.append('<h4 class="sub">%s</h4>' % self.inline(text[2:-2]))
            elif text.startswith("*") and not text.startswith("**") and text.endswith("*"):
                out.append('<p class="note">%s</p>' % self.inline(text))
            elif text.startswith("**"):
                out.append('<p class="lead-bold">%s</p>' % self.inline(text))
            else:
                out.append("<p>%s</p>" % self.inline(text))
        return "\n".join(out)

    def table(self, header, rows):
        cols = len(header)
        h = "".join("<th>%s</th>" % self.inline(c) for c in header)
        body = []
        for r in rows:
            r = (r + [""] * cols)[:cols]
            body.append("<tr>" + "".join("<td>%s</td>" % self.inline(c) for c in r) + "</tr>")
        return ('<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                % (h, "".join(body)))


def plain(md_text):
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md_text)
    t = t.replace("**", "").replace("\\*", "\x00")
    t = re.sub(r"(?<![\w])\*(?=\S)(.+?)(?<=\S)\*(?![\w])", r"\1", t)
    t = t.replace("\x00", "*").replace("\\[", "[").replace("\\]", "]")
    return re.sub(r"\s+", " ", t).strip()


def shorten(text, limit=240):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if dot > 90:
        return cut[:dot + 1]
    return cut[:cut.rfind(" ")] + " …"


def split_sections(text, level):
    pat = re.compile(r"^%s (.+)$" % ("#" * level), re.M)
    ms = list(pat.finditer(text))
    out = []
    for k, m in enumerate(ms):
        end = ms[k + 1].start() if k + 1 < len(ms) else len(text)
        out.append((m.group(1).strip(), text[m.end():end].strip("\n")))
    return out


def read_md(path):
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def rel(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_overview(path, renderer):
    data = {"sections": [], "tag_groups": [], "template": {}}
    if not path.exists():
        warn("Die Übersicht fehlt; Tag-Filter und Benutzung bleiben leer.", rel(path))
        return data
    for title, body in split_sections(read_md(path), 2):
        data["sections"].append({"title": title, "slug": slugify(title), "html": renderer.render(body)})
        if title.startswith("Tags"):
            for line in body.split("\n"):
                if line.startswith("|") and "#" in line:
                    cells = renderer.split_row(line)
                    if len(cells) >= 2:
                        tags = []
                        for tm in re.finditer(r"#(\w+)(?:\s*\(([^)]*)\))?", cells[1]):
                            tags.append({"tag": tm.group(1), "desc": tm.group(2) or ""})
                        data["tag_groups"].append({"group": cells[0], "tags": tags})
        if title.startswith("Eintragsvorlage"):
            for line in body.split("\n"):
                if line.startswith("|") and not renderer.is_sep(line):
                    cells = renderer.split_row(line)
                    if len(cells) >= 3 and cells[0] != "Rubrik":
                        data["template"][cells[0]] = {"inhalt": cells[1], "nutzen": cells[2]}
    return data


def read_areas(inhalt):
    areas = []
    for d in sorted(p for p in inhalt.iterdir() if p.is_dir() and re.match(r"^[A-H]", p.name)):
        code, name = d.name[0], d.name[2:].replace("-", " ").strip() or d.name
        readme = d / "README.md"
        if readme.exists():
            m = re.match(r"^# ([A-H]) · (.+)$", read_md(readme), re.M)
            if m:
                code, name = m.group(1), m.group(2).strip()
            else:
                warn("Erste Zeile sollte so aussehen: # %s · Name des Bereichs" % code, rel(readme))
        else:
            warn("Im Ordner fehlt README.md mit dem Namen des Bereichs.", rel(d))
        entries = []
        for f in sorted(d.glob("*.md"), key=lambda p: p.name):
            if f.name == "README.md":
                continue
            text = read_md(f)
            m = re.search(r"^# ([A-H][1-9]) (.+)$", text, re.M)
            if not m:
                warn("Datei übersprungen: Die erste Überschrift muss so aussehen: # %s1 Titel" % code, rel(f))
                continue
            if m.group(1)[0] != code:
                warn("Kürzel %s passt nicht zum Bereich %s." % (m.group(1), code), rel(f))
            entries.append({"id": m.group(1), "title": m.group(2).strip(), "area": code,
                            "md": text[m.end():], "path": rel(f)})
        entries.sort(key=lambda e: int(e["id"][1:]))
        areas.append({"code": code, "name": name, "entries": entries})
    return areas


def build(inhalt, stand, source, changed):
    areas = read_areas(inhalt)
    all_entries = [e for a in areas for e in a["entries"]]
    seen = {}
    for e in all_entries:
        if e["id"] in seen:
            warn("Kürzel %s kommt doppelt vor (auch in %s)." % (e["id"], seen[e["id"]]), e["path"])
        seen.setdefault(e["id"], e["path"])
    known = [e["id"] for e in all_entries]
    titles = {e["id"]: e["title"] for e in all_entries}
    renderer = Renderer(known)

    out_entries = []
    for e in all_entries:
        rubrics = []
        tags, stand_line, summary = [], "", ""
        qv = []
        renderer.refs_found = []
        sections = split_sections(e["md"], 2)
        names = [s[0] for s in sections]
        unknown = [n for n in names if n not in RUBRIC_SLUGS]
        missing = [n for n in RUBRIC_SLUGS if n not in names]
        if unknown:
            warn("%s: unbekannte Rubrik %s (erscheint nicht im Querschnitt)." % (e["id"], ", ".join(unknown)), e["path"])
        if missing:
            warn("%s: Rubrik fehlt: %s." % (e["id"], ", ".join(missing)), e["path"])
        for rname, rmd in sections:
            slug = RUBRIC_SLUGS.get(rname, slugify(rname))
            if slug == "blick":
                keep = []
                for line in rmd.split("\n"):
                    tm = re.match(r"^[-*] \*\*Tags:\*\*\s*(.+)$", line)
                    sm = re.match(r"^[-*] \*\*Stand:\*\*\s*(.+)$", line)
                    if tm:
                        tags = re.findall(r"#(\w+)", tm.group(1))
                    elif sm:
                        stand_line = sm.group(1).strip()
                    else:
                        keep.append(line)
                rmd = "\n".join(keep)
                first = next((l for l in rmd.split("\n")
                              if l.strip() and not l.startswith("|") and not re.match(r"^[-*] ", l)), "")
                summary = shorten(plain(first))
            if slug == "querverweise":
                raw = " ".join(l.strip() for l in rmd.split("\n") if l.strip())
                for item in re.split(r",\s*(?=[A-H][1-9]\s)", raw):
                    im = re.match(r"^([A-H][1-9])\s+(.+?)\.?$", item.strip())
                    if im:
                        qv.append({"id": im.group(1), "label": im.group(2).strip(),
                                   "known": im.group(1) in titles})
                        if im.group(1) not in titles:
                            warn("%s: Querverweis auf %s, diesen Eintrag gibt es nicht." % (e["id"], im.group(1)), e["path"])
                html_q = ['<ul class="qv-list">']
                for q in qv:
                    if q["known"]:
                        html_q.append('<li><a class="ref qv" href="#%s" data-ref="%s"><span class="code a-%s">%s</span> %s</a></li>'
                                      % (q["id"].lower(), q["id"], q["id"][0].lower(), q["id"], html.escape(titles[q["id"]])))
                    else:
                        html_q.append('<li><span class="code">%s</span> %s</li>' % (q["id"], html.escape(q["label"])))
                html_q.append("</ul>")
                rubrics.append({"name": rname, "slug": slug, "html": "".join(html_q)})
                continue
            rubrics.append({"name": rname, "slug": slug, "html": renderer.render(rmd)})
        inline_refs = sorted(set(r for r in renderer.refs_found if r != e["id"]))
        status = "dr" if "ergänzt um Deep Research" in stand_line else "draft"
        out_entries.append({
            "id": e["id"], "title": e["title"], "area": e["area"], "tags": tags,
            "stand": stand_line, "status": status, "summary": summary,
            "qv": [q["id"] for q in qv if q["known"] and q["id"] != e["id"]],
            "qvMissing": [q["id"] for q in qv if not q["known"]],
            "inline": inline_refs, "rubrics": rubrics,
            "path": e["path"], "changed": changed.get(e["path"], ""),
        })

    overview = parse_overview(inhalt / "uebersicht.md", renderer)
    return {
        "stand": stand,
        "source": source,
        "offlineFile": OFFLINE_NAME,
        "areas": [{"code": a["code"], "name": a["name"], "entries": [e["id"] for e in a["entries"]]} for a in areas],
        "entries": out_entries,
        "overview": overview,
        "rubricOrder": [{"name": k, "slug": v} for k, v in RUBRIC_SLUGS.items()],
    }


def git(*args):
    try:
        r = subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_dates(inhalt):
    """Letzte Änderung je Datei und für den ganzen Inhalt (Unix-Zeit)."""
    log = git("log", "--format=@%ct", "--name-only", "--", rel(inhalt))
    per_file, newest, ts = {}, 0, 0
    for line in log.splitlines():
        if line.startswith("@"):
            ts = int(line[1:])
            newest = max(newest, ts)
        elif line.strip() and line.strip() not in per_file:
            per_file[line.strip()] = ts
    return per_file, newest


def repo_source(repo, branch):
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        url = git("remote", "get-url", "origin").strip()
        m = re.search(r"([^/:]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            repo = "%s/%s" % (m.group(1), m.group(2))
    if not repo:
        return None
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    base = "%s/%s" % (server, repo)
    return {
        "name": "GitHub",
        "repoUrl": base,
        "editBase": "%s/edit/%s/" % (base, branch),
        "historyBase": "%s/commits/%s/" % (base, branch),
        "blobBase": "%s/blob/%s/" % (base, branch),
        "overviewPath": "inhalt/uebersicht.md",
    }


def font_css(font_dir):
    faces = [
        ("Spectral", 400, "normal", "spectral-400.woff2"),
        ("Spectral", 400, "italic", "spectral-400i.woff2"),
        ("Spectral", 600, "normal", "spectral-600.woff2"),
        ("Spectral SC", 500, "normal", "spectralsc-500.woff2"),
        ("IBM Plex Sans", "400 600", "normal", "plexsans-var.woff2"),
    ]
    css = []
    for fam, weight, style, fn in faces:
        p = font_dir / fn
        if not p.exists():
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        css.append("@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;"
                   "src:url(data:font/woff2;base64,%s) format('woff2');}" % (fam, style, weight, b64))
    return "\n".join(css)


def main():
    ap = argparse.ArgumentParser(description="Erzeugt die Website aus inhalt/.")
    ap.add_argument("--inhalt", default=str(ROOT / "inhalt"), help="Ordner mit den Markdown-Dateien")
    ap.add_argument("--out", default=str(ROOT / "_site"), help="Zielordner")
    ap.add_argument("--stand", help='Datum für "Stand", sonst die letzte Änderung laut Versionsverlauf')
    ap.add_argument("--repo", help="besitzer/name des GitHub-Repositorys, sonst automatisch")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--suchmaschinen", action="store_true",
                    help="Suchmaschinen erlauben (ohne diese Angabe bleibt die Website aus Suchergebnissen heraus)")
    ap.add_argument("--artifact", action="store_true", help="zusätzlich artifact.html ohne Seitengerüst schreiben")
    args = ap.parse_args()

    inhalt = pathlib.Path(args.inhalt)
    changed_ts, newest = git_dates(inhalt)
    stand = args.stand or deutsches_datum(newest or datetime.datetime.now().timestamp())
    changed = {p: deutsches_datum(t) for p, t in changed_ts.items()}
    data = build(inhalt, stand, repo_source(args.repo, args.branch), changed)
    if not data["entries"]:
        sys.exit("Keine Einträge gefunden in " + str(inhalt))

    template = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__FONTS__*/", font_css(HERE / "fonts"))

    def seite(daten):
        payload = json.dumps(daten, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return template.replace("__DATA_JSON__", payload)

    page = seite(data)

    robots = "" if args.suchmaschinen else '<meta name="robots" content="noindex, nofollow">\n'
    head_extra = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
                  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                  '<meta name="description" content="%s: %d Einträge zu Fremdsprachendidaktik für '
                  'Fachseminare, Unterrichtsbesuche und Beratung, mit Querverweisen und Suche.">\n%s'
                  % (TITLE, len(data["entries"]), robots))
    full = head_extra + page.replace("<!--BODY-->", "</head>\n<body>", 1) + "\n</body>\n</html>\n"

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(full, encoding="utf-8")
    (out / OFFLINE_NAME).write_text(full, encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\n%s\n" % ("Allow: /" if args.suchmaschinen else "Disallow: /"),
                                    encoding="utf-8")
    if args.artifact:
        # Vorschau als Claude-Artifact: dort lassen sich keine Dateien herunterladen, also ohne Offline-Link.
        vorschau = dict(data, offlineFile=None)
        (out / "artifact.html").write_text(seite(vorschau).replace("<!--BODY-->", "", 1), encoding="utf-8")

    n_edges = len({tuple(sorted((e["id"], q))) for e in data["entries"] for q in e["qv"]})
    print("Einträge:", len(data["entries"]), "| Bereiche:", len(data["areas"]), "| Verbindungen:", n_edges,
          "| Stand:", stand)
    print("Website:", out / "index.html", round(len(full.encode("utf-8")) / 1024), "KB")
    if WARNUNGEN:
        print(len(WARNUNGEN), "Hinweis(e), siehe oben.")


if __name__ == "__main__":
    main()
