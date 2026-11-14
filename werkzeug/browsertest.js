// Prüft die erzeugte Website im Browser, bevor ein Pull Request übernommen wird.
//
// - Jeder Eintrag, jeder Querschnitt, Start und Benutzung auf Handybreite (360 Pixel):
//   keine Skriptfehler, kein seitliches Scrollen, keine ernsten oder kritischen Verstöße laut axe-core.
// - Auf dem Desktop und in dunkler Darstellung: Stichproben mit axe-core.
// - Suche, Tastaturbedienung, Fenstertitel und Fokus nach einem Seitenwechsel.
//
// Aufruf: node werkzeug/browsertest.js _site/index.html
// Braucht die npm-Pakete playwright und axe-core (der Workflow installiert sie).
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const datei = path.resolve(process.argv[2] || '_site/index.html');
const BASE = pathToFileURL(datei).href;
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const fehler = [];
let geprueft = 0;

function fail(msg) { fehler.push(msg); console.log('FEHLER  ' + msg); }

async function axe(page, label) {
  if (!(await page.evaluate(() => !!window.axe))) await page.addScriptTag({ content: AXE });
  const v = await page.evaluate(async (tags) => {
    const r = await window.axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] });
    return r.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical')
      .map((x) => x.id + ' (' + x.nodes.length + '×): ' + x.nodes.slice(0, 2).map((n) => n.target.join(' ')).join(', '));
  }, AXE_TAGS);
  v.forEach((x) => fail(label + ': ' + x));
}

// Wechselt die Ansicht über die Adresse und wartet, bis die neue Ansicht gezeichnet ist.
async function gehe(page, hash) {
  await page.evaluate((h) => {
    const alt = document.querySelector('#view > *');
    if (alt) alt.setAttribute('data-alt', '');
    location.hash = h;
  }, hash);
  await page.waitForFunction(() => !document.querySelector('#view > [data-alt]') && document.querySelector('#view h1'));
}

async function seitlich(page, label) {
  const w = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  if (w[0] > w[1] + 1) fail(label + ': seitliches Scrollen (' + w[0] + ' statt ' + w[1] + ' Pixel breit)');
}

(async () => {
  const browser = await chromium.launch();
  const meldungen = [];
  function beobachte(page) {
    page.on('pageerror', (e) => meldungen.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error') meldungen.push(m.text()); });
  }

  // ---------- Handy: alles einmal aufschlagen ----------
  const handy = await browser.newContext({ viewport: { width: 360, height: 740 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
  const m = await handy.newPage();
  beobachte(m);
  await m.goto(BASE);
  await m.waitForSelector('.areas');
  const ids = await m.evaluate(() => Array.from(document.querySelectorAll('.areas a[data-id]')).map((a) => a.getAttribute('data-id').toLowerCase()));
  await gehe(m, 'querschnitt');
  const quer = await m.evaluate(() => Array.from(document.querySelectorAll('.q-rubs a')).map((a) => a.getAttribute('href').slice(1)));
  const ziele = ['start', 'benutzung'].concat(quer, ids);
  for (const h of ziele) {
    const vorher = meldungen.length;
    await gehe(m, h);
    await seitlich(m, '#' + h + ' (360 px)');
    await axe(m, '#' + h + ' (360 px)');
    if (meldungen.length > vorher) fail('#' + h + ': Skriptfehler ' + meldungen.slice(vorher).join(' | '));
    geprueft++;
  }
  // Eintrag öffnen: Fenstertitel und Fokus auf der Überschrift
  await gehe(m, 'start');
  await gehe(m, ids[0]);
  const t = await m.evaluate(() => ({ title: document.title, fokus: document.activeElement && document.activeElement.tagName, h1: document.querySelector('#view h1').textContent }));
  if (t.title.indexOf(t.h1.replace(/^([A-H]\d+)/, '$1 ')) !== 0) fail('Fenstertitel nennt den Eintrag nicht: ' + t.title);
  if (t.fokus !== 'H1') fail('Nach dem Seitenwechsel liegt der Fokus auf ' + t.fokus + ' statt auf der Überschrift');
  await handy.close();

  // ---------- Desktop und dunkel: Stichproben ----------
  const desk = await browser.newContext({ viewport: { width: 1366, height: 860 }, deviceScaleFactor: 1 });
  const d = await desk.newPage();
  beobachte(d);
  await d.goto(BASE);
  await d.waitForSelector('.areas');
  for (const h of ['start', ids[Math.floor(ids.length / 2)], 'querschnitt-stolpersteine', 'benutzung']) {
    await gehe(d, h);
    await axe(d, '#' + h + ' (Desktop)');
    geprueft++;
  }
  await d.emulateMedia({ colorScheme: 'dark' });
  for (const h of ['start', ids[ids.length - 1], 'querschnitt-reflexion']) {
    await gehe(d, h);
    await axe(d, '#' + h + ' (dunkel)');
    geprueft++;
  }
  await d.emulateMedia({ colorScheme: 'light' });

  // ---------- Suche ----------
  async function suche(q) {
    await d.fill('#q', q);
    await d.waitForTimeout(60);
    return d.evaluate(() => Array.from(document.querySelectorAll('#results .res-g .where .c')).map((c) => c.textContent));
  }
  await gehe(d, 'start');
  const erst = await suche(ids[0].toUpperCase());
  if (erst[0] !== ids[0].toUpperCase()) fail('Suche nach dem Kürzel ' + ids[0].toUpperCase() + ' zeigt zuerst ' + (erst[0] || 'nichts'));
  const titel = await d.evaluate((id) => document.querySelector('.areas a[data-id="' + id + '"] .t').textContent, ids[1].toUpperCase());
  const wort = titel.split(/\s+/).sort((a, b) => b.length - a.length)[0];
  const treffer = await suche(wort);
  if (treffer.indexOf(ids[1].toUpperCase()) < 0) fail('Suche nach „' + wort + '“ findet ' + ids[1].toUpperCase() + ' nicht');
  if ((await suche('xqzjw')).length) fail('Suche nach Unsinn liefert Treffer');
  await suche(wort);
  await d.keyboard.press('ArrowDown');
  const aktiv = await d.evaluate(() => document.getElementById('q').getAttribute('aria-activedescendant'));
  if (!aktiv) fail('Pfeiltaste in der Suche setzt aria-activedescendant nicht');
  await d.keyboard.press('Enter');
  await d.waitForFunction(() => /^#[a-h]\d/.test(location.hash) && document.querySelector('#view .entry'));
  const marks = await d.waitForFunction(() => document.querySelectorAll('mark.found').length, null, { timeout: 3000 })
    .then((h) => h.jsonValue()).catch(() => 0);
  if (!marks) fail('Nach dem Öffnen eines Treffers ist nichts markiert');
  if (meldungen.length) fail('Skriptfehler: ' + meldungen.join(' | '));
  await desk.close();
  await browser.close();

  console.log('\n' + geprueft + ' Ansichten geprüft, ' + (fehler.length ? fehler.length + ' Fehler.' : 'alles in Ordnung.'));
  const ziel = process.env.GITHUB_STEP_SUMMARY;
  if (ziel) {
    const z = ['## Browsertest', '', geprueft + ' Ansichten geprüft (Handybreite, Desktop, dunkel).', ''];
    if (fehler.length) z.push('### ' + fehler.length + ' Fehler', '', ...fehler.map((f) => '- ' + f));
    else z.push('Keine Skriptfehler, kein seitliches Scrollen, keine ernsten Verstöße laut axe-core.');
    fs.appendFileSync(ziel, z.join('\n') + '\n');
  }
  process.exit(fehler.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
