# Enzyklopädie Fachdidaktik Französisch

Arbeitsgrundlage der Französisch-Fachleitung für Fachseminare, Unterrichtsbesuche und Beratungsgespräche: 40 Einträge in acht Bereichen, jeder nach derselben Vorlage mit elf Rubriken und mit Querverweisen untereinander.

**Website:** https://florianchristophnowak-dot.github.io/Fachdidaktik-Franzoesisch/ (dort auch die Offline-Fassung zum Herunterladen)

## Aufbau

- `inhalt/uebersicht.md`: Benutzung, Eintragsvorlage, Systematik, Tags und Suchbegriffe
- `inhalt/A-grundlagen/` bis `inhalt/H-professionalisierung-im-referendariat/`: ein Ordner je Bereich, eine Datei je Eintrag, zum Beispiel `B3-sprechen.md`
- `werkzeug/`: erzeugt aus den Dateien die Website (`build.py`, Python ohne Zusatzpakete) und prüft sie (`browsertest.js`, `linkcheck.py`)
- `.github/workflows/website.yml`: baut und veröffentlicht die Website nach jeder Änderung
- `.github/workflows/links.yml`: prüft einmal im Monat alle Links

## Bearbeiten

1. Auf der Website im Eintrag „Auf GitHub bearbeiten“ wählen, oder hier die Datei öffnen und auf den Stift klicken.
2. Den Text ändern. „Preview“ zeigt, wie es aussieht.
3. „Commit changes…“ wählen und kurz notieren, was sich geändert hat.

Nach etwa einer Minute zeigt die Website den neuen Stand. Unter „Actions“ ist zu sehen, ob der Bau geklappt hat; Formatfehler erscheinen dort als Hinweis und in der Zusammenfassung des Laufs, die Website wird trotzdem erzeugt. Jede Änderung bleibt im Versionsverlauf und lässt sich zurücknehmen.

## Format eines Eintrags

```markdown
# B3 Sprechen

## Auf einen Blick

Kurzdefinition in wenigen Sätzen.

- **Begriffe:** …
- **Tags:** #FKK #SekI #Unterrichtsbesuch
- **Stand:** Entwurf Claude, ergänzt um Deep Research (Oktober 2026)

## Haltung

1. …

## Querverweise

A2 Aufgabenorientierung und Lernaufgaben, B5 Sprachmittlung, E4 Kooperatives Lernen und Unterrichtsgespräch
```

- Die erste Zeile ist `# Kürzel Titel`. Das Kürzel (Buchstabe A bis H und eine Nummer von 1 bis 99 ohne führende Null, zum Beispiel B3 oder E10) ist die Adresse des Eintrags.
- Die elf Rubriken der Eintragsvorlage sind Überschriften mit `##`: Auf einen Blick, Haltung, Handlungshinweise, Best Practice Französisch, Stolpersteine, Beobachten und beraten, Reflexionsfragen, Bezüge, Forschungslage, Querverweise, Bibliografie.
- Querverweise sind eine kommagetrennte Liste aus Kürzel und Titel.
- Verweise im Text heißen „siehe B3“ oder „siehe B3 und E2“; die Website macht daraus Links. Bloße Kürzel ohne „siehe“ bleiben Text, weil sie mit GeR-Niveaus wie A1 oder B2 verwechselbar sind.
- Steht im Stand „ergänzt um Deep Research“, gilt der Eintrag als eingearbeitet; die Systematik in `inhalt/uebersicht.md` muss denselben Status nennen.
- In der Zeile „Begriffe“ endet jeder Abschnitt mit (frz.) oder (engl.), getrennt durch Semikolon. Die Website zeichnet die Abschnitte dann als Französisch oder Englisch aus, damit Screenreader sie richtig aussprechen.
- Eine Zeile, die nur aus `**Fett**` besteht, ist eine Unterüberschrift, zum Beispiel **Sek I** und **Sek II** in den Handlungshinweisen. Hat eine Rubrik mindestens zwei, erscheinen sie im Inhaltsverzeichnis und haben eigene Adressen wie `#b3-handlung-2`.
- Formatierung: `**fett**`, `*kursiv*`, Listen mit `- `, nummerierte Listen mit `1. `, Tabellen mit `|`, Links als `[Text](https://…)`. Nackte Adressen wie `https://doi.org/…` werden von selbst klickbar.
- Französische Wendungen im Fließtext lassen sich mit `[la classe inversée]{fr}` auszeichnen (ebenso `{en}`, `{es}`, `{it}`, `{la}`). Die Website zeigt nur den Text, Screenreader lesen ihn in der richtigen Sprache.

