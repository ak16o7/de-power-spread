# Backtest-Report

Alle Zahlen im Detail. Die Kurzfassung steht im [README](../README.md).

Testzeitraum 2026-01-01 bis 2026-10-09 (282 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0,25 €/MWh je Seite, 1,0 €/MWh Slippage beim Ausstieg, 10 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3,39). Nicht geschlagen: Immer long (t -0,37), Vorzeichen je Viertelstunde (28 T) (t 0,16), Letztes bekanntes Vorzeichen (t 0,93).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +3,45 €/MWh netto bei 1,0 €/MWh Slippage. Kostet der Ausstieg mehr als 4,5 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +162 371 € auf 23 805 MWh, short -28 576 € auf 14 965 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben -699 € von +133 794 €.

![PnL](pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +133 794 | +3,45 | 38 770 | 51 % | 2,15 | 1,93 | -56 843 | -31 329 | 0 |
| Immer long | +190 570 | +2,82 | 67 670 | 44 % | 1,90 | 1,38 | -129 624 | -48 138 | 0 |
| Immer short | -393 580 | -5,82 | 67 670 | 50 % | -3,92 | -2,86 | -398 874 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +119 027 | +1,76 | 67 670 | 49 % | 1,72 | 1,42 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +54 162 | +0,80 | 67 652 | 49 % | 0,71 | 0,63 | -47 757 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -201,3 | -0,37 | +470,0 | 1,35 |
| Immer short | +1 870,1 | 3,39 | +1 206,1 | 3,49 |
| Vorzeichen je Viertelstunde (28 T) | +52,4 | 0,16 | +240,9 | 1,33 |
| Letztes bekanntes Vorzeichen | +282,4 | 0,93 | +547,8 | 2,94 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +133 794 | -1 284 | -699 | +139 461 (3,1) | +134 822 (3,5) | +112 440 (3,4) |
| Immer long | +190 570 | +33 512 | -32 502 | +88 400 (0,8) | +2 295 (0,0) | -80 911 (-1,1) |
| Immer short | -393 580 | -33 587 | -522 527 | -291 410 (-2,8) | -205 305 (-2,3) | -122 099 (-1,6) |
| Vorzeichen je Viertelstunde (28 T) | +119 027 | +33 512 | -25 550 | +73 338 (1,5) | +66 877 (1,6) | +46 459 (1,2) |
| Letztes bekanntes Vorzeichen | +54 162 | +44 228 | -126 789 | -547 (-0,0) | -19 664 (-0,5) | -29 902 (-0,9) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0,0 | 1,0 | 2,0 | 5,0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +172 564 | +133 794 | +95 024 | -21 286 | 4,5 |
| Immer long | +258 240 | +190 570 | +122 900 | -80 110 | 3,8 |
| Immer short | -325 910 | -393 580 | -461 250 | -664 260 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +186 697 | +119 027 | +51 357 | -151 653 | 2,8 |
| Letztes bekanntes Vorzeichen | +121 815 | +54 162 | -13 490 | -216 448 | 1,8 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +162 371 (23 805) | -28 576 (14 965) |
| Immer long | +190 570 (67 670) | +0 (0) |
| Immer short | +0 (0) | -393 580 (67 670) |
| Vorzeichen je Viertelstunde (28 T) | +194 755 (41 032) | -75 727 (26 638) |
| Letztes bekanntes Vorzeichen | +176 547 (31 660) | -122 384 (35 992) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -4 321 | 180 | 30 | 90 |
| 2026-02 | +1 017 | 202 | 30 | 121 |
| 2026-03 | +6 289 | 5 218 | 5 | 149 |
| 2026-04 | +19 481 | 2 538 | 10 | 180 |
| 2026-05 | +8 267 | 5 928 | 5 | 210 |
| 2026-06 | +29 692 | 6 650 | 2 | 241 |
| 2026-07 | +31 982 | 4 840 | 5 | 271 |
| 2026-08 | +20 880 | 5 172 | 5 | 302 |
| 2026-09 | +47 538 | 6 102 | 2 | 333 |
| 2026-10 | -27 032 | 1 940 | 2 | 363 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste Version fest (erste Zeile). Danach wurde das Hauptmodell dreimal geändert: Lastprognose entfernt (Zeitstempel nicht belegbar), Mittel aus fünf Startwerten (ein Einzel-Fit hing stark am Startwert), Handelsschwelle nie unter den Round-trip-Kosten. Keine der Änderungen hat den PnL im Test gesenkt. Alle anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **erste Version, vor dem ersten Backtest festgelegt (mit Lastprognose, ein einzelnes Modell, Startwert 0, Schwelle 0 erlaubt)** | +75 939 | +1,97 | 1,06 | +91 628 (2,3) | -0,43 | +153 466 | -77 527 |
| **Hauptmodell: ohne Lastprognose, Mittel aus fünf Startwerten, Schwelle mindestens 2 €/MWh** | +133 794 | +3,45 | 1,93 | +134 822 (3,5) | 0,16 | +162 371 | -28 576 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose | +133 994 | +3,26 | 1,71 | +122 811 (3,0) | 0,14 | +168 585 | -34 591 |
| Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten) | +118 407 | +2,94 | 1,80 | +123 177 (3,4) | -0,01 | +150 351 | -31 944 |
| ohne MW-Features (keine installierte Leistung) | +119 950 | +3,35 | 1,79 | +121 487 (3,3) | 0,01 | +149 863 | -29 913 |
| _Entscheidungsregel_ | | | | | | | |
| Schwelle 0 erlaubt (Regel bis 9. Oktober 2026) | +133 437 | +3,17 | 1,92 | +134 113 (3,5) | 0,16 | +160 169 | -26 733 |
| feste Schwelle 2 €/MWh, nichts gewählt | +130 210 | +2,19 | 1,48 | +119 816 (2,2) | 0,11 | +199 450 | -69 239 |
| Schwelle auf 56 statt 28 Tagen gewählt | +97 383 | +3,05 | 1,25 | +83 343 (2,0) | -0,23 | +161 269 | -63 886 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +129 946 | +3,86 | 1,80 | +110 892 (3,0) | 0,12 | +177 407 | -47 461 |
| getrennte Schwellen für long und short, „nie“ erlaubt | +136 712 | +4,00 | 2,04 | +101 581 (2,7) | 0,23 | +175 403 | -38 691 |
| Größe nach Signalstärke (10–20 MW) | +273 146 | +3,99 | 2,06 | +246 426 (3,4) | 1,10 | +343 253 | -70 108 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | -23 726 | -0,80 | -0,43 | +49 913 (1,4) | -1,25 | +42 132 | -65 858 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +124 899 | +3,08 | 1,97 | +126 214 (3,2) | 0,06 | +144 505 | -19 607 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +81 257 | +2,60 | 1,51 | +121 494 (3,8) | -0,40 | +107 538 | -26 281 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +142 655 | +3,85 | 2,20 | +144 093 (3,9) | 0,24 | +155 738 | -13 083 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +10 420 | +0,59 | 0,25 | -3 098 (-0,1) | -1,19 | +33 783 | -23 363 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -62 349 | -3,18 | -1,05 | +31 805 (1,3) | -2,04 | -7 367 | -54 982 |
| ohne Spread-Historie | +158 309 | +5,18 | 2,22 | +132 215 (3,9) | 0,33 | +144 292 | +14 017 |
| ohne Day-Ahead-Preise des Vortags | +196 451 | +5,79 | 2,41 | +108 102 (2,7) | 0,68 | +156 348 | +40 103 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-10-09) | +109 784 | +2,57 | 1,52 | +115 071 (2,8) | 0,13 | +152 507 | -42 723 |
| _Zufallsstartwert_ | | | | | | | |
| ein einzelnes Modell statt des Mittels, Startwert 0 | +134 184 | +3,77 | 2,00 | +118 498 (3,3) | 0,17 | +174 642 | -40 458 |
| ein einzelnes Modell statt des Mittels, Startwert 1 | +128 387 | +3,94 | 1,99 | +124 786 (3,4) | 0,09 | +148 537 | -20 150 |
| ein einzelnes Modell statt des Mittels, Startwert 2 | +31 502 | +0,93 | 0,51 | +83 034 (2,5) | -0,99 | +96 572 | -65 070 |
| ein einzelnes Modell statt des Mittels, Startwert 3 | +143 659 | +4,12 | 2,03 | +111 967 (3,0) | 0,27 | +169 434 | -25 775 |
| ein einzelnes Modell statt des Mittels, Startwert 4 | +59 484 | +1,75 | 1,04 | +93 406 (2,7) | -0,64 | +113 122 | -53 639 |
| Mittel über die Startwerte 5–9 | +165 781 | +4,46 | 2,17 | +132 384 (3,4) | 0,43 | +166 104 | -323 |
| Mittel über die Startwerte 10–14 | +168 223 | +4,01 | 2,21 | +141 573 (3,7) | 0,49 | +175 668 | -7 445 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): -23 726 bis +168 223 €.
Ein einzelnes Modell landet je nach Zufallsstartwert bei +31 502 bis +143 659 € (t 0,51 bis 2,03). So groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das Hauptmodell fünf Startwerte.
Mittel über fünf Startwerte: 0–4 (Hauptmodell): +133 794 € (t 1,93), 5–9: +165 781 € (t 2,17), 10–14: +168 223 € (t 2,21).

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4,64 | 3,3 | +1,96 | 2,3 | +4,64 | +4,96 | +9,39 | +1,86 | +9,53 |
| Solar | -7,93 | -6,1 | -7,67 | -13,0 | – | -11,40 | -7,68 | -7,66 | – |
| Wind an Land | -3,82 | -1,7 | -4,95 | -6,1 | -6,30 | -6,95 | +4,60 | -7,14 | -11,23 |
| Wind auf See | -5,68 | -2,1 | -4,36 | -3,6 | -8,90 | -8,49 | -2,79 | -10,22 | -8,08 |
| Last | +0,71 | 1,1 | -0,09 | -0,3 | -0,50 | -0,91 | +1,64 | +2,32 | -0,75 |

n = 36 000 Viertelstunden, R² = 0,02, gekappt 0,12. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens 24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---|---:|---:|---:|---:|
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 41 712 | 41 709 | 24 / 27 / 29 h | 0 |
| icon_eu | 2026-06-14 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 41 712 | 41 712 | 48 / 51 / 53 h | 0 |
| ecmwf_ifs | 2026-06-13 bis 2026-09-30 | Tag 1 (behauptet ≥ 24 h) | 41 952 | 41 759 | 24 / 27 / 41 h | 0 |
| ecmwf_ifs | 2026-06-13 bis 2026-09-30 | Tag 2 (behauptet ≥ 48 h) | 41 952 | 41 759 | 48 / 51 / 65 h | 0 |

Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die gemessene Veröffentlichungszeit.
Gemessen: icon_eu 2,9 bis 4,2 h nach Laufstart (91 Läufe; das Archiv setzt 4,5 h an); ecmwf_ifs 6,1 bis 7,8 h nach Laufstart (47 Läufe; das Archiv setzt 8,5 h an).


<sub>Gerechnet am 2026-10-11 11:39 UTC, Code 507c286, Wetterdaten akderekaan/de-power-forecast-data @ 9a35b39a5dba.</sub>
