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
Testzeitraum 2026-01-01 bis 2026-10-06 (279 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg zum ID-AEP. Kosten: 0.25 €/MWh je Seite, 1.0 €/MWh Slippage beim Ausstieg, 10.0 €/MWh Strafe, wenn der ID-AEP fehlt.

![PnL](reports/pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +155 879 | +4.02 | 38 770 | 51 % | 2.28 | 2.11 | -43 825 | -31 848 | 0 |
| Immer long | +186 998 | +2.79 | 66 950 | 44 % | 1.88 | 1.36 | -129 624 | -48 138 | 0 |
| Immer short | -387 848 | -5.79 | 66 950 | 50 % | -3.91 | -2.82 | -390 414 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +104 937 | +1.57 | 66 950 | 49 % | 1.54 | 1.27 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +68 219 | +1.02 | 66 932 | 49 % | 0.92 | 0.81 | -39 963 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -111.5 | -0.19 | +382.0 | 1.06 |
| Immer short | +1 948.8 | 3.80 | +1 193.5 | 3.65 |
| Vorzeichen je Viertelstunde (28 T) | +182.6 | 0.50 | +188.2 | 1.00 |
| Letztes bekanntes Vorzeichen | +314.2 | 1.18 | +498.3 | 2.81 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|
| Modell | +155 879 | +31 719 | +127 739 (2.9) | +119 351 (3.3) | +96 990 (3.1) |
| Immer long | +186 998 | +26 937 | +97 387 (0.9) | +12 781 (0.1) | -69 993 (-0.9) |
| Immer short | -387 848 | -27 012 | -298 237 (-2.9) | -213 631 (-2.4) | -130 857 (-1.7) |
| Vorzeichen je Viertelstunde (28 T) | +104 937 | +26 937 | +71 805 (1.4) | +66 845 (1.6) | +46 995 (1.2) |
| Letztes bekanntes Vorzeichen | +68 219 | +50 803 | +951 (0.0) | -19 666 (-0.5) | -30 335 (-0.9) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh) von

| Strategie | 0.0 | 1.0 | 2.0 | 5.0 |
|---|---:|---:|---:|---:|
| Modell | +194 649 | +155 879 | +117 109 | +799 |
| Immer long | +253 948 | +186 998 | +120 048 | -80 802 |
| Immer short | -320 898 | -387 848 | -454 798 | -655 648 |
| Vorzeichen je Viertelstunde (28 T) | +171 887 | +104 937 | +37 987 | -162 863 |
| Letztes bekanntes Vorzeichen | +135 152 | +68 219 | +1 287 | -199 511 |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -14 481 | 332 | 30 | 90 |
| 2026-02 | +1 952 | 412 | 30 | 121 |
| 2026-03 | +2 968 | 3 022 | 10 | 149 |
| 2026-04 | +43 800 | 4 742 | 5 | 180 |
| 2026-05 | +5 279 | 6 752 | 2 | 210 |
| 2026-06 | +26 909 | 5 592 | 5 | 241 |
| 2026-07 | +24 093 | 1 835 | 15 | 271 |
| 2026-08 | +32 608 | 7 440 | 0 | 302 |
| 2026-09 | +44 012 | 7 200 | 0 | 333 |
| 2026-10 | -11 261 | 1 440 | 0 | 363 |

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4.58 | 3.2 | +2.05 | 2.5 | +4.71 | +3.84 | +10.20 | +1.92 | +10.52 |
| Solar | -7.90 | -6.1 | -7.64 | -12.9 | – | -11.47 | -7.69 | -7.55 | -42.41 |
| Wind an Land | -3.81 | -1.7 | -4.79 | -5.9 | -6.18 | -8.06 | +5.00 | -7.00 | -11.11 |
| Wind auf See | -5.92 | -2.2 | -4.72 | -4.0 | -9.30 | -8.02 | -3.58 | -10.49 | -8.44 |
| Last | +0.75 | 1.1 | -0.02 | -0.1 | -0.46 | -1.08 | +1.86 | +2.42 | -0.74 |

n = 35 712 Viertelstunden, R² = 0.03, gekappt 0.12. t mit Newey-West-Standardfehlern (96 Lags). „Gekappt": Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt).


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
| ENTSO-E A44, ohne Key: Energy-Charts (SMARD) | Day-Ahead-Preis DE-LU je Viertelstunde | 13:30 am Vortag der Lieferung |
| netztransparenz.de `IdAep`, ohne Zugang: CSV-Download der Webseite | ID-AEP je Viertelstunde (Ausstiegspreis, Label) | 00:00 zwei Tage nach Lieferung (konservativ) |
| ENTSO-E A65, ohne Key: Energy-Charts | Lastprognose Day-Ahead (A01) | 10:00 am Vortag (Transparenzverordnung: spätestens 2 h vor Day-Ahead-Gate-Closure) |
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

python -m dps fetch --full        # Preise, Last, ID-AEP seit 2025-10-01 nach data/ (geht ohne Keys)
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

1. Repository-Secrets: `ENTSOE_API_KEY`, `NTP_CLIENT_ID`, `NTP_CLIENT_SECRET`. Ohne sie läuft alles
   über Energy-Charts und den CSV-Download von netztransparenz.de; für den Dauerbetrieb sind die
   offiziellen APIs aber robuster (`cp .env.example .env` für lokal).
2. Settings → Actions → General → Workflow permissions: „Read and write".
3. `Backtest` einmal von Hand starten (füllt den Daten-Cache und den Ergebnis-Abschnitt).
4. `Live` läuft danach täglich von selbst und hält das Repo aktiv.

## Struktur

```
dps/
  config.py     alle Annahmen an einer Stelle
  util.py       Zeit: Liefertage, 11:00-Entscheidung, Bekanntheitszeiten
  entsoe.py     Day-Ahead-Preise (A44), Last (A65)
  energycharts.py  dasselbe ohne Key (Energy-Charts, SMARD)
  ntp.py        ID-AEP von netztransparenz.de (WebAPI oder CSV-Download)
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