## Neuer Eintrag

Im passenden Bereichsordner „Add file“ und „Create new file“ wählen, zum Beispiel `inhalt/C-sprachliche-mittel/C4-orthografie.md`, und den Inhalt nach dem Format oben schreiben. Die Website ordnet den Eintrag selbst ein. Nach der 9 geht es mit 10 weiter, zum Beispiel `E10-projektunterricht.md`; GitHub listet E10 alphabetisch vor E2, die Website ordnet nach der Nummer. Die Systematik-Tabelle in `inhalt/uebersicht.md` wird von Hand ergänzt; der Bau meldet, wenn Tabelle und Einträge nicht zusammenpassen (Kürzel, Titel, Status oder die Zahl der Einträge).

## Suche

Die Suche auf der Website findet Wörter unabhängig von Groß- und Kleinschreibung, Akzenten, Bindestrichen und der Schreibung mit ae, oe, ue oder ss. Treffer im Titel, bei den Begriffen und Tags stehen oben, je Eintrag gebündelt mit Sprungmarken zu den Rubriken. Gleichbedeutende Wörter und Abkürzungen wie UB für Unterrichtsbesuch stehen in `inhalt/uebersicht.md` unter „Suchbegriffe“ und lassen sich dort ergänzen.

## Website lokal erzeugen

`python3 werkzeug/build.py` schreibt `_site/index.html`. Die Datei lässt sich direkt im Browser öffnen, auch ohne Internet. Mit `--streng` endet der Bau mit einem Fehler, sobald es Hinweise zum Format gibt.

## Prüfungen

- **Pull Requests:** Der Bau läuft mit `--streng`. Danach schlägt `werkzeug/browsertest.js` jeden Eintrag, jeden Querschnitt, Start und Benutzung auf Handybreite auf und prüft, dass keine Skriptfehler auftreten, nichts seitlich scrollt und axe-core keine ernsten Verstöße gegen die Barrierefreiheit (WCAG 2.2 AA) findet; dazu Stichproben auf dem Desktop, in dunkler Darstellung und für die Suche. Die fertige Website liegt im Lauf unter „Artifacts“ als `website-vorschau` zum Herunterladen.
- **Links:** Am 1. jedes Monats prüft `werkzeug/linkcheck.py` alle Links, DOIs über das DOI-Verzeichnis. Sind Links sicher defekt (404, 410, unbekannte Adresse oder DOI), entsteht ein Issue „Defekte Links in der Enzyklopädie“; sind wieder alle erreichbar, schließt der nächste Lauf es. Antworten wie 403 oder 429 gelten als unklar, weil viele Verlage automatische Abrufe sperren; sie stehen nur in der Zusammenfassung des Laufs. Von Hand starten: „Actions“, „Linkprüfung“, „Run workflow“.
- **Browsertest lokal:** `npm install --no-save playwright axe-core`, `npx playwright install chromium`, dann `node werkzeug/browsertest.js _site/index.html`.

## Sichtbarkeit

Die Website ist für alle mit dem Link erreichbar, aber für Suchmaschinen gesperrt (`robots.txt` und `noindex`). Soll sie in Suchergebnissen erscheinen, im Workflow den Aufruf um `--suchmaschinen` ergänzen.

## Schriften

Spectral und IBM Plex Sans unter der SIL Open Font License 1.1, siehe `werkzeug/fonts/OFL.txt`.
