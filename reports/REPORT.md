# Backtest-Report

Alle Zahlen im Detail. Die Kurzfassung steht im [README](../README.md).

Testzeitraum 2026-01-01 bis 2026-11-20 (324 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0,25 €/MWh je Seite, 1,0 €/MWh Slippage beim Ausstieg, 10 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3,46). Nicht geschlagen: Immer long (t -0,47), Vorzeichen je Viertelstunde (28 T) (t 0,71), Letztes bekanntes Vorzeichen (t 0,83).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +3,97 €/MWh netto bei 1,0 €/MWh Slippage. Kostet der Ausstieg mehr als 5,0 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +181 537 € auf 25 100 MWh, short -29 262 € auf 13 222 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben -8 630 € von +152 275 €.

![PnL](pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +152 275 | +3,97 | 38 322 | 50 % | 2,02 | 1,95 | -67 736 | -31 934 | 0 |
| Immer long | +224 318 | +2,88 | 77 760 | 44 % | 1,96 | 1,55 | -129 624 | -48 138 | 0 |
| Immer short | -457 598 | -5,88 | 77 760 | 50 % | -3,99 | -3,16 | -490 198 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +91 190 | +1,17 | 77 760 | 48 % | 1,17 | 1,03 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +64 100 | +0,82 | 77 742 | 49 % | 0,75 | 0,72 | -66 427 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -222,4 | -0,47 | +332,8 | 0,97 |
| Immer short | +1 882,3 | 3,46 | +1 237,6 | 3,72 |
| Vorzeichen je Viertelstunde (28 T) | +188,5 | 0,71 | +317,8 | 1,66 |
| Letztes bekanntes Vorzeichen | +272,1 | 0,83 | +464,8 | 2,43 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +152 275 | -8 519 | -8 630 | +152 247 (2,9) | +137 765 (3,0) | +106 126 (2,8) |
| Immer long | +224 318 | +33 512 | +1 247 | +122 149 (1,1) | +29 952 (0,3) | -67 571 (-0,8) |
| Immer short | -457 598 | -33 587 | -593 023 | -355 429 (-3,1) | -263 232 (-2,6) | -165 709 (-1,9) |
| Vorzeichen je Viertelstunde (28 T) | +91 190 | +33 512 | -56 629 | +45 501 (0,8) | +34 789 (0,7) | +10 345 (0,2) |
| Letztes bekanntes Vorzeichen | +64 100 | +44 228 | -122 726 | +9 391 (0,2) | -12 842 (-0,3) | -26 019 (-0,7) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0,0 | 1,0 | 2,0 | 5,0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +190 597 | +152 275 | +113 952 | -1 015 | 5,0 |
| Immer long | +302 078 | +224 318 | +146 558 | -86 722 | 3,9 |
| Immer short | -379 838 | -457 598 | -535 358 | -768 638 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +168 950 | +91 190 | +13 430 | -219 850 | 2,2 |
| Letztes bekanntes Vorzeichen | +141 842 | +64 100 | -13 643 | -246 870 | 1,8 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +181 537 (25 100) | -29 262 (13 222) |
| Immer long | +224 318 (77 760) | +0 (0) |
| Immer short | +0 (0) | -457 598 (77 760) |
| Vorzeichen je Viertelstunde (28 T) | +201 843 (48 368) | -110 653 (29 392) |
| Letztes bekanntes Vorzeichen | +205 792 (36 815) | -141 692 (40 928) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -5 366 | 138 | 30 | 90 |
| 2026-02 | -796 | 90 | 30 | 121 |
| 2026-03 | +9 533 | 1 075 | 20 | 149 |
| 2026-04 | -1 510 | 2 860 | 10 | 180 |
| 2026-05 | +13 802 | 3 945 | 10 | 210 |
| 2026-06 | +29 684 | 5 355 | 5 | 241 |
| 2026-07 | +34 996 | 6 550 | 2 | 271 |
| 2026-08 | +22 776 | 6 440 | 2 | 302 |
| 2026-09 | +63 897 | 4 798 | 5 | 333 |
| 2026-10 | -11 099 | 6 758 | 2 | 363 |
| 2026-11 | -3 644 | 315 | 30 | 394 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste Version fest (erste Zeile). Danach wurde das Hauptmodell dreimal geändert: Lastprognose entfernt (Zeitstempel nicht belegbar), Mittel aus fünf Startwerten (ein Einzel-Fit hing stark am Startwert), Handelsschwelle nie unter den Round-trip-Kosten. Keine der Änderungen hat den PnL im Test gesenkt. Alle anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **erste Version, vor dem ersten Backtest festgelegt (mit Lastprognose, ein einzelnes Modell, Startwert 0, Schwelle 0 erlaubt)** | +151 683 | +3,70 | 1,95 | +148 324 (3,2) | 0,66 | +177 756 | -26 073 |
| **Hauptmodell: ohne Lastprognose, Mittel aus fünf Startwerten, Schwelle mindestens 2 €/MWh** | +152 275 | +3,97 | 1,95 | +137 765 (3,0) | 0,71 | +181 537 | -29 262 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose | +135 742 | +3,57 | 1,64 | +156 208 (3,4) | 0,49 | +132 596 | +3 146 |
| Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten) | +99 078 | +2,14 | 1,44 | +101 783 (2,5) | 0,08 | +158 785 | -59 707 |
| ohne MW-Features (keine installierte Leistung) | +182 636 | +4,66 | 2,42 | +130 339 (2,9) | 1,18 | +178 435 | +4 201 |
| _Entscheidungsregel_ | | | | | | | |
| Schwelle 0 erlaubt (Regel bis 9. Oktober 2026) | +146 073 | +3,73 | 1,88 | +133 635 (3,0) | 0,64 | +180 665 | -34 592 |
| feste Schwelle 2 €/MWh, nichts gewählt | +31 186 | +0,46 | 0,26 | +84 203 (1,1) | -0,49 | +154 161 | -122 975 |
| Schwelle auf 56 statt 28 Tagen gewählt | +113 666 | +2,65 | 1,23 | +118 454 (2,2) | 0,23 | +157 564 | -43 898 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +85 259 | +6,51 | 1,50 | +66 637 (2,2) | -0,06 | +100 114 | -14 855 |
| getrennte Schwellen für long und short, „nie“ erlaubt | +124 025 | +3,18 | 1,57 | +98 071 (2,4) | 0,47 | +156 351 | -32 326 |
| Größe nach Signalstärke (10–20 MW) | +299 446 | +3,65 | 1,79 | +297 805 (3,3) | 1,48 | +333 454 | -34 009 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | -26 977 | -0,93 | -0,49 | +54 247 (1,4) | -1,08 | +47 405 | -74 383 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +87 889 | +2,33 | 1,41 | +123 825 (3,2) | -0,03 | +160 275 | -72 386 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +78 067 | +1,87 | 0,89 | +118 552 (2,6) | -0,15 | +101 641 | -23 574 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +91 861 | +2,40 | 1,03 | +127 156 (2,7) | 0,01 | +115 781 | -23 920 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +28 226 | +1,22 | 0,38 | +32 045 (0,7) | -0,76 | +49 426 | -21 200 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -65 617 | -2,92 | -1,09 | +27 941 (1,0) | -1,66 | -10 006 | -55 612 |
| ohne Spread-Historie | +134 326 | +3,03 | 1,60 | +134 200 (3,1) | 0,52 | +169 705 | -35 379 |
| ohne Day-Ahead-Preise des Vortags | +148 482 | +3,93 | 2,08 | +89 156 (2,1) | 0,65 | +180 044 | -31 562 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-11-20) | +130 575 | +3,10 | 1,63 | +120 323 (2,5) | 0,70 | +172 703 | -42 128 |
| _Zufallsstartwert_ | | | | | | | |
| ein einzelnes Modell statt des Mittels, Startwert 0 | +116 282 | +3,46 | 1,40 | +106 850 (2,9) | 0,31 | +139 212 | -22 930 |
| ein einzelnes Modell statt des Mittels, Startwert 1 | +73 242 | +2,31 | 0,93 | +110 386 (2,9) | -0,20 | +103 218 | -29 977 |
| ein einzelnes Modell statt des Mittels, Startwert 2 | +167 749 | +4,34 | 2,28 | +149 793 (3,4) | 0,78 | +170 225 | -2 475 |
| ein einzelnes Modell statt des Mittels, Startwert 3 | +115 174 | +2,77 | 1,44 | +142 533 (2,9) | 0,26 | +127 821 | -12 646 |
| ein einzelnes Modell statt des Mittels, Startwert 4 | +117 018 | +3,13 | 1,56 | +140 928 (3,7) | 0,34 | +106 120 | +10 898 |
| Mittel über die Startwerte 5–9 | +152 737 | +3,79 | 2,08 | +160 535 (3,6) | 0,72 | +160 873 | -8 136 |
| Mittel über die Startwerte 10–14 | +163 320 | +3,88 | 1,84 | +162 626 (3,5) | 0,89 | +170 096 | -6 776 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): -26 977 bis +182 636 €.
Ein einzelnes Modell landet je nach Zufallsstartwert bei +73 242 bis +167 749 € (t 0,93 bis 2,28). So groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das Hauptmodell fünf Startwerte.
Mittel über fünf Startwerte: 0–4 (Hauptmodell): +152 275 € (t 1,95), 5–9: +152 737 € (t 2,08), 10–14: +163 320 € (t 1,84).

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4,91 | 3,5 | +2,55 | 3,0 | +4,71 | +4,88 | +8,77 | +2,50 | +9,99 |
| Solar | -8,44 | -6,7 | -8,19 | -14,0 | – | -11,66 | -8,18 | -7,71 | – |
| Wind an Land | -4,25 | -2,1 | -5,23 | -6,6 | -6,04 | -6,96 | +3,50 | -7,72 | -11,15 |
| Wind auf See | -6,87 | -2,9 | -5,78 | -5,1 | -9,67 | -8,98 | -3,83 | -10,73 | -9,08 |
| Last | +0,85 | 1,4 | +0,15 | 0,5 | -0,37 | -0,83 | +1,51 | +2,65 | -0,47 |

