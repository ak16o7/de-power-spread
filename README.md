# DE Power Spread

Ein Handelsexperiment am deutschen Strommarkt mit ehrlicher Buchführung: Day-Ahead kaufen
oder verkaufen, zum ID-AEP glattstellen, Entscheidung um 11:00 am Vortag. Gemessen wird in
Euro nach Kosten, gegen dumme Baselines, walk-forward und live mit Zeitstempel.

**Die Frage:** Enthalten Wetterprognosen, die um 11:00 am Vortag öffentlich verfügbar sind,
Information über den Intraday-Preis, die der Day-Ahead-Preis noch nicht hat, und bleibt
nach Kosten etwas übrig?

## Warum genau dieser Trade

Mit freien Daten gibt es genau zwei Preise, zu denen man realistisch handeln kann: den
Day-Ahead-Clearingpreis als Einstieg und den ID-AEP als Ausstieg.

- **Einstieg zum Day-Ahead-Preis** geht nur mit einer Order vor der Auktion um 12:00.
  Jede spätere Entscheidung bräuchte einen Intraday-Einstiegspreis. Wer trotzdem zum
  Day-Ahead-Preis einsteigt, hat Lookahead im Backtest.
- **Ausstieg zum ID-AEP**: der mengengewichtete Preis der letzten 500 MW, die vor Lieferung
  im deutschen Continuous-Handel umgesetzt wurden (Viertelstunden- und Stundenprodukte).
  Für kleine Größen (hier 10 MW) ist das ein ehrlicher Proxy für einen Ausstieg im Endspurt.
- **Kein Geld aus dem reBAP.** Die Position ist vor Lieferung immer flach. Wer den
  Bilanzkreis offen lässt, um Ausgleichsenergie zu kassieren, verletzt die Bilanzkreistreue.
  Das ist keine Strategie, sondern ein Verstoß.

## Ergebnisse

<!-- RESULTS:START -->
_Noch nicht gerechnet. `python -m dps fetch --full && python -m dps run` schreibt diesen
Abschnitt, den Chart und `reports/REPORT.md`. Der wöchentliche Workflow hält ihn aktuell._
<!-- RESULTS:END -->

## Live-Track-Record

Jeden Tag schreibt eine GitHub Action zwischen 10:45 und 11:50 die Positionen für morgen nach
`signals/` und committet sie. Der Commit ist der Zeitstempel: Das Signal existierte vor der
Auktion. Sobald der ID-AEP veröffentlicht ist, wird mit derselben PnL-Funktion wie im Backtest
abgerechnet (`live/ledger.csv`). Signale nach 11:50 werden markiert und nie gezählt.

<!-- LIVE:START -->
_Noch kein abgerechneter Tag._
<!-- LIVE:END -->

## Methode

### Daten und wann sie bekannt sind

