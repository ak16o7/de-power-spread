# Backtest-Report

Alle Zahlen im Detail. Die Kurzfassung steht im [README](../README.md).

Testzeitraum 2026-01-01 bis 2026-10-16 (289 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0,25 €/MWh je Seite, 1,0 €/MWh Slippage beim Ausstieg, 10 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3,23). Nicht geschlagen: Immer long (t -0,76), Vorzeichen je Viertelstunde (28 T) (t -0,29), Letztes bekanntes Vorzeichen (t 0,42).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +2,32 €/MWh netto bei 1,0 €/MWh Slippage. Kostet der Ausstieg mehr als 3,3 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +121 018 € auf 22 802 MWh, short -37 045 € auf 13 405 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben -26 711 € von +83 973 €.

![PnL](pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +83 973 | +2,32 | 36 208 | 51 % | 1,38 | 1,19 | -65 434 | -30 759 | 0 |
| Immer long | +202 751 | +2,92 | 69 350 | 44 % | 1,98 | 1,47 | -129 624 | -48 138 | 0 |
| Immer short | -410 801 | -5,92 | 69 350 | 50 % | -4,01 | -2,97 | -411 027 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +110 081 | +1,59 | 69 350 | 49 % | 1,56 | 1,31 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +43 822 | +0,63 | 69 332 | 48 % | 0,56 | 0,51 | -58 097 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -411,0 | -0,76 | +331,8 | 0,93 |
| Immer short | +1 712,0 | 3,23 | +1 151,9 | 3,60 |
| Vorzeichen je Viertelstunde (28 T) | -90,3 | -0,29 | +181,5 | 0,96 |
| Letztes bekanntes Vorzeichen | +138,9 | 0,42 | +485,7 | 2,56 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +83 973 | -10 615 | -26 711 | +111 685 (2,4) | +110 371 (2,8) | +92 809 (2,8) |
| Immer long | +202 751 | +33 512 | -20 321 | +100 581 (1,0) | +14 476 (0,2) | -69 855 (-0,9) |
| Immer short | -410 801 | -33 587 | -539 748 | -308 631 (-2,9) | -222 526 (-2,5) | -138 195 (-1,8) |
| Vorzeichen je Viertelstunde (28 T) | +110 081 | +33 512 | -34 496 | +64 392 (1,3) | +57 931 (1,4) | +37 404 (1,0) |
| Letztes bekanntes Vorzeichen | +43 822 | +44 228 | -137 130 | -10 887 (-0,2) | -30 005 (-0,8) | -39 951 (-1,1) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0,0 | 1,0 | 2,0 | 5,0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +120 180 | +83 973 | +47 765 | -60 857 | 3,3 |
| Immer long | +272 101 | +202 751 | +133 401 | -74 649 | 3,9 |
| Immer short | -341 451 | -410 801 | -480 151 | -688 201 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +179 431 | +110 081 | +40 731 | -167 319 | 2,6 |
| Letztes bekanntes Vorzeichen | +113 154 | +43 822 | -25 511 | -233 508 | 1,6 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +121 018 (22 802) | -37 045 (13 405) |
| Immer long | +202 751 (69 350) | +0 (0) |
| Immer short | +0 (0) | -410 801 (69 350) |
| Vorzeichen je Viertelstunde (28 T) | +197 520 (41 948) | -87 439 (27 402) |
| Letztes bekanntes Vorzeichen | +178 731 (32 498) | -134 909 (36 835) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -3 222 | 140 | 30 | 90 |
| 2026-02 | -963 | 108 | 30 | 121 |
| 2026-03 | +12 105 | 1 862 | 15 | 149 |
| 2026-04 | +2 254 | 6 242 | 2 | 180 |
| 2026-05 | +5 462 | 6 798 | 2 | 210 |
| 2026-06 | +11 478 | 6 458 | 2 | 241 |
| 2026-07 | +34 271 | 3 072 | 10 | 271 |
| 2026-08 | +16 523 | 5 200 | 5 | 302 |
| 2026-09 | +28 674 | 2 995 | 10 | 333 |
| 2026-10 | -22 609 | 3 332 | 2 | 363 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste Version fest (erste Zeile). Danach wurde das Hauptmodell dreimal geändert: Lastprognose entfernt (Zeitstempel nicht belegbar), Mittel aus fünf Startwerten (ein Einzel-Fit hing stark am Startwert), Handelsschwelle nie unter den Round-trip-Kosten. Keine der Änderungen hat den PnL im Test gesenkt. Alle anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **erste Version, vor dem ersten Backtest festgelegt (mit Lastprognose, ein einzelnes Modell, Startwert 0, Schwelle 0 erlaubt)** | +69 349 | +1,94 | 1,02 | +98 042 (2,7) | -0,47 | +112 206 | -42 857 |
| **Hauptmodell: ohne Lastprognose, Mittel aus fünf Startwerten, Schwelle mindestens 2 €/MWh** | +83 973 | +2,32 | 1,19 | +110 371 (2,8) | -0,29 | +121 018 | -37 045 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose | +125 951 | +3,21 | 1,96 | +130 043 (3,3) | 0,18 | +134 464 | -8 513 |
| Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten) | +98 302 | +2,62 | 1,53 | +113 747 (3,1) | -0,13 | +133 274 | -34 972 |
| ohne MW-Features (keine installierte Leistung) | +55 283 | +1,65 | 0,97 | +68 189 (1,8) | -0,58 | +133 737 | -78 454 |
| _Entscheidungsregel_ | | | | | | | |
| Schwelle 0 erlaubt (Regel bis 9. Oktober 2026) | +80 949 | +2,20 | 1,15 | +107 386 (2,8) | -0,32 | +121 317 | -40 368 |
| feste Schwelle 2 €/MWh, nichts gewählt | +14 535 | +0,24 | 0,15 | +65 424 (1,0) | -0,85 | +137 211 | -122 675 |
| Schwelle auf 56 statt 28 Tagen gewählt | +100 185 | +3,68 | 1,42 | +93 689 (2,4) | -0,11 | +125 852 | -25 667 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +93 738 | +9,49 | 1,77 | +67 026 (2,7) | -0,20 | +84 870 | +8 869 |
| getrennte Schwellen für long und short, „nie“ erlaubt | +83 523 | +2,30 | 1,29 | +73 277 (1,8) | -0,32 | +140 269 | -56 746 |
| Größe nach Signalstärke (10–20 MW) | +116 049 | +1,67 | 0,89 | +199 157 (2,8) | 0,04 | +230 862 | -114 813 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | +8 330 | +0,26 | 0,14 | +87 469 (2,2) | -0,89 | +77 255 | -68 925 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +106 534 | +3,05 | 1,61 | +117 572 (2,9) | -0,04 | +159 994 | -53 460 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +63 566 | +1,72 | 0,95 | +109 218 (2,9) | -0,53 | +115 859 | -52 293 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +106 164 | +2,93 | 1,49 | +121 027 (3,2) | -0,04 | +138 069 | -31 905 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +34 006 | +1,66 | 0,51 | +22 052 (0,7) | -1,11 | +33 583 | +423 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -61 114 | -3,01 | -1,03 | +33 040 (1,3) | -1,91 | -4 926 | -56 188 |
| ohne Spread-Historie | +84 188 | +2,56 | 1,47 | +120 893 (3,4) | -0,27 | +152 063 | -67 875 |
| ohne Day-Ahead-Preise des Vortags | +180 100 | +4,83 | 2,25 | +96 848 (2,3) | 0,62 | +166 582 | +13 519 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-10-16) | +61 576 | +1,54 | 0,85 | +92 233 (2,2) | -0,31 | +111 706 | -50 129 |
| _Zufallsstartwert_ | | | | | | | |
| ein einzelnes Modell statt des Mittels, Startwert 0 | +117 519 | +3,85 | 1,85 | +90 872 (2,5) | 0,08 | +117 657 | -138 |
| ein einzelnes Modell statt des Mittels, Startwert 1 | +48 780 | +1,44 | 0,78 | +111 660 (3,1) | -0,70 | +95 967 | -47 187 |
| ein einzelnes Modell statt des Mittels, Startwert 2 | +112 467 | +3,22 | 1,63 | +101 637 (2,7) | 0,03 | +146 732 | -34 265 |
| ein einzelnes Modell statt des Mittels, Startwert 3 | +73 330 | +1,88 | 1,08 | +122 209 (3,1) | -0,37 | +143 630 | -70 301 |
| ein einzelnes Modell statt des Mittels, Startwert 4 | +61 382 | +1,67 | 0,91 | +92 867 (2,4) | -0,51 | +141 812 | -80 430 |
| Mittel über die Startwerte 5–9 | +94 907 | +2,74 | 1,32 | +106 154 (2,8) | -0,17 | +151 814 | -56 907 |
| Mittel über die Startwerte 10–14 | +71 023 | +2,32 | 1,13 | +90 880 (2,6) | -0,40 | +138 439 | -67 416 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): +8 330 bis +125 951 €.
Ein einzelnes Modell landet je nach Zufallsstartwert bei +48 780 bis +117 519 € (t 0,78 bis 1,85). So groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das Hauptmodell fünf Startwerte.
Mittel über fünf Startwerte: 0–4 (Hauptmodell): +83 973 € (t 1,19), 5–9: +94 907 € (t 1,32), 10–14: +71 023 € (t 1,13).

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4,73 | 3,3 | +2,12 | 2,5 | +4,70 | +4,92 | +9,23 | +2,18 | +9,70 |
| Solar | -7,96 | -6,1 | -7,69 | -13,1 | – | -11,46 | -7,70 | -7,73 | – |
| Wind an Land | -3,84 | -1,7 | -4,94 | -6,1 | -6,31 | -6,96 | +4,53 | -7,15 | -11,18 |
| Wind auf See | -5,75 | -2,1 | -4,60 | -3,8 | -9,12 | -8,28 | -2,81 | -10,61 | -8,03 |
| Last | +0,72 | 1,1 | -0,06 | -0,2 | -0,44 | -0,92 | +1,55 | +2,36 | -0,68 |

n = 36 672 Viertelstunden, R² = 0,02, gekappt 0,12. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens 24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---|---:|---:|---:|---:|
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 41 712 | 41 709 | 24 / 27 / 29 h | 0 |
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 41 712 | 41 712 | 48 / 51 / 53 h | 0 |
| ecmwf_ifs | 2025-10-01 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 140 160 | 111 300 | 24 / 27 / 71 h | 0 |
| ecmwf_ifs | 2025-10-01 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 140 160 | 107 729 | 29 / 51 / 71 h | 1 |

Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die gemessene Veröffentlichungszeit.
Gemessen: icon_eu 2,9 bis 4,2 h nach Laufstart (145 Läufe; das Archiv setzt 4,5 h an); ecmwf_ifs 6,1 bis 8,2 h nach Laufstart (74 Läufe; das Archiv setzt 8,5 h an).


<sub>Gerechnet am 2026-10-18 05:05 UTC, Code 3acd22d, Wetterdaten akderekaan/de-power-forecast-data @ 239f6ed21270.</sub>
