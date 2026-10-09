# DE Power Spread

Systematische Day-Ahead/Intraday-Spread-Strategie für DE-LU auf Viertelstundenbasis.
Positioniert wird je Viertelstunde in der Day-Ahead-Auktion (Entscheidung 11:00 D-1, vor
Gate Closure 12:00), glattgestellt im kontinuierlichen Intraday-Handel, bewertet zum ID-AEP.
Das Signal kommt ausschließlich aus frei verfügbaren Daten, im Kern aus NWP-Prognosen
(ICON-EU, ECMWF IFS). Evaluiert walk-forward gegen naive Baselines mit vorab festgelegtem
Erfolgskriterium, seit Oktober 2026 zusätzlich als Live-Track-Record mit öffentlichem
Zeitstempel.

**Hypothese.** Der DA-Preis bildet die Erwartung zum Auktionszeitpunkt ab; der Spread
ID − DA wird vor allem von Prognosefehlern bei Wind und PV getrieben (Ex-post-Regression
unten). Geprüft wird, ob die um 11:00 verfügbaren Prognosen (Wetterlage, Revisionen,
Dissens zwischen ICON und ECMWF) systematische Information über das Vorzeichen des Spreads
enthalten, die nach Kosten verwertbar ist.

## Ergebnis

<!-- RESULTS:START -->
Out-of-sample 2026-01-01 bis 2026-10-07 (280 Liefertage), Walk-forward mit monatlichem Refit, 10 MW je gehandelter Viertelstunde, Kosten 0,25 €/MWh je Leg plus 1,0 €/MWh Slippage gegen ID-AEP. Stand 2026-10-09.

| Kennzahl | Modell |
|---|---:|
| Netto-PnL | +156 336 € |
| Netto je gehandelter MWh | +4,08 € |
| Gehandeltes Volumen | 38 332 MWh |
| t-Wert Tages-PnL (Newey-West) | 2,41 |
| Sharpe p. a. (Tages-PnL) | 2,62 |
| Max. Drawdown | -36 555 € |
| Break-even-Slippage gegen ID-AEP | 5,1 €/MWh |
| Netto-PnL, Spread auf ±200 €/MWh gekappt | +143 306 € (t 3,92) |

**Vorab festgelegtes Kriterium** (Tages-PnL schlägt jede Baseline mit HAC-t > 2): **nicht erfüllt**. Signifikant besser als „Immer short“ (t 3,57); nicht signifikant gegen „Immer long“ (t -0,22), „Vorzeichen je Viertelstunde (28 T)“ (t 0,64), „Letztes bekanntes Vorzeichen“ (t 1,07).

- „Immer long“ liegt ungekappt bei +189 252 €, mit Spread-Cap ±200 €/MWh bei +15 036 €: überwiegend Spike-Prämie. Mit gekappten Spreads liegt das Modell vorn, aber nicht signifikant (t 1,31).
- Der Edge kommt aus den NWP-Features: ohne sie -55 083 € (t -0,93).
- Asymmetrisch und konzentriert: Long +171 740 €, Short -15 405 €; ohne die 10 besten Tage +21 843 €.
- Die vor dem ersten Backtest fixierte Erstversion liegt bei +101 647 € (t 1,54); die Änderungen danach sind unten dokumentiert.

**Einordnung:** Messbarer, aber schwacher Edge, statistisch nicht von einfachen Baselines zu trennen und abhängig von der Ausführungsqualität gegen den Index.

![Kumulierter Netto-PnL, Modell gegen Baselines](reports/pnl.png)

| Strategie | Netto € | €/MWh | t (HAC) | Max. DD € | Netto €, Spread ±200 gekappt |
|---|---:|---:|---:|---:|---:|
| **Modell** | +156 336 | +4,08 | 2,41 | -36 555 | +143 306 |
| Immer long | +189 252 | +2,82 | 1,38 | -129 624 | +15 036 |
| Immer short | -390 822 | -5,82 | -2,84 | -398 874 | -216 606 |
| Vorzeichen je Viertelstunde (28 T) | +103 275 | +1,54 | 1,25 | -57 401 | +65 184 |
| Letztes bekanntes Vorzeichen | +65 797 | +0,98 | 0,78 | -39 963 | -22 089 |

**Robustheit** (Auszug; gleiche Splits, gleiche Kosten):

| Variante | Netto € | t (HAC) |
|---|---:|---:|
| Erstversion (vor dem ersten Backtest fixiert) | +101 647 | 1,54 |
| **Hauptmodell** | +156 336 | 2,41 |
| mit DA-Lastprognose als Feature | +159 374 | 2,18 |
| ohne NWP-Features | -55 083 | -0,93 |
| NWP nur im Vintage des Previous-Runs-Archivs | +139 865 | 2,26 |
| fixe Schwelle 2 €/MWh statt Auswahl | +152 752 | 1,80 |
| Teststart Dezember 2025 | +132 326 | 1,95 |
| Einzel-Fit statt Seed-Mittel (Seeds 0–4) | +52 924 bis +160 814 | 0,93 bis 2,54 |

