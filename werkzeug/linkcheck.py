#!/usr/bin/env python3
"""Prüft die Links in inhalt/ und schreibt einen Bericht in Markdown.

Läuft einmal im Monat über GitHub Actions (.github/workflows/links.yml). Dort wird bei sicher defekten
Links ein Issue angelegt oder aktualisiert.

- DOIs (https://doi.org/…) werden beim DOI-Verzeichnis nachgefragt, nicht beim Verlag.
- Sicher defekt: 404 oder 410, unbekannte Adresse, unbekannte DOI. Dann endet das Skript mit Code 1.
- Unklar: 401, 403, 429, Serverfehler, Zeitüberschreitung. Viele Verlage sperren automatische Abrufe;
  diese Links stehen im Bericht, lösen aber kein Issue aus.

Aufruf (im Repository):
    python3 werkzeug/linkcheck.py                      # Bericht auf dem Bildschirm
    python3 werkzeug/linkcheck.py --bericht links.md   # Bericht zusätzlich in eine Datei
Nur Python-Standardbibliothek.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build import BARE_RE, LINK_RE, bare_url  # noqa: E402  (gleiche Regeln wie die Website)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TIMEOUT = 25
DOI_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/(10\.[^\s]+)$", re.I)


def links_finden(inhalt):
    """Alle Adressen mit den Dateien und Zeilen, in denen sie stehen."""
    fundstellen = {}
    for datei in sorted(inhalt.resolve().rglob("*.md")):
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            urls = [m.group(2) for m in LINK_RE.finditer(zeile)]
            rest = LINK_RE.sub(" ", zeile)
            urls += [bare_url(m.group(0)) for m in BARE_RE.finditer(rest)]
            for url in urls:
                fundstellen.setdefault(url, []).append("%s:%d" % (datei.relative_to(ROOT).as_posix(), nr))
    return fundstellen


def abrufen(url, methode="GET"):
    req = urllib.request.Request(url, method=methode, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "de,en;q=0.8,fr;q=0.6"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read(200000) if methode == "GET" else b""
        return r.status, body


def pruefe_doi(doi):
    api = "https://doi.org/api/handles/" + urllib.parse.quote(urllib.parse.unquote(doi), safe="/")
    try:
        status, body = abrufen(api)
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read(20000)
    except (urllib.error.URLError, OSError) as e:
        return "unklar", "DOI-Verzeichnis nicht erreichbar (%s)" % getattr(e, "reason", e)
    try:
        code = json.loads(body.decode("utf-8", "replace")).get("responseCode")
    except ValueError:
        code = None
    if code == 1:
        return "ok", "DOI bekannt"
    if code == 100 or status == 404:
        return "defekt", "DOI unbekannt"
    return "unklar", "DOI-Verzeichnis antwortet mit %s" % status


def pruefe_url(url):
    try:
        m = DOI_RE.match(url)
        return pruefe_doi(m.group(1)) if m else pruefe_seite(url)
    except Exception as e:  # noqa: BLE001  (ein Link soll den Lauf nicht abbrechen)
        return "unklar", type(e).__name__


def pruefe_seite(url):
    letzte = None
    for versuch in range(2):
        try:
            status, _ = abrufen(url)
            return "ok", str(status)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return "defekt", "HTTP %d" % e.code
            letzte = ("unklar", "HTTP %d" % e.code)
            if e.code not in (429, 500, 502, 503, 504):
                break
        except urllib.error.URLError as e:
            grund = e.reason
            if isinstance(grund, socket.gaierror):
                letzte = ("defekt", "Adresse unbekannt")
            elif isinstance(grund, ssl.SSLError):
                letzte = ("unklar", "Zertifikat: %s" % grund)
            else:
                letzte = ("unklar", str(grund))
        except (socket.timeout, TimeoutError):
            letzte = ("unklar", "Zeitüberschreitung")
        time.sleep(3)
    return letzte


def main():
    ap = argparse.ArgumentParser(description="Prüft die Links in inhalt/.")
    ap.add_argument("--inhalt", default=str(ROOT / "inhalt"))
    ap.add_argument("--bericht", help="Bericht zusätzlich in diese Datei schreiben")
    ap.add_argument("--parallel", type=int, default=8)
    args = ap.parse_args()

    fundstellen = links_finden(pathlib.Path(args.inhalt))
    ergebnisse = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for url, erg in zip(fundstellen, pool.map(pruefe_url, fundstellen)):
            ergebnisse[url] = erg

    defekt = {u: e for u, e in ergebnisse.items() if e[0] == "defekt"}
    unklar = {u: e for u, e in ergebnisse.items() if e[0] == "unklar"}
    zeilen = ["## Linkprüfung", "",
              "%d Adressen geprüft: %d erreichbar, %d defekt, %d unklar." % (
                  len(ergebnisse), len(ergebnisse) - len(defekt) - len(unklar), len(defekt), len(unklar)), ""]
    if defekt:
        zeilen += ["### Defekt", "", "Bitte im Eintrag ersetzen oder entfernen.", ""]
        zeilen += ["- %s (%s): %s" % (u, e[1], ", ".join(fundstellen[u])) for u, e in sorted(defekt.items())]
        zeilen.append("")
    if unklar:
        zeilen += ["### Unklar", "", "Oft sperrt der Server nur automatische Abrufe. Im Browser prüfen.", ""]
        zeilen += ["- %s (%s): %s" % (u, e[1], ", ".join(fundstellen[u])) for u, e in sorted(unklar.items())]
        zeilen.append("")
    text = "\n".join(zeilen)
    print(text)
    if args.bericht:
        pathlib.Path(args.bericht).write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.exit(1 if defekt else 0)


if __name__ == "__main__":
    main()
