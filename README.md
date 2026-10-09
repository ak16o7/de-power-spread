# DE Power Spread

**Die Frage:** Kann man mit öffentlich verfügbaren Wetterprognosen vorhersagen, ob Strom kurz
vor der Lieferung teurer oder billiger wird als am Vortag, und damit nach Kosten Geld verdienen?

Dieses Projekt prüft das am deutschen Strommarkt. Jeden Tag um 11:00 entscheidet ein Modell für
jede Viertelstunde des nächsten Tages: kaufen, verkaufen oder nichts tun. Gemessen wird so
streng wie möglich: in Euro nach Kosten, gegen einfache Vergleichsstrategien, ohne Blick in die
Zukunft und seit Oktober 2026 auch live, mit öffentlichem Zeitstempel.

## Ergebnis

Begriffe wie Spread, ID-AEP oder t-Wert erklärt die Tabelle [Begriffe](#begriffe), die Vergleichsstrategien („Immer long“ usw.) der Abschnitt [Warum man den Zahlen trauen kann](#warum-man-den-zahlen-trauen-kann).

<!-- RESULTS:START -->
**Ergebnis auf einen Blick** · Test 2026-01-01 bis 2026-10-07 (280 Tage), gerechnet am 2026-10-09

- **Verdient das Modell Geld?** Ja: +155 425 € nach Kosten (+3,73 € je MWh), t-Wert 2,38.
- **Kommt das aus den Wetterprognosen?** Ja: Dasselbe Modell ohne Wetterdaten kommt auf -55 083 €.
- **Ist es besser als einfache Regeln?** Nicht eindeutig. Deutlich besser (t > 2) ist es nur als „Immer short“. „Immer long“ verdient sogar mehr (+189 252 €), aber fast nur an Preisspitzen: Mit Spreads auf ±200 €/MWh begrenzt bleiben +15 036 €, beim Modell +142 043 €. Das vorab festgelegte Erfolgskriterium ist damit **nicht erfüllt**.
- **Wo kommt der Gewinn her?** Aus Long-Positionen (+170 265 €); Short-Positionen verlieren unterm Strich (-14 840 €). Ein großer Teil hängt an wenigen Tagen: Ohne die 10 besten Tage blieben +19 813 €.
- **Was darf die Ausführung kosten?** Der Gewinn hält, solange echte Geschäfte im Schnitt höchstens 4,7 €/MWh schlechter sind als der ID-AEP-Index (angesetzt: 1,0 €/MWh).
- **Ehrlichkeitshinweis:** Die vor dem ersten Test festgelegte Version kam auf +101 647 € (t-Wert 1,54). Zwei Änderungen danach haben das Ergebnis verbessert; was und warum, steht unten.

**Fazit:** Ein sauber gemessenes, aber schwaches Signal. Kein Geldautomat.

![Kumulierter Gewinn des Modells und der Vergleichsstrategien](reports/pnl.png)

| Strategie | Gewinn nach Kosten | € je MWh | t-Wert | Gewinn ohne extreme Preisspitzen (Spread auf ±200 €/MWh begrenzt) |
|---|---:|---:|---:|---:|
| **Modell** | +155 425 € | +3,73 | 2,38 | +142 043 € |
| Immer long | +189 252 € | +2,82 | 1,38 | +15 036 € |
| Immer short | -390 822 € | -5,82 | -2,84 | -216 606 € |
| Vorzeichen je Viertelstunde (28 T) | +103 275 € | +1,54 | 1,25 | +65 184 € |
| Letztes bekanntes Vorzeichen | +65 797 € | +0,98 | 0,78 | -22 089 € |

**Wie stabil ist das?** Dieselbe Rechnung mit geänderten Annahmen:

| Variante | Gewinn nach Kosten | t-Wert |
|---|---:|---:|
| Erste, vorab festgelegte Version | +101 647 € | 1,54 |
| **Hauptmodell** | +155 425 € | 2,38 |
| Hauptmodell mit Lastprognose | +160 194 € | 2,19 |
| Hauptmodell ohne Wetterdaten | -55 083 € | -0,93 |
| Feste Handelsschwelle statt monatlich gewählter | +152 752 € | 1,80 |
| Test schon ab Dezember 2025 | +131 415 € | 1,93 |
| Ein einzelnes Modell statt Mittel aus fünf, je nach Zufallsstartwert | +44 744 bis +176 158 € | 0,78 bis 2,56 |

Alle 26 getesteten Varianten, auch die schlechten, stehen in [reports/REPORT.md](reports/REPORT.md).

**Warum der Spread sich bewegt:** Liefern Sonne oder Wind 1 GW mehr als die Netzbetreiber am Vortag prognostiziert haben, fällt der Intraday-Preis gegenüber Day-Ahead im Schnitt um 7,6 €/MWh (Solar), 4,8 €/MWh (Wind an Land), 4,7 €/MWh (Wind auf See). Diese Überraschungen versucht das Modell vorab zu erkennen.

Alle Tabellen (Kosten, Monate, Long und Short, alle Varianten, Regression, Datenprüfung): [reports/REPORT.md](reports/REPORT.md).

<!-- RESULTS:END -->

## Der Trade in einem Beispiel

Strom für morgen wird zweimal gehandelt:

1. **Day-Ahead-Auktion**, heute um 12:00. Sie legt für jede Viertelstunde von morgen einen
   Preis fest.
2. **Intraday-Handel**, bis kurz vor der Lieferung. Hier reagiert der Preis auf alles, was
   nach der Auktion passiert, vor allem auf neue Wetterprognosen.

Der Unterschied zwischen beiden Preisen heißt **Spread** (Intraday minus Day-Ahead). Auf ihn
wird gewettet:

| Position | Was man tut | Gewinn, wenn … |
|---|---|---|
| **Long** | in der Auktion kaufen, kurz vor Lieferung verkaufen | … Strom intraday teurer wird |
| **Short** | in der Auktion verkaufen, kurz vor Lieferung zurückkaufen | … Strom intraday billiger wird |

**Zahlenbeispiel:** 10 MW für eine Viertelstunde sind 2,5 MWh. Auktionspreis 60 €/MWh,
Intraday-Preis 75 €/MWh. Long verdient (75 − 60) × 2,5 = 37,50 €, minus 3,75 € Kosten,
also 33,75 €. Short hätte 37,50 € plus Kosten verloren.

**Warum es den Spread gibt:** Bei der Auktion kennt der Markt nur die Wetterprognose vom
Vortag. Weht morgen mehr Wind oder scheint mehr Sonne als erwartet, gibt es zu viel Strom und
der Intraday-Preis fällt; dann gewinnt Short. Kommt weniger, steigt er; dann gewinnt Long.
Das Modell versucht, die Richtung dieser Überraschung vorab zu erraten.

Die Position wird vor der Lieferung immer vollständig glattgestellt. Unterm Strich bleibt also
nie eine Strommenge offen, und es wird nie auf Ausgleichsenergie spekuliert. Das wäre ein
Verstoß gegen die Bilanzkreistreue, keine Strategie.

## Ein Handelstag

| Wann | Was passiert |
|---|---|
| Vortag, bis 11:00 | Daten sammeln: Wetterprognosen, die Auktionspreise für den Vortag selbst, Spreads der letzten Tage |
| Vortag, 11:00 | Das Modell entscheidet für jede der 96 Viertelstunden: long, short oder nichts |
| Vortag, 12:00 | Day-Ahead-Auktion: Einstieg zum Auktionspreis |
| Liefertag | Kurz vor jeder Viertelstunde wird im Intraday-Handel glattgestellt |
| Tag danach | Der ID-AEP wird veröffentlicht, der Tag wird abgerechnet |

### Wie der Ausstieg bewertet wird: der ID-AEP

Echte Intraday-Kurse kosten Geld (die Börse EPEX verkauft sie). Frei verfügbar ist der
**ID-AEP**, den die vier Übertragungsnetzbetreiber für jede Viertelstunde veröffentlichen: der
Durchschnittspreis der letzten 500 MW, die vor der Lieferung gehandelt wurden. Inhaltlich ist
das der ID500 (der Name kommt daher, dass der Ausgleichsenergiepreis daran gekoppelt ist).

Der ID-AEP ist ein **Index, kein Preis, zu dem man handeln kann**. Ein echter Händler bekommt
mal mehr, mal weniger. Diesen Unterschied deckt ein Kostenaufschlag ab (Slippage, 1 €/MWh).
Wie groß er höchstens sein darf, ohne dass der Gewinn verschwindet, steht oben im Ergebnis
(„Was darf die Ausführung kosten?“).

## Wie das Modell entscheidet

**Was es um 11:00 weiß.** Jede Quelle wird nur mit dem Stand verwendet, der zur Entscheidung
tatsächlich veröffentlicht war:

| Input | Quelle | bekannt ab |
|---|---|---|
| Wetterprognosen (Wind an Land und auf See, Sonne, Temperatur, Wolken) der Modelle ICON-EU und ECMWF an 16 Orten in Deutschland, dazu wie stark sie sich zuletzt geändert haben und wie sehr sich die beiden Modelle widersprechen | [de-power-forecast-data](https://huggingface.co/datasets/akderekaan/de-power-forecast-data) (Open-Meteo, DWD, ECMWF) | laut Zeitstempel jeder Prognose; nur Prognosen, die mindestens 24 h vor ihrer Gültigkeit gemacht wurden |
| Installierte Wind- und Solarleistung | Energy-Charts | Wert von vor zwei Monaten |
| Auktionspreise des Vortags | ENTSO-E oder SMARD (Bundesnetzagentur) | 13:30 am Tag davor |
| Spreads der letzten Tage | netztransparenz.de | nur Tage, deren ID-AEP schon veröffentlicht war (drei Tage alt und älter) |
| Kalender: Uhrzeit, Wochentag, Feiertag, Sonnenstand | berechnet | immer |

**Das Modell.** Gradient Boosting (scikit-learn) mit festen Einstellungen. Es lernt aus der
Vergangenheit, welcher Spread bei welcher Wetterlage zu erwarten ist. Die Vorhersage ist das
Mittel aus fünf identischen Modellen mit verschiedenem Zufallsstart, weil ein einzelnes
Modell stark vom Zufall abhing (siehe Ergebnis, „Wie stabil ist das?“).

**Die Handelsregel.** Gehandelt wird nur, wenn der vorhergesagte Spread groß genug ist. Die
Schwelle wird jeden Monat auf den letzten 28 Tagen gewählt, mit einem Modell, das diese Tage
nicht kannte.

**Walk-forward.** Das Modell wird jeden Monat neu trainiert, immer nur mit Daten, die zu diesem
Zeitpunkt schon bekannt waren. Jeder Testmonat ist für das Modell also echte Zukunft.

## Warum man den Zahlen trauen kann

- **Kein Blick in die Zukunft.** Ein automatischer Test baut die Entscheidung für einen Tag,
  verfälscht dann alle Daten, die erst später veröffentlicht wurden, und verlangt exakt
  dieselbe Entscheidung. Absichtlich eingebaute Fehler fängt er. Zusätzlich sind die
  Zeitstempel der Wetterdaten gegen die Daten selbst geprüft: Kein einziger Wert war frischer
  als angegeben (Tabelle in [REPORT.md](reports/REPORT.md)).
- **Einfache Vergleichsstrategien.** Ein Modell ist nur etwas wert, wenn es simple Regeln
  schlägt:

  | Vergleichsstrategie | Regel |
  |---|---|
  | Immer long / Immer short | jede Viertelstunde dieselbe Richtung |
  | Vorzeichen je Viertelstunde | Richtung, in die der Spread zu dieser Uhrzeit in den letzten 28 Tagen im Schnitt ging |
  | Letztes bekanntes Vorzeichen | Richtung des Spreads zu dieser Uhrzeit am neuesten bekannten Tag |

  **Das Erfolgskriterium stand vorher fest:** Das Modell muss jede dieser Regeln mit einem
  t-Wert über 2 schlagen. Ob das erfüllt ist, rechnet der Report automatisch aus.
- **Realistische Kosten.** 0,25 €/MWh Gebühren je Seite und 1 €/MWh Slippage beim Ausstieg,
  bei 10 MW je Viertelstunde. Der Report zeigt auch, was bei höheren Kosten übrig bleibt.
- **Alles offen.** Alle getesteten Varianten stehen im Report, auch die schlechten. Die beste
  davon als Strategie zu verkaufen, wäre Selbstbetrug.

### Was nach dem ersten Test geändert wurde

Vor dem ersten Test auf echten Daten war alles festgelegt. Danach wurde zweimal geändert.
Aufgefallen ist beides beim Prüfen der Testergebnisse, begründet ist beides unabhängig von der
Höhe des Gewinns:

1. **Die Lastprognose wurde entfernt.** Bei ihr lässt sich nicht belegen, wann ein Wert
   veröffentlicht oder ob er später korrigiert wurde. Messbar bringt sie ohnehin nichts.
2. **Fünf Modelle statt einem.** Ein einzelnes Modell hing stark vom Zufallsstart ab.
   Fünf zu mitteln reduziert dieses Rauschen, ohne irgendetwas am Modell einzustellen.

Außerdem wurde ein kleiner Fehler behoben (die installierte Leistung wurde in den ersten
Stunden jedes Monats aus dem falschen Monat gelesen). Beide Änderungen haben das Ergebnis
verbessert. Deshalb steht die ursprüngliche Version mit ihrem schwächeren Ergebnis gleich oben
mit im Ergebnis.

## Grenzen

- **Der Ausstieg ist ein Index, kein echter Preis.** Ob echte Ausführung gut genug wäre, kann
  nur ein Handelsdesk mit Orderbuchdaten beantworten.
- **Kurze Historie.** Gut neun Monate Test, Daten ab Oktober 2025 (seitdem wird Day-Ahead in
  Viertelstunden gehandelt). Jahreszeiten hat das Modell nur einmal gesehen.
- **Wenige Tage tragen viel.** Ein t-Wert um 2 über neun Monate ist bei so starken
  Preisspitzen wenig belastbar.
- **Wetterdaten werden besser.** Ab Mitte Juni 2026 gibt es vollständige Modellläufe statt nur
  Archivwerten; die Prognosen im Modell sind seitdem frischer. Das war echte, zur Entscheidung
  verfügbare Information, aber der Testzeitraum ist dadurch nicht ganz einheitlich.
- **Kleinkram.** Installierte Leistung im heutigen Datenstand (spätere Nachmeldungen sind
  klein), nur bundesweite Feiertage, keine eigene Marktwirkung.

## Live-Track-Record

Der Backtest wurde vom Autor angeschaut, so ehrlich er auch gerechnet ist. Der einzige Test auf
wirklich unbekannten Daten ist der Live-Betrieb:

- Jeden Tag zwischen 10:45 und 11:50 berechnet eine GitHub Action die Positionen für morgen und
  legt sie in `signals/` ab. Push-Zeitpunkt und Protokoll des Laufs belegen, dass das Signal vor
  der Auktion existierte.
- Verfahren, Daten und Regeln sind dieselben wie im Backtest; ein Test prüft das. Fehlen Daten,
  wird an dem Tag nicht gehandelt. Ein Signal, das erst nach 11:50 fertig ist, zählt nicht.
- Sobald der ID-AEP veröffentlicht ist, wird mit derselben Rechnung wie im Backtest abgerechnet
  (`live/ledger.csv`).

<!-- LIVE:START -->
_Noch kein abgerechneter Tag. Signale liegen in `signals/`, abgerechnet wird, sobald der ID-AEP veröffentlicht ist._

Warten auf ID-AEP: 2026-10-10

<!-- LIVE:END -->

## Begriffe

| Begriff | Bedeutung |
|---|---|
| Day-Ahead | Auktion am Vortag um 12:00, ein Preis je Viertelstunde |
| Intraday | fortlaufender Handel bis kurz vor der Lieferung |
| Spread | Intraday-Preis minus Day-Ahead-Preis |
| Long / Short | auf steigenden / fallenden Intraday-Preis setzen |
| ID-AEP | Durchschnittspreis der letzten 500 MW Intraday-Handel einer Viertelstunde, veröffentlicht von den Netzbetreibern |
| Slippage | wie viel schlechter ein echtes Geschäft ist als der Referenzpreis |
| t-Wert | wie deutlich ein Ergebnis über dem Tagesrauschen liegt; ab etwa 2 ist Zufall unwahrscheinlich. Berechnet mit Newey-West-Korrektur, weil aufeinanderfolgende Tage zusammenhängen |
| Walk-forward | jeden Monat neu trainieren, nur mit dem, was bis dahin bekannt war |
| Lookahead | versehentlicher Blick in die Zukunft im Backtest, der Kardinalfehler |

## Für Entwickler

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m dps demo                # ganze Pipeline auf erfundenen Daten, ohne Zugangsdaten
python -m pytest                  # Tests, u. a. der Lookahead-Test

python -m dps fetch --full        # echte Daten seit 2025-10-01 laden (geht ohne API-Keys)
python -m dps run                 # Regression, Backtest, Report, dieses README
python -m dps run --robustness    # dazu alle Varianten und die Datenprüfung (rund eine Stunde)
```

- **Betrieb auf GitHub:** Workflows unter `.github/workflows`: `Live` (täglich Signal und
  Abrechnung), `Backtest` (sonntags alles neu rechnen), `CI` (Tests). Optionale Secrets
  `ENTSOE_API_KEY`, `NTP_CLIENT_ID`, `NTP_CLIENT_SECRET` für die offiziellen APIs; ohne sie
  laufen Energy-Charts und der CSV-Download von netztransparenz.de.
- **Reproduzierbarkeit:** `reports/backtest.json` hält Code-Commit, Revision des Wetter-Datasets
  und Datenstand fest. `DPS_HF_REVISION=<commit>` liest genau diese Revision.
- **Code:** `dps/config.py` (alle Annahmen an einer Stelle), `features.py` (Inputs streng nach
  Verfügbarkeit), `model.py`, `backtest.py`, `robustness.py`, `live.py`, `trading.py`
  (PnL-Rechnung für Backtest und Live), `checks.py` (Datenprüfung), `report.py`.

Code unter MIT-Lizenz. Daten: ENTSO-E Transparency Platform, netztransparenz.de,
Open-Meteo/DWD/ECMWF, Energy-Charts; deren Nutzungsbedingungen gelten. Keine Anlageberatung.