Alle 27 Varianten, Kostensensitivität, Long/Short, Monatswerte, Ex-post-Regression und Datenprüfung: [reports/REPORT.md](reports/REPORT.md).

**Ex post:** 1 GW positiver Prognosefehler (Ist minus ÜNB-Day-Ahead-Prognose) verschiebt den Spread um -7,6 €/MWh Solar (t -13,0), -4,8 €/MWh Wind onshore (t -5,9), -4,7 €/MWh Wind offshore (t -4,0) (Spread auf ±200 €/MWh gekappt, Newey-West).

<!-- RESULTS:END -->

## Setup

### Trade und PnL

- **Entry:** preisunabhängiges Gebot in der SDAC-Auktion, 10 MW je Viertelstunde, long (Kauf)
  oder short (Verkauf). MTU 15 Minuten seit dem 1. Oktober 2025; ab dann beginnt die Historie.
- **Exit:** Close-out im Continuous Intraday vor Lieferung, bewertet zum ID-AEP. Der ID-AEP ist
  der mengengewichtete Preis der letzten Geschäfte des Viertelstundenprodukts bis 500 MW,
  bei zu wenig Umsatz mit dem Stundenprodukt aufgefüllt, also der Index der reBAP-Kopplung
  (inhaltlich ID500).
- **PnL je Viertelstunde:** Position × (ID-AEP − DA) × 2,5 MWh, abzüglich 0,25 €/MWh je Leg
  und 1 €/MWh Slippage gegen den Index. Fehlt der ID-AEP (unter 500 MW Umsatz), werden
  10 €/MWh Verlust gebucht statt die Position zu verwerfen.
- **Kein Imbalance-Exposure:** Der Bilanzkreis ist vor Lieferung immer ausgeglichen; es gibt
  keine Spekulation auf den reBAP.
- **Kritische Annahme:** Ausführung zum Index plus Slippage. Der ID-AEP ist nicht handelbar;
  echte Fills hängen von Timing, Orderbuchtiefe und Geld-Brief-Spanne ab. Die
  Break-even-Slippage im Ergebnis zeigt, wie viel Ausführungsverlust gegen den Index der Edge
  verträgt. Intraday-Tickdaten (EPEX) würden die Annahme ersetzen; frei verfügbar ist nur der
  Index.

### Informationsstand um 11:00 D-1