n = 40 036 Viertelstunden, R² = 0,03, gekappt 0,13. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens 24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---|---:|---:|---:|---:|
| icon_eu | 2026-04-05 bis 2026-10-31 | Tag 1 (behauptet ≥ 24 h) | 80 640 | 79 272 | 24 / 27 / 33 h | 0 |
| icon_eu | 2026-04-05 bis 2026-10-31 | Tag 2 (behauptet ≥ 48 h) | 80 640 | 66 706 | 45 / 50 / 53 h | 140 |
| ecmwf_ifs | 2025-10-01 bis 2026-10-31 | Tag 1 (behauptet ≥ 24 h) | 152 064 | 120 739 | 18 / 27 / 71 h | 6 |
| ecmwf_ifs | 2025-10-01 bis 2026-10-31 | Tag 2 (behauptet ≥ 48 h) | 152 064 | 117 259 | 29 / 51 / 71 h | 7 |

Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die gemessene Veröffentlichungszeit.
Gemessen: icon_eu 2,9 bis 4,3 h nach Laufstart (424 Läufe; das Archiv setzt 4,5 h an); ecmwf_ifs 6,0 bis 8,2 h nach Laufstart (214 Läufe; das Archiv setzt 8,5 h an).


<sub>Gerechnet am 2026-11-22 06:06 UTC, Code 904176c, Wetterdaten akderekaan/de-power-forecast-data @ bb411f9fe986.</sub>