| Quelle | Inhalt | gilt als bekannt ab |
|---|---|---|
| ENTSO-E A44 | Day-Ahead-Preis DE-LU je Viertelstunde | 13:30 am Vortag der Lieferung |
| netztransparenz.de `IdAep` | ID-AEP je Viertelstunde (Ausstiegspreis, Label) | 00:00 zwei Tage nach Lieferung (konservativ) |
| ENTSO-E A65 | Lastprognose Day-Ahead (A01) | 10:00 am Vortag (Transparenzverordnung: spätestens 2 h vor Day-Ahead-Gate-Closure) |
| [de-power-forecast-data](https://huggingface.co/datasets/akderekaan/de-power-forecast-data) | ICON-EU und ECMWF IFS an 16 Punkten, Vintages mit `available_at` | laut `available_at` |
| dito | Installierte Leistung (Energy-Charts) | Wert von vor zwei Monaten |
| dito | Ist-Erzeugung A75 und ÜNB-Prognose A01 | nur ex post (Teil 1), nie als Feature |

Zeitraum ab 1. Oktober 2025: Seitdem läuft Day-Ahead in Viertelstunden. Ein Regime, keine
Strukturbruch-Akrobatik.

### Teil 1: Was ein Prognosefehler in Euro kostet (ex post)

Regression je Viertelstunde: Spread (ID-AEP − Day-Ahead) auf die Fehler der ÜNB-Day-Ahead-Prognose
(Ist − Prognose) für Solar, Wind an Land, Wind auf See und Last, in GW. Newey-West-Standardfehler
mit einem Tag Lags, zusätzlich getrennt nach Tageszeit. Das übersetzt Prognose-MAE in €/MWh.
Die ÜNB-Prognose erscheint um 18:00, also nach der Auktion: Sie erklärt Spreads, sie handelt nie.

### Teil 2: Die Strategie (ex ante)

- **Features um 11:00 D-1**, jede Quelle nach ihrer eigenen Verfügbarkeit gefiltert:
  - Wetter je Modell: Windleistungs-Proxy an Land und auf See, Einstrahlung, Klarheitsindex,
    Temperatur, Bewölkung, Revision gegenüber dem Stand 24 h vorher, Uneinigkeit ECMWF − ICON.
    Nur Prognosen, die mindestens 24 h vor ihrer Gültigkeit gemacht wurden; das Archiv hat nur
    solche, live wird genauso gefiltert.
  - Fundamentaldaten-Proxy: Wind- und Solar-MW (Proxy × installierte Leistung), Residuallast
    (Lastprognose minus diese).
  - Preise: Day-Ahead-Preise von D-1.
  - Spread-Historie: nur Tage, deren ID-AEP um 11:00 bekannt war (D-3 und älter).
  - Kalender: Viertelstunde, Wochentag, Feiertag, Sonnenstand.
- **Modell**: Gradient Boosting (scikit-learn, feste Einstellungen) auf den Spread, Ausreißer im
  Trainingsziel auf das 1.–99. Perzentil gekappt.
- **Handel**: Vorzeichen der Vorhersage, nur wenn ihr Betrag die Schwelle übersteigt. Die
  Schwelle wählt ein Modell, das die letzten 28 Trainingstage nicht gesehen hat, auf genau diesen
  Tagen. Danach wird auf dem ganzen Fenster neu trainiert.
- **Walk-forward**: Monat M wird mit einem Modell gehandelt, das nur Labels kennt, die vor der
  Entscheidung für M's ersten Tag bekannt waren. Der erste Testmonat braucht 60 gelabelte Tage.

### Die Latte: Baselines

| Baseline | Regel |
|---|---|
| Immer long / immer short | jede Viertelstunde, gleiche Größe |
| Vorzeichen je Viertelstunde (28 T) | Vorzeichen des mittleren Spreads derselben Uhrzeit über die letzten 28 bekannten Tage |
| Letztes bekanntes Vorzeichen | Vorzeichen derselben Viertelstunde am neuesten bekannten Tag (D-3) |

Verdient eine Baseline Geld, ist das eine Risikoprämie oder ein Kalendereffekt, kein Alpha aus
der Prognose. Das Modell zählt nur, wenn es die Baselines im Tages-PnL schlägt (t > 2 mit
Newey-West).

### Kosten

10 MW je gehandelter Viertelstunde, 0,25 €/MWh je Seite, 1 €/MWh Slippage beim Ausstieg, alles
in `dps/config.py`. Das sind Annahmen, keine Gebührenliste einer Börse; die Tabelle
„Kostenempfindlichkeit" zeigt den PnL für 0 bis 5 €/MWh Slippage. Fehlt der ID-AEP (unter
500 MW Umsatz), wird die Position mit 10 €/MWh Verlust gebucht statt still verworfen.

## Ehrliche Grenzen

- **Ausstieg zum ID-AEP ist ein Proxy.** Echte Fills streuen um den Durchschnitt der letzten
  500 MW. Nur für kleine Größen vertretbar. Tickdaten (EPEX) würden das ersetzen.