| Daten | Quelle | verwendet ab |
|---|---|---|
| DA-Preise DE-LU je Viertelstunde | ENTSO-E A44, ohne Key SMARD über Energy-Charts | 13:30 am Tag vor Lieferung; als Feature die Kurve von D-1 |
| ID-AEP je Viertelstunde | netztransparenz.de (WebAPI oder CSV-Download) | 00:00 an D+2 (konservativ, beobachtet: D+1); jüngstes Label zur Entscheidung ist D-3 |
| NWP ICON-EU und ECMWF IFS an 16 Punkten (Wind in Nabenhöhe, GHI, Temperatur, Bewölkung) | [de-power-forecast-data](https://huggingface.co/datasets/akderekaan/de-power-forecast-data) (Open-Meteo) | laut `available_at`, nur Vorlauf ≥ 24 h; Previous-Runs-Archiv bis 30.09.2026, vollständige Läufe ab 10.06.2026 |
| Installierte Leistung Wind und PV | Energy-Charts | Monat M−2 |
| Ist-Erzeugung (A75), ÜNB-DA-Prognose Wind/PV (A69, 18:00 D-1) | ENTSO-E über das Dataset | nur ex post, nie als Feature |
| Last und DA-Lastprognose (A65) | ENTSO-E, ohne Key Energy-Charts | nur ex post; kein Feature, weil Veröffentlichungs- und Revisionszeitpunkt nicht belegbar sind |

### Features

- **NWP je Modell:** Kapazitätsfaktor-Proxy onshore und offshore (generische Leistungskurve),
  GHI, Clear-Sky-Index, Temperatur, Bewölkung; Revision gegenüber dem Stand 24 h zuvor;
  Dissens ECMWF − ICON.
- **Leistungs-Proxy:** Wind- und PV-MW aus Kapazitätsfaktor bzw. GHI und installierter Leistung.
- **DA-Kurve D-1:** Preis der Viertelstunde, Tagesmittel, Standardabweichung, Shape.
- **Spread-Historie** (nur veröffentlichte Tage): Slot-Mittel über 14 und 28 Tage, letzter
  bekannter Slot, 7-Tage-Mittel und -Betragsmittel.
- **Kalender:** Viertelstunde, Wochentag, Wochenende oder bundesweiter Feiertag, Sonnenstand.

### Modell und Entscheidungsregel

- **Modell:** HistGradientBoostingRegressor auf den Spread, Trainingsziel auf das
  1./99. Perzentil winsorisiert, feste Hyperparameter. Die Prognose ist das Mittel aus fünf
  Seeds. Der Seed steuert nur den Early-Stopping-Holdout, Einzel-Fits streuen aber stark
  (Robustheit).
- **Signal:** Position = Vorzeichen der Prognose, wenn |Prognose| die Schwelle übersteigt. Die
  Schwelle kommt aus {2, 5, 10, 15, 20, 30} €/MWh, liegt also nie unter den Round-trip-Kosten
  von 1,5 €/MWh, und wird monatlich auf den letzten 28 gelabelten Tagen gewählt, mit einem
  Modell, das diese Tage nicht gesehen hat.
- **Walk-forward:** monatlicher Refit; Labels nur, soweit sie zur Entscheidung für den ersten
  Liefertag des Monats veröffentlicht waren. Erster Testmonat mit mindestens 60 gelabelten
  Tagen ist Januar 2026.
- **Data Guard:** Kein Handel ohne DA-Preise von D-1, Spread-Historie und beide NWP-Modelle
  oder wenn die jüngste Prognose älter als 30 h ist. Im Backtest und live identisch.

## Validierung

- **Baselines:**

  | Baseline | Regel |
  |---|---|
  | Immer long / Immer short | jede Viertelstunde dieselbe Richtung |
  | Vorzeichen je Viertelstunde (28 T) | Vorzeichen des mittleren Spreads im selben Slot über die letzten 28 bekannten Tage |
  | Letztes bekanntes Vorzeichen | Vorzeichen des Spreads im selben Slot am jüngsten bekannten Tag (D-3) |

- **Erfolgskriterium,** seit dem ersten Commit festgelegt: Das Modell schlägt jede Baseline im
  Tages-PnL mit HAC-t > 2 (Newey-West, 5 Lags).
- **Lookahead-Test:** Alle nach der Entscheidung veröffentlichten Daten werden verfälscht: DA
  ab Liefertag, ID-AEP ab D-2, Lastprognosen späterer Tage, noch nicht nutzbare
  Kapazitätsmonate, NWP aller Vintages und Variablen. Die Features müssen identisch bleiben.
  Geprüft werden auch der Tag der Zeitumstellung (100 Viertelstunden) und eine frühe
  Live-Entscheidung. Per Mutationstest ist belegt, dass der Test eingebaute Fehler findet.
- **NWP-Zeitstempel gegen die Daten verifiziert:** Archivwerte lassen sich exakt einzelnen
  Modellläufen zuordnen; keiner stammt aus einem Lauf mit kürzerem Vorlauf als angegeben. Die
  gemessenen Veröffentlichungszeiten der live mitgeschnittenen Läufe liegen unter den
  angesetzten Grenzen.
- **Robustheit:** alle getesteten Varianten auf denselben Splits: Schwellenregeln, Sizing, Loss,
  Regularisierung, Bagging, ein zweistufiges Modell über die ÜNB-Prognosefehler,
  Feature-Ablationen, NWP-Vintage, Teststart, Seeds. Vollständig in
  [reports/REPORT.md](reports/REPORT.md).
- **Reproduzierbarkeit:** `reports/backtest.json` hält Code-Commit, Revision des Datasets und
  Stand des Datencaches fest.

### Änderungen nach dem ersten Backtest

1. **DA-Lastprognose als Feature entfernt.** Ihr Zeitstempel ist nicht belegbar, ihr Beitrag
   nicht messbar.
2. **Seed-Mittel statt Einzel-Fit.** Ein Einzel-Fit streut über die Seeds zwischen etwa
   +45k € und +176k €.
3. **Schwelle nie unter den Kosten** (seit 9. Oktober 2026). Vorher enthielt das Grid 0 €/MWh;
   in drei Testmonaten wurde damit jede Viertelstunde gehandelt, auch bei Prognosen von wenigen
   Cent und damit erwarteter Marge unter den Kosten. Effekt: rund 8 % weniger Volumen, höhere
   Marge je MWh, PnL praktisch unverändert.
4. **Bugfix:** Die installierte Leistung wurde nach UTC-Monat statt nach lokalem Liefermonat
   nachgeschlagen.

Aufgefallen ist all das bei der Prüfung der Testergebnisse; begründet ist es unabhängig von der
Höhe des PnL. Alle drei Modelländerungen haben den Test-PnL erhöht oder unverändert gelassen.
Die Erstversion ist deshalb im Ergebnis und in der Robustheitstabelle ausgewiesen, die alte
Schwellenregel als eigene Variante. Weitere Änderungen am Modell sind nicht vorgesehen; ab hier
entscheidet der Live-Track-Record.

## Grenzen

- **Ausführung:** Index statt Fills. Die Break-even-Slippage ist die entscheidende Zahl. Ob sie
  erreichbar ist, lässt sich nur mit Orderbuchdaten beantworten.
- **Stichprobe:** gut neun Monate out-of-sample, ein Saisonzyklus, fette Ränder. Ein t um 2 ist
  wenig belastbar.
- **Profil:** Der Edge ist long-lastig und hängt an wenigen Spike-Tagen.
- **NWP-Vintage nicht homogen:** Ab Mitte Juni 2026 gibt es vollständige Läufe mit frischeren
  Prognosen, seit Oktober nur noch diese. Die Variante, die das auf das Archiv-Vintage
  zurückschneidet, liegt nahe am Hauptergebnis.
- **Signal, kein Handelssystem:** Das Setup prüft, ob ein Edge existiert. Für den Handel
  fehlen eine Kalibrierung der Prognose auf den erwarteten Spread (im Mittel kommt nur etwa ein
  Viertel der prognostizierten Abweichung an), Positionsgrößen nach Erwartungswert und Risiko,
  Limits und eine explizite Behandlung des Tail-Risikos, etwa über Quantilprognosen. Bewusst
  nicht nachgerüstet: Jede dieser Stellschrauben auf denselben neun Monaten zu justieren, wäre
  Fitting am Testzeitraum.
- **Kleinere Punkte:** Die installierte Leistung ist der heutige Datenstand (Nachmeldungen sind
  klein). Es gibt nur bundesweite Feiertage. Marktwirkung wird nicht modelliert (10 MW
  gegenüber einem 500-MW-Index). Es gibt keinen Portfoliokontext und keine Intraday-Auktionen
  (IDA).

## Live-Track-Record

- **Ablauf:** Täglich im Fenster 10:45–11:50 erzeugt eine GitHub Action die Positionen für D+1
  und committet sie nach `signals/`. Push-Zeitpunkt und Lauf-Protokoll belegen, dass das
  Signal vor Gate Closure existierte.
- **Gleiches Verfahren wie im Backtest:** gleiches Monatsmodell, gleiche Schwellenregel, gleicher
  Verfügbarkeitsfilter, gleicher Data Guard; ein Test prüft die Gleichheit. Ein Signal, das
  erst nach 11:50 fertig ist, wird markiert und nicht gezählt.
- **Abrechnung:** nach Veröffentlichung des ID-AEP mit derselben PnL-Funktion
  (`live/ledger.csv`). Das ist der einzige Test auf Daten, die beim Festlegen des Modells
  niemand kannte.
- **Regelstand:** Das erste Signal (Liefertag 10.10.2026) entstand noch mit Schwelle 0 und
  handelt alle 96 Viertelstunden; es zählt nach der Regel, die bei seiner Erzeugung galt. Ab
  dem Liefertag 11.10.2026 gilt die Kostenuntergrenze.

<!-- LIVE:START -->
_Noch kein abgerechneter Tag. Signale liegen in `signals/`, abgerechnet wird, sobald der ID-AEP veröffentlicht ist._

Warten auf ID-AEP: 2026-10-10

<!-- LIVE:END -->

## Reproduktion

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                  # Tests inkl. Lookahead-Test
python -m dps demo                # komplette Pipeline auf synthetischen Daten

python -m dps fetch --full        # Daten seit 2025-10-01 (ohne API-Keys über freie Quellen)
python -m dps run                 # Ex-post-Regression, Backtest, Report, README
python -m dps run --robustness    # zusätzlich alle Varianten und die Datenprüfung (ca. 1 h)
```

- **Betrieb:** Workflows in `.github/workflows`: `Live` (Signal und Abrechnung), `Backtest`
  (sonntags komplett neu), `CI`. Optionale Secrets `ENTSOE_API_KEY`, `NTP_CLIENT_ID` und
  `NTP_CLIENT_SECRET` für die offiziellen APIs.
- **Code:** alle Annahmen in `dps/config.py`; Features streng nach Verfügbarkeit in
  `features.py`; PnL-Funktion für Backtest und Live in `trading.py`; dazu `model.py`,
  `backtest.py`, `robustness.py`, `checks.py`, `live.py` und `report.py`.

Code: MIT. Daten: ENTSO-E Transparency Platform, netztransparenz.de, Open-Meteo/DWD/ECMWF,
Energy-Charts; es gelten deren Nutzungsbedingungen. Keine Anlageberatung.
