# Enzyklopädie Fachdidaktik Französisch

Arbeitsgrundlage der Französisch-Fachleitung für Fachseminare, Unterrichtsbesuche und Beratungsgespräche: 41 Einträge in acht Bereichen, jeder nach derselben Vorlage mit elf Rubriken und mit Querverweisen untereinander.

**Website:** https://florianchristophnowak-dot.github.io/Fachdidaktik-Franzoesisch/ (dort auch die Offline-Fassung zum Herunterladen)

## Aufbau

- `inhalt/uebersicht.md`: Benutzung, Eintragsvorlage, Systematik und Tags
- `inhalt/A-grundlagen/` bis `inhalt/H-professionalisierung-im-referendariat/`: ein Ordner je Bereich, eine Datei je Eintrag, zum Beispiel `B3-sprechen.md`
- `werkzeug/`: erzeugt aus den Dateien die Website (Python, ohne Zusatzpakete)
- `.github/workflows/website.yml`: baut und veröffentlicht die Website nach jeder Änderung

## Bearbeiten

1. Auf der Website im Eintrag „Auf GitHub bearbeiten“ wählen, oder hier die Datei öffnen und auf den Stift klicken.
2. Den Text ändern. „Preview“ zeigt, wie es aussieht.
3. „Commit changes…“ wählen und kurz notieren, was sich geändert hat.

Nach etwa einer Minute zeigt die Website den neuen Stand. Unter „Actions“ ist zu sehen, ob der Bau geklappt hat; Formatfehler erscheinen dort als Hinweis, die Website wird trotzdem erzeugt. Jede Änderung bleibt im Versionsverlauf und lässt sich zurücknehmen.

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
- Steht im Stand „ergänzt um Deep Research“, zeigt die Systematik den Eintrag als eingearbeitet.
- Formatierung: `**fett**`, `*kursiv*`, Listen mit `- `, nummerierte Listen mit `1. `, Tabellen mit `|`, Links als `[Text](https://…)`.

## Neuer Eintrag

Im passenden Bereichsordner „Add file“ und „Create new file“ wählen, zum Beispiel `inhalt/C-sprachliche-mittel/C4-orthografie.md`, und den Inhalt nach dem Format oben schreiben. Die Website ordnet den Eintrag selbst ein. Nach der 9 geht es mit 10 weiter, zum Beispiel `E10-projektunterricht.md`; GitHub listet E10 alphabetisch vor E2, die Website ordnet nach der Nummer. Die Systematik-Tabelle in `inhalt/uebersicht.md` wird von Hand ergänzt.

## Website lokal erzeugen

`python3 werkzeug/build.py` schreibt `_site/index.html`. Die Datei lässt sich direkt im Browser öffnen, auch ohne Internet.

## Sichtbarkeit

Die Website ist für alle mit dem Link erreichbar, aber für Suchmaschinen gesperrt (`robots.txt` und `noindex`). Soll sie in Suchergebnissen erscheinen, im Workflow den Aufruf um `--suchmaschinen` ergänzen.

## Schriften

Spectral und IBM Plex Sans unter der SIL Open Font License 1.1, siehe `werkzeug/fonts/OFL.txt`.
