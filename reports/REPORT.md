# Backtest-Report

Alle Zahlen im Detail. Die Kurzfassung steht im [README](../README.md).

Testzeitraum 2026-01-01 bis 2026-11-06 (310 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0,25 €/MWh je Seite, 1,0 €/MWh Slippage beim Ausstieg, 10 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3,76). Nicht geschlagen: Immer long (t -0,52), Vorzeichen je Viertelstunde (28 T) (t 0,72), Letztes bekanntes Vorzeichen (t 1,23).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +4,31 €/MWh netto bei 1,0 €/MWh Slippage. Kostet der Ausstieg mehr als 5,3 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +167 138 € auf 25 140 MWh, short -289 € auf 13 580 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben +24 262 € von +166 849 €.

![PnL](pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +166 849 | +4,31 | 38 720 | 51 % | 2,39 | 2,26 | -67 590 | -31 591 | 0 |
| Immer long | +243 809 | +3,28 | 74 400 | 45 % | 2,22 | 1,74 | -129 624 | -48 138 | 0 |
| Immer short | -467 009 | -6,28 | 74 400 | 50 % | -4,25 | -3,33 | -474 417 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +108 132 | +1,45 | 74 400 | 49 % | 1,46 | 1,28 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +41 223 | +0,55 | 74 382 | 48 % | 0,50 | 0,47 | -66 427 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -248,3 | -0,52 | +341,0 | 1,00 |
| Immer short | +2 044,7 | 3,76 | +1 407,5 | 4,30 |
| Vorzeichen je Viertelstunde (28 T) | +189,4 | 0,72 | +338,0 | 1,90 |
| Letztes bekanntes Vorzeichen | +405,2 | 1,23 | +621,6 | 3,36 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +166 849 | -10 282 | +24 262 | +175 860 (3,5) | +159 428 (3,7) | +123 921 (3,4) |
| Immer long | +243 809 | +33 512 | +20 738 | +141 640 (1,3) | +53 709 (0,6) | -39 749 (-0,5) |
| Immer short | -467 009 | -33 587 | -597 521 | -364 840 (-3,4) | -276 909 (-2,9) | -183 451 (-2,3) |
| Vorzeichen je Viertelstunde (28 T) | +108 132 | +33 512 | -36 445 | +62 442 (1,2) | +54 643 (1,2) | +32 225 (0,8) |
| Letztes bekanntes Vorzeichen | +41 223 | +44 228 | -140 377 | -13 487 (-0,3) | -33 258 (-0,8) | -43 638 (-1,2) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0,0 | 1,0 | 2,0 | 5,0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +205 569 | +166 849 | +128 129 | +11 969 | 5,3 |
| Immer long | +318 209 | +243 809 | +169 409 | -53 791 | 4,3 |
| Immer short | -392 609 | -467 009 | -541 409 | -764 609 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +182 532 | +108 132 | +33 732 | -189 468 | 2,5 |
| Letztes bekanntes Vorzeichen | +115 605 | +41 223 | -33 160 | -256 307 | 1,6 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +167 138 (25 140) | -289 (13 580) |
| Immer long | +243 809 (74 400) | +0 (0) |
| Immer short | +0 (0) | -467 009 (74 400) |
| Vorzeichen je Viertelstunde (28 T) | +219 339 (45 488) | -111 207 (28 912) |
| Letztes bekanntes Vorzeichen | +201 313 (35 312) | -160 090 (39 070) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -4 988 | 128 | 30 | 90 |
| 2026-02 | -796 | 118 | 30 | 121 |
| 2026-03 | +13 173 | 1 920 | 15 | 149 |
| 2026-04 | -2 288 | 2 855 | 10 | 180 |
| 2026-05 | +16 870 | 3 845 | 10 | 210 |
| 2026-06 | +37 588 | 5 278 | 5 | 241 |
| 2026-07 | +33 093 | 6 552 | 2 | 271 |
| 2026-08 | +18 464 | 5 088 | 5 | 302 |
| 2026-09 | +67 542 | 6 125 | 2 | 333 |
| 2026-10 | -13 131 | 6 738 | 2 | 363 |
| 2026-11 | +1 322 | 75 | 30 | 394 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste Version fest (erste Zeile). Danach wurde das Hauptmodell dreimal geändert: Lastprognose entfernt (Zeitstempel nicht belegbar), Mittel aus fünf Startwerten (ein Einzel-Fit hing stark am Startwert), Handelsschwelle nie unter den Round-trip-Kosten. Keine der Änderungen hat den PnL im Test gesenkt. Alle anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **erste Version, vor dem ersten Backtest festgelegt (mit Lastprognose, ein einzelnes Modell, Startwert 0, Schwelle 0 erlaubt)** | +112 604 | +2,99 | 1,41 | +123 990 (3,0) | 0,05 | +125 311 | -12 707 |
| **Hauptmodell: ohne Lastprognose, Mittel aus fünf Startwerten, Schwelle mindestens 2 €/MWh** | +166 849 | +4,31 | 2,26 | +159 428 (3,7) | 0,72 | +167 138 | -289 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose | +159 235 | +4,64 | 2,27 | +151 756 (3,5) | 0,63 | +143 708 | +15 528 |
| Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten) | +101 656 | +2,70 | 1,53 | +90 507 (2,4) | -0,07 | +167 006 | -65 351 |
| ohne MW-Features (keine installierte Leistung) | +186 095 | +4,77 | 2,48 | +132 438 (2,9) | 1,06 | +178 435 | +7 660 |
| _Entscheidungsregel_ | | | | | | | |
| Schwelle 0 erlaubt (Regel bis 9. Oktober 2026) | +164 139 | +4,05 | 2,27 | +158 720 (3,7) | 0,69 | +170 142 | -6 002 |
| feste Schwelle 2 €/MWh, nichts gewählt | +31 489 | +0,48 | 0,27 | +80 626 (1,1) | -0,68 | +157 187 | -125 698 |
| Schwelle auf 56 statt 28 Tagen gewählt | +115 237 | +3,03 | 1,36 | +127 094 (2,8) | 0,08 | +147 238 | -32 001 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +97 804 | +8,70 | 1,82 | +75 999 (3,1) | -0,12 | +97 103 | +701 |
| getrennte Schwellen für long und short, „nie“ erlaubt | +171 057 | +4,74 | 2,55 | +119 926 (2,9) | 0,98 | +176 627 | -5 570 |
| Größe nach Signalstärke (10–20 MW) | +337 152 | +4,76 | 2,40 | +310 509 (3,8) | 1,78 | +333 263 | +3 889 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | -9 143 | -0,28 | -0,16 | +73 515 (1,8) | -1,09 | +51 755 | -60 897 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +116 649 | +3,07 | 1,72 | +130 511 (3,2) | 0,10 | +167 508 | -50 858 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +84 279 | +1,98 | 1,02 | +110 682 (2,5) | -0,29 | +114 001 | -29 721 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +127 601 | +3,72 | 1,46 | +153 923 (3,7) | 0,25 | +134 958 | -7 357 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +40 848 | +1,96 | 0,59 | +54 430 (1,2) | -0,82 | +46 213 | -5 365 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -68 248 | -3,05 | -1,14 | +25 223 (0,9) | -1,94 | -10 006 | -58 243 |
| ohne Spread-Historie | +134 035 | +3,05 | 1,74 | +130 420 (3,1) | 0,33 | +188 290 | -54 255 |
| ohne Day-Ahead-Preise des Vortags | +161 213 | +4,61 | 2,40 | +108 077 (2,7) | 0,65 | +185 132 | -23 919 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-11-06) | +145 149 | +3,42 | 1,90 | +141 987 (3,1) | 0,71 | +158 304 | -13 155 |
| _Zufallsstartwert_ | | | | | | | |
| ein einzelnes Modell statt des Mittels, Startwert 0 | +134 533 | +3,73 | 1,87 | +114 864 (3,0) | 0,29 | +163 542 | -29 009 |
| ein einzelnes Modell statt des Mittels, Startwert 1 | +96 878 | +2,46 | 1,14 | +125 053 (3,0) | -0,14 | +131 956 | -35 077 |
| ein einzelnes Modell statt des Mittels, Startwert 2 | +169 739 | +3,68 | 2,21 | +138 126 (2,9) | 0,67 | +205 420 | -35 681 |
| ein einzelnes Modell statt des Mittels, Startwert 3 | +131 247 | +3,49 | 1,61 | +130 432 (3,1) | 0,30 | +143 468 | -12 220 |
| ein einzelnes Modell statt des Mittels, Startwert 4 | +64 608 | +1,95 | 0,86 | +110 987 (3,0) | -0,52 | +87 749 | -23 141 |
| Mittel über die Startwerte 5–9 | +121 016 | +2,58 | 1,34 | +135 709 (3,0) | 0,16 | +150 908 | -29 891 |
| Mittel über die Startwerte 10–14 | +141 955 | +3,52 | 1,67 | +135 334 (3,1) | 0,43 | +164 543 | -22 588 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): -9 143 bis +186 095 €.
Ein einzelnes Modell landet je nach Zufallsstartwert bei +64 608 bis +169 739 € (t 0,86 bis 2,21). So groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das Hauptmodell fünf Startwerte.
Mittel über fünf Startwerte: 0–4 (Hauptmodell): +166 849 € (t 2,26), 5–9: +121 016 € (t 1,34), 10–14: +141 955 € (t 1,67).

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4,97 | 3,6 | +2,58 | 3,1 | +4,83 | +4,89 | +9,02 | +2,60 | +10,19 |
| Solar | -8,38 | -6,6 | -8,14 | -13,9 | – | -11,72 | -8,13 | -7,78 | – |
| Wind an Land | -4,06 | -1,9 | -5,08 | -6,3 | -6,13 | -6,77 | +4,07 | -7,61 | -11,26 |
| Wind auf See | -6,12 | -2,4 | -5,08 | -4,3 | -9,49 | -8,79 | -2,67 | -10,38 | -8,53 |
| Last | +0,76 | 1,2 | +0,04 | 0,1 | -0,40 | -0,91 | +1,41 | +2,54 | -0,49 |

