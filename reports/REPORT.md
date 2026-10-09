# Backtest-Report

Testzeitraum 2026-01-01 bis 2026-10-07 (280 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0,25 €/MWh je Seite, 1,0 €/MWh Slippage beim Ausstieg, 10 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3,56). Nicht geschlagen: Immer long (t -0,22), Vorzeichen je Viertelstunde (28 T) (t 0,63), Letztes bekanntes Vorzeichen (t 1,06).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +3,73 €/MWh netto bei 1,0 €/MWh Slippage. Kostet der Ausstieg mehr als 4,7 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +170 265 € auf 25 200 MWh, short -14 840 € auf 16 460 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben +19 813 € von +155 425 €.

![PnL](pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +155 425 | +3,73 | 41 660 | 51 % | 2,59 | 2,38 | -37 357 | -31 329 | 0 |
| Immer long | +189 252 | +2,82 | 67 190 | 44 % | 1,90 | 1,38 | -129 624 | -48 138 | 0 |
| Immer short | -390 822 | -5,82 | 67 190 | 50 % | -3,93 | -2,84 | -398 874 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +103 275 | +1,54 | 67 190 | 49 % | 1,51 | 1,25 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +65 797 | +0,98 | 67 172 | 49 % | 0,88 | 0,78 | -39 963 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -120,8 | -0,22 | +453,6 | 1,29 |
| Immer short | +1 950,9 | 3,56 | +1 280,9 | 3,78 |
| Vorzeichen je Viertelstunde (28 T) | +186,2 | 0,63 | +274,5 | 1,52 |
| Letztes bekanntes Vorzeichen | +320,1 | 1,06 | +586,2 | 3,19 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +155 425 | +16 840 | +19 813 | +148 694 (3,5) | +142 043 (3,8) | +118 742 (3,7) |
| Immer long | +189 252 | +26 937 | -33 820 | +99 641 (0,9) | +15 036 (0,2) | -67 739 (-0,9) |
| Immer short | -390 822 | -27 012 | -518 909 | -301 211 (-2,9) | -216 606 (-2,4) | -133 831 (-1,8) |
| Vorzeichen je Viertelstunde (28 T) | +103 275 | +26 937 | -35 965 | +70 144 (1,4) | +65 184 (1,6) | +45 334 (1,2) |
| Letztes bekanntes Vorzeichen | +65 797 | +50 803 | -115 155 | -1 471 (-0,0) | -22 089 (-0,6) | -32 758 (-0,9) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0,0 | 1,0 | 2,0 | 5,0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +197 085 | +155 425 | +113 765 | -11 215 | 4,7 |
| Immer long | +256 442 | +189 252 | +122 062 | -79 508 | 3,8 |
| Immer short | -323 632 | -390 822 | -458 012 | -659 582 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +170 465 | +103 275 | +36 085 | -165 485 | 2,5 |
| Letztes bekanntes Vorzeichen | +132 969 | +65 797 | -1 376 | -202 893 | 2,0 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +170 265 (25 200) | -14 840 (16 460) |
| Immer long | +189 252 (67 190) | +0 (0) |
| Immer short | +0 (0) | -390 822 (67 190) |
| Vorzeichen je Viertelstunde (28 T) | +185 879 (40 780) | -82 603 (26 410) |
| Letztes bekanntes Vorzeichen | +181 240 (31 490) | -115 443 (35 682) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -4 321 | 180 | 30 | 90 |
| 2026-02 | +1 017 | 202 | 30 | 121 |
| 2026-03 | +6 289 | 5 218 | 5 | 149 |
| 2026-04 | +19 481 | 2 538 | 10 | 180 |
| 2026-05 | +8 267 | 5 928 | 5 | 210 |
| 2026-06 | +29 419 | 7 200 | 0 | 241 |
| 2026-07 | +32 147 | 7 440 | 0 | 271 |
| 2026-08 | +20 880 | 5 172 | 5 | 302 |
| 2026-09 | +47 538 | 6 102 | 2 | 333 |
| 2026-10 | -5 292 | 1 680 | 0 | 363 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste Version fest (erste Zeile). Danach wurde das Hauptmodell zweimal geändert: Die Lastprognose flog raus, weil ihr Veröffentlichungszeitpunkt nicht belegbar ist, und die Vorhersage ist jetzt das Mittel aus fünf Startwerten, weil ein einzelnes Modell stark am Startwert hing. Beides hat den PnL im Test erhöht. Alle anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **erste Version, vor dem ersten Backtest festgelegt (mit Lastprognose, ein einzelnes Modell, Startwert 0)** | +101 647 | +2,67 | 1,54 | +103 278 (2,8) | -0,02 | +165 504 | -63 856 |
| **Hauptmodell: nach dem ersten Backtest ohne Lastprognose und als Mittel aus fünf Startwerten** | +155 425 | +3,73 | 2,38 | +142 043 (3,8) | 0,63 | +170 265 | -14 840 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose | +160 194 | +3,76 | 2,19 | +135 272 (3,5) | 0,57 | +179 479 | -19 285 |
| Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten) | +153 345 | +3,59 | 2,36 | +135 775 (3,6) | 0,59 | +164 424 | -11 079 |
| ohne MW-Features (keine installierte Leistung) | +154 742 | +4,19 | 2,39 | +137 855 (3,8) | 0,62 | +172 716 | -17 975 |
| _Entscheidungsregel_ | | | | | | | |
| feste Schwelle 2 €/MWh, nichts gewählt | +152 752 | +2,59 | 1,80 | +128 300 (2,4) | 0,53 | +208 820 | -56 068 |
| Schwelle auf 56 statt 28 Tagen gewählt | +126 483 | +3,90 | 1,65 | +91 951 (2,2) | 0,27 | +180 575 | -54 092 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +152 487 | +4,58 | 2,24 | +119 375 (3,3) | 0,62 | +186 776 | -34 289 |
| getrennte Schwellen für long und short, „nie“ erlaubt | +174 643 | +4,35 | 2,38 | +118 481 (3,0) | 0,79 | +187 156 | -12 513 |
| Größe nach Signalstärke (10–20 MW) | +318 724 | +4,22 | 2,55 | +265 236 (3,7) | 1,69 | +361 377 | -42 653 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | +12 980 | +0,42 | 0,22 | +56 984 (1,6) | -0,85 | +70 784 | -57 804 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +131 998 | +3,22 | 2,11 | +133 314 (3,6) | 0,29 | +154 849 | -22 851 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +102 293 | +3,32 | 2,06 | +128 471 (4,1) | -0,01 | +115 858 | -13 565 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +146 075 | +3,86 | 2,37 | +146 903 (3,9) | 0,49 | +141 034 | +5 041 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +19 542 | +1,13 | 0,48 | +7 515 (0,3) | -0,95 | +42 905 | -23 363 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -55 083 | -2,84 | -0,93 | +39 071 (1,6) | -1,82 | -101 | -54 982 |
| ohne Spread-Historie | +172 811 | +5,73 | 2,50 | +132 658 (3,9) | 0,61 | +149 866 | +22 945 |
| ohne Day-Ahead-Preise des Vortags | +199 174 | +4,83 | 2,36 | +107 505 (2,5) | 0,85 | +179 235 | +19 939 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-10-07) | +131 415 | +2,89 | 1,93 | +122 292 (3,0) | 0,59 | +160 401 | -28 986 |
| _Zufallsstartwert_ | | | | | | | |
| ein einzelnes Modell statt des Mittels, Startwert 0 | +152 065 | +4,26 | 2,45 | +124 455 (3,7) | 0,61 | +182 177 | -30 112 |
| ein einzelnes Modell statt des Mittels, Startwert 1 | +156 071 | +4,00 | 2,27 | +133 742 (3,4) | 0,54 | +186 321 | -30 251 |
| ein einzelnes Modell statt des Mittels, Startwert 2 | +44 744 | +1,25 | 0,78 | +87 881 (2,6) | -0,70 | +108 834 | -64 090 |
| ein einzelnes Modell statt des Mittels, Startwert 3 | +176 158 | +4,28 | 2,56 | +130 078 (3,4) | 0,86 | +195 711 | -19 553 |
| ein einzelnes Modell statt des Mittels, Startwert 4 | +82 743 | +2,33 | 1,57 | +102 140 (3,1) | -0,24 | +126 233 | -43 490 |
| Mittel über die Startwerte 5–9 | +193 473 | +5,15 | 2,66 | +143 167 (3,6) | 0,89 | +179 139 | +14 334 |
| Mittel über die Startwerte 10–14 | +197 435 | +4,64 | 2,64 | +149 160 (4,0) | 1,01 | +195 858 | +1 576 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): +12 980 bis +197 435 €.
Ein einzelnes Modell landet je nach Zufallsstartwert bei +44 744 bis +176 158 € (t 0,78 bis 2,56). So groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das Hauptmodell fünf Startwerte.
Mittel über fünf Startwerte: 0–4 (Hauptmodell): +155 425 € (t 2,38), 5–9: +193 473 € (t 2,66), 10–14: +197 435 € (t 2,64).

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4,57 | 3,2 | +2,05 | 2,5 | +4,71 | +3,83 | +10,19 | +1,91 | +9,59 |
| Solar | -7,90 | -6,1 | -7,64 | -13,0 | – | -11,47 | -7,69 | -7,55 | – |
| Wind an Land | -3,81 | -1,7 | -4,79 | -5,9 | -6,18 | -8,06 | +5,00 | -7,00 | -11,06 |
| Wind auf See | -5,92 | -2,2 | -4,72 | -4,0 | -9,30 | -8,02 | -3,58 | -10,48 | -8,52 |
| Last | +0,75 | 1,1 | -0,02 | -0,1 | -0,46 | -1,08 | +1,86 | +2,42 | -0,63 |

n = 35 712 Viertelstunden, R² = 0,03, gekappt 0,12. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens 24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---|---:|---:|---:|---:|
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 41 712 | 41 709 | 24 / 27 / 29 h | 0 |
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 41 712 | 41 712 | 48 / 51 / 53 h | 0 |
| ecmwf_ifs | 2026-06-13 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 41 952 | 41 759 | 24 / 27 / 41 h | 0 |
| ecmwf_ifs | 2026-06-13 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 41 952 | 41 759 | 48 / 51 / 65 h | 0 |

Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die gemessene Veröffentlichungszeit.
Gemessen: icon_eu 2,9 bis 4,2 h nach Laufstart (74 Läufe; das Archiv setzt 4,5 h an); ecmwf_ifs 6,1 bis 7,5 h nach Laufstart (38 Läufe; das Archiv setzt 8,5 h an).


<sub>Gerechnet am 2026-10-09 07:10 UTC, Code 70c7d36, Wetterdaten akderekaan/de-power-forecast-data @ 519789445ac9.</sub>