- **Ein Jahr Daten.** Saisonalität lernt das Modell nicht, die Schwelle stützt sich auf 28 Tage.
- **Wetter-Frische wechselt.** Bis Mai 2026 gibt es nur Open-Meteo-Previous-Runs (≥ 24 h bzw.
  ≥ 48 h alt), ab Juni 2026 auch mitgeschnittene Läufe. Beides war zur Entscheidung verfügbar,
  die Qualität der Features ist aber nicht über das ganze Jahr gleich.
- **Lastprognose**: Verfügbarkeit um 10:00 folgt der Verordnung, nicht einer Messung.
  `DPS_USE_LOAD_FORECAST=0` rechnet ohne sie.
- **Revisionen**: ENTSO-E und Energy-Charts liefern den heutigen Stand. Day-Ahead-Preise werden
  nicht revidiert, installierte Leistung schon (deshalb der Wert von vor zwei Monaten).
- **Keine Marktwirkung.** Die eigene Order ändert weder den Day-Ahead-Preis noch den ID-AEP.

## Lokal

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m dps demo                # ganze Pipeline auf synthetischen Daten, ohne Keys
python -m dps demo --noise --out demo-noise   # Welt ohne Signal: Modell sollte nicht handeln
python -m pytest                  # Tests, u. a. der Lookahead-Test

cp .env.example .env              # Keys eintragen
set -a; source .env; set +a
python -m dps fetch --full        # Preise, Last, ID-AEP seit 2025-10-01 nach data/
python -m dps run                 # Teil 1, Teil 2, Report, README-Abschnitt
python -m dps signal --day 2026-10-10 --force   # Signal von Hand; nach 11:50 als spät markiert
```

Die Demo-Zahlen sind erfunden. Die synthetische Welt hat ein absichtlich eingebautes Signal
(der Markt preist nur mit ICON-EU), damit man sieht, dass die Pipeline es findet. In der
`--noise`-Welt soll sie nichts finden, und genau das prüft ein Test.

**Der wichtigste Test** ist `tests/test_lookahead.py`: Er baut die Features für einen Tag,
verändert dann alles, was um 11:00 am Vortag noch nicht bekannt war (Preise des Tages, ID-AEP
ab D-2, später veröffentlichtes Wetter), und verlangt identische Features.

## Auf GitHub betreiben

1. Repository-Secrets: `ENTSOE_API_KEY`, `NTP_CLIENT_ID`, `NTP_CLIENT_SECRET`.
2. Settings → Actions → General → Workflow permissions: „Read and write".
3. `Backtest` einmal von Hand starten (füllt den Daten-Cache und den Ergebnis-Abschnitt).
4. `Live` läuft danach täglich von selbst und hält das Repo aktiv.

## Struktur

```
dps/
  config.py     alle Annahmen an einer Stelle
  util.py       Zeit: Liefertage, 11:00-Entscheidung, Bekanntheitszeiten
  entsoe.py     Day-Ahead-Preise (A44), Last (A65)
  ntp.py        ID-AEP von netztransparenz.de
  hf.py         Wetter, Kapazität, ÜNB-Daten aus dem de-power-forecast-Dataset
  store.py      lokaler Parquet-Cache mit first_seen
  fetch.py      inkrementelles Laden
  panel.py      Viertelstunden-Panel: Preise, Spread, Bekanntheitszeiten
  features.py   Features streng nach Verfügbarkeit
  explain.py    Teil 1, OLS mit Newey-West
  model.py      Modell und Schwellenwahl
  trading.py    PnL, gemeinsam für Backtest und Live
  baselines.py  die Latte
  backtest.py   Walk-forward
  metrics.py    Kennzahlen, HAC-t
  report.py     Chart, REPORT.md, README-Abschnitte
  live.py       Signal und Abrechnung
  synthetic.py  synthetische Welt für Demo und Tests
```

## Lizenz

Code: MIT. Daten: ENTSO-E Transparency Platform, netztransparenz.de (die vier deutschen ÜNB),
Open-Meteo/DWD/ECMWF und Energy-Charts über das de-power-forecast-Dataset; bitte deren
Nutzungsbedingungen beachten. Kein Anlagerat.