n = 38 596 Viertelstunden, R² = 0,03, gekappt 0,12. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens 24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---|---:|---:|---:|---:|
| icon_eu | 2026-04-05 bis 2026-10-31 | Tag 1 (behauptet ≥ 24 h) | 80 640 | 79 272 | 24 / 27 / 33 h | 0 |
| icon_eu | 2026-04-05 bis 2026-10-31 | Tag 2 (behauptet ≥ 48 h) | 80 640 | 66 706 | 45 / 50 / 53 h | 140 |
| ecmwf_ifs | 2025-10-01 bis 2026-10-31 | Tag 1 (behauptet ≥ 24 h) | 152 064 | 120 739 | 18 / 27 / 71 h | 6 |
| ecmwf_ifs | 2025-10-01 bis 2026-10-31 | Tag 2 (behauptet ≥ 48 h) | 152 064 | 117 259 | 29 / 51 / 71 h | 7 |

Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die gemessene Veröffentlichungszeit.
Gemessen: icon_eu 2,9 bis 4,3 h nach Laufstart (312 Läufe; das Archiv setzt 4,5 h an); ecmwf_ifs 6,0 bis 8,2 h nach Laufstart (158 Läufe; das Archiv setzt 8,5 h an).


<sub>Gerechnet am 2026-11-08 06:06 UTC, Code 84649be, Wetterdaten akderekaan/de-power-forecast-data @ b29c2ac8afd5.</sub>
