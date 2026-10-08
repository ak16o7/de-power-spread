# DE Power Spread

Ein Handelsexperiment am deutschen Strommarkt mit ehrlicher Buchführung. Um 11:00 am Vortag
wird für jede Viertelstunde entschieden: Day-Ahead kaufen, verkaufen oder nichts tun. Kurz vor
Lieferung wird glattgestellt, und dieser Ausstieg wird zum ID-AEP bewertet, dem Index der
letzten 500 MW im Intraday-Handel. Gemessen wird in Euro nach Kosten, gegen dumme Baselines,
walk-forward und live mit Zeitstempel.

**Die Frage:** Enthalten Wetterprognosen, die um 11:00 am Vortag öffentlich verfügbar sind,
Information über den Intraday-Preis, die der Day-Ahead-Preis noch nicht hat, und bleibt
nach Kosten etwas übrig?

**Die Antwort bisher** (Oktober 2026; die Zahlen darunter werden wöchentlich neu gerechnet):

- **Ein wenig, ja.** Das Modell verdient im Test Geld, und das Geld kommt aus den
  Wetterdaten: Ohne sie ist es weg (Robustheitstabelle).
- **Aber nicht genug für das eigene Kriterium.** Das Modell schlägt die einfachen Baselines
  nicht signifikant. Ungekappt verdient sogar „Immer long" mehr, allerdings fast nur mit
  Preisspitzen; mit gekappten Spitzen liegt das Modell vorn, aber auch dann nicht
  signifikant vor „Vorzeichen je Viertelstunde".
- **Der Gewinn ist einseitig und klumpig.** Er kommt fast nur aus der Long-Seite und zu
  einem großen Teil aus wenigen Tagen mit Preisspitzen.
- **Alles hängt an der Ausführung.** Der Ausstieg ist zum ID-AEP bewertet, einem Index, zu
  dem niemand handeln kann. Die Gewinnschwelle im Ergebnisteil sagt, wie viel schlechter als
  der Index echte Ausführung sein darf.

Ein sauber gemessenes, schwaches Signal also, kein Geldautomat. Die ehrliche Zahl ist hier
das Ergebnis.

## Warum genau dieser Trade

- **Der Einstieg ist echt handelbar.** Eine preisunabhängige Order in der Day-Ahead-Auktion
  um 12:00 bekommt sicher den Clearingpreis. Dafür muss die Entscheidung vor 12:00 fallen.
  Jede spätere Entscheidung bräuchte einen Intraday-Einstiegspreis; wer trotzdem zum
  Day-Ahead-Preis einsteigt, hat Lookahead im Backtest.
- **Der Ausstieg ist eine Benchmark, kein Preis.** In echt stellt man im kontinuierlichen
  Intraday-Handel glatt. Bewertet wird das zum ID-AEP der Übertragungsnetzbetreiber: dem
  mengengewichteten Preis der letzten Geschäfte des Viertelstundenprodukts im deutschen
  Continuous-Handel, bis 500 MW erreicht sind. Reicht das Viertelstundenprodukt nicht,
  zählen Geschäfte des Stundenprodukts dazu. Inhaltlich ist das der ID500; „AEP" im Namen
  steht dafür, dass der Ausgleichsenergiepreis an ihn gekoppelt ist. Zum Index selbst kann
  niemand handeln. Echte Fills liegen darüber oder darunter, je nach Zeitpunkt, Orderbuch
  und Geld-Brief-Spanne. Genau diesen Abstand soll die angenommene Slippage abdecken.
  Freie Intraday-Tickdaten gibt es nicht (EPEX verkauft sie), der ID-AEP ist der einzige
  freie Intraday-Preis nahe an der Lieferung.
- **Kein Geld aus dem reBAP.** Die Position ist vor Lieferung immer flach. Wer den
  Bilanzkreis offen lässt, um Ausgleichsenergie zu kassieren, verletzt die Bilanzkreistreue.
  Das ist keine Strategie, sondern ein Verstoß.

## Ergebnisse

<!-- RESULTS:START -->
Testzeitraum 2026-01-01 bis 2026-10-07 (280 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet zum ID-AEP (Benchmark, kein handelbarer Preis). Kosten: 0.25 €/MWh je Seite, 1.0 €/MWh Slippage beim Ausstieg, 10.0 €/MWh Strafe, wenn der ID-AEP fehlt.

**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline im Tages-PnL mit t > 2 schlägt): **nicht erfüllt**. Geschlagen: Immer short (t 3.48). Nicht geschlagen: Immer long (t -0.26), Vorzeichen je Viertelstunde (28 T) (t 0.61), Letztes bekanntes Vorzeichen (t 1.07).

- **Gewinnschwelle der Ausführung:** Das Modell verdient +4.26 €/MWh netto bei 1.0 €/MWh Slippage. Kostet der Ausstieg mehr als 5.3 €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das schafft, kann dieser Backtest nicht zeigen: der ID-AEP ist ein Index, kein Preis, zu dem man handeln kann.
- **Long gegen Short:** long +182 177 € auf 23 115 MWh, short -30 112 € auf 12 610 MWh.
- **Spitzen:** ohne die 10 besten Tage bleiben +16 341 € von +152 065 €.

![PnL](reports/pnl.png)

| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Modell** | +152 065 | +4.26 | 35 725 | 51 % | 2.61 | 2.45 | -40 817 | -31 134 | 0 |
| Immer long | +189 252 | +2.82 | 67 190 | 44 % | 1.90 | 1.38 | -129 624 | -48 138 | 0 |
| Immer short | -390 822 | -5.82 | 67 190 | 50 % | -3.93 | -2.84 | -398 874 | -30 949 | 0 |
| Vorzeichen je Viertelstunde (28 T) | +103 275 | +1.54 | 67 190 | 49 % | 1.51 | 1.25 | -57 401 | -44 370 | 0 |
| Letztes bekanntes Vorzeichen | +65 797 | +0.98 | 67 172 | 49 % | 0.88 | 0.78 | -39 963 | -27 745 | 0 |

**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):

| gegen | Ø €/Tag | t (HAC) | Ø €/Tag, Spread gekappt ±200 | t |
|---|---:|---:|---:|---:|
| Immer long | -132.8 | -0.26 | +390.8 | 1.16 |
| Immer short | +1 938.9 | 3.48 | +1 218.1 | 3.54 |
| Vorzeichen je Viertelstunde (28 T) | +174.2 | 0.61 | +211.7 | 1.22 |
| Letztes bekanntes Vorzeichen | +308.1 | 1.07 | +523.4 | 2.90 |

**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.

| Strategie | ungekappt | davon 10 größte Viertelstunden | ohne die 10 besten Tage | ±500 | ±200 | ±100 |
|---|---:|---:|---:|---:|---:|---:|
| Modell | +152 065 | +16 466 | +16 341 | +134 009 (3.4) | +124 455 (3.7) | +102 392 (3.6) |
| Immer long | +189 252 | +26 937 | -33 820 | +99 641 (0.9) | +15 036 (0.2) | -67 739 (-0.9) |
| Immer short | -390 822 | -27 012 | -518 909 | -301 211 (-2.9) | -216 606 (-2.4) | -133 831 (-1.8) |
| Vorzeichen je Viertelstunde (28 T) | +103 275 | +26 937 | -35 965 | +70 144 (1.4) | +65 184 (1.6) | +45 334 (1.2) |
| Letztes bekanntes Vorzeichen | +65 797 | +50 803 | -115 155 | -1 471 (-0.0) | -22 089 (-0.6) | -32 758 (-0.9) |

**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von

| Strategie | 0.0 | 1.0 | 2.0 | 5.0 | Gewinnschwelle €/MWh |
|---|---:|---:|---:|---:|---:|
| Modell | +187 790 | +152 065 | +116 340 | +9 165 | 5.3 |
| Immer long | +256 442 | +189 252 | +122 062 | -79 508 | 3.8 |
| Immer short | -323 632 | -390 822 | -458 012 | -659 582 | – (verliert schon ohne Slippage) |
| Vorzeichen je Viertelstunde (28 T) | +170 465 | +103 275 | +36 085 | -165 485 | 2.5 |
| Letztes bekanntes Vorzeichen | +132 969 | +65 797 | -1 376 | -202 893 | 2.0 |

**Long- und Short-Seite** (netto €, in Klammern MWh)

| Strategie | long | short |
|---|---:|---:|
| Modell | +182 177 (23 115) | -30 112 (12 610) |
| Immer long | +189 252 (67 190) | +0 (0) |
| Immer short | +0 (0) | -390 822 (67 190) |
| Vorzeichen je Viertelstunde (28 T) | +185 879 (40 780) | -82 603 (26 410) |
| Letztes bekanntes Vorzeichen | +181 240 (31 490) | -115 443 (35 682) |

**Modell je Monat**

| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |
|---|---:|---:|---:|---:|
| 2026-01 | -4 321 | 180 | 30 | 90 |
| 2026-02 | +570 | 318 | 30 | 121 |
| 2026-03 | +4 414 | 340 | 30 | 149 |
| 2026-04 | +20 480 | 2 770 | 10 | 180 |
| 2026-05 | +11 342 | 6 928 | 2 | 210 |
| 2026-06 | +27 808 | 7 200 | 0 | 241 |
| 2026-07 | +21 728 | 6 445 | 2 | 271 |
| 2026-08 | +48 284 | 4 975 | 5 | 302 |
| 2026-09 | +28 161 | 5 060 | 5 | 333 |
| 2026-10 | -6 399 | 1 510 | 2 | 363 |

### Robustheit: alle getesteten Varianten

Gleicher Walk-forward, gleiche Kosten. Das Hauptmodell stand vor dem ersten echten Backtest fest; die Varianten kamen danach. Alle stehen hier, auch die schlechten. Die beste Zeile als Strategie zu nehmen wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.

| Variante | Netto € | €/MWh | t | Spread gekappt ±200: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |
|---|---:|---:|---:|---:|---:|---:|---:|
| _Hauptmodell_ | | | | | | | |
| **Hauptmodell (Einstellungen vorab festgelegt, ohne Lastprognose)** | +152 065 | +4.26 | 2.45 | +124 455 (3.7) | 0.61 | +182 177 | -30 112 |
| _Datenstand_ | | | | | | | |
| mit Lastprognose (erste Version des Projekts) | +101 647 | +2.67 | 1.54 | +103 278 (2.8) | -0.02 | +165 504 | -63 856 |
| Wetter nur so frisch wie im Archiv (ohne die vollständigen Läufe ab Juni) | +151 037 | +3.86 | 2.29 | +124 124 (3.4) | 0.56 | +181 881 | -30 844 |
| ohne MW-Features (keine installierte Leistung) | +131 849 | +3.44 | 2.09 | +108 721 (3.0) | 0.38 | +175 961 | -44 112 |
| _Entscheidungsregel_ | | | | | | | |
| feste Schwelle 2 €/MWh, nichts gewählt | +138 650 | +2.33 | 1.68 | +119 112 (2.3) | 0.43 | +206 180 | -67 531 |
| Schwelle auf 56 statt 28 Tagen gewählt | +96 723 | +3.13 | 1.48 | +86 935 (2.3) | -0.08 | +134 446 | -37 723 |
| Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt | +115 368 | +4.33 | 2.00 | +87 531 (3.1) | 0.16 | +149 279 | -33 911 |
| getrennte Schwellen für long und short, „nie" erlaubt | +175 632 | +4.44 | 2.64 | +118 056 (3.1) | 1.03 | +188 899 | -13 268 |
| Größe nach Signalstärke (10–20 MW) | +317 218 | +3.89 | 2.39 | +263 504 (3.7) | 1.84 | +329 881 | -12 663 |
| _Modell_ | | | | | | | |
| Median- statt Quadratverlust | +15 206 | +0.53 | 0.31 | +70 394 (2.2) | -0.93 | +76 079 | -60 874 |
| stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt) | +125 344 | +3.07 | 2.12 | +137 479 (3.8) | 0.23 | +140 737 | -15 393 |
| Trainingsziel hart auf ±100 €/MWh gekappt | +121 396 | +3.06 | 1.69 | +114 291 (3.3) | 0.15 | +117 376 | +4 020 |
| Mittel aus 5 Modellen auf Tages-Bootstraps | +146 075 | +3.86 | 2.37 | +146 903 (3.9) | 0.49 | +141 034 | +5 041 |
| zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen | +28 851 | +1.48 | 0.48 | -16 923 (-0.5) | -0.91 | +81 561 | -52 709 |
| _Feature-Gruppe weggelassen_ | | | | | | | |
| ohne Wetter | -10 046 | -0.39 | -0.16 | +50 914 (1.8) | -1.45 | +50 068 | -60 115 |
| ohne Spread-Historie | +166 118 | +4.85 | 2.23 | +126 583 (3.4) | 0.52 | +172 649 | -6 531 |
| ohne Day-Ahead-Preise des Vortags | +180 628 | +4.48 | 2.23 | +110 197 (2.8) | 0.67 | +172 881 | +7 747 |
| _Startmonat_ | | | | | | | |
| Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt) (2025-12-01 bis 2026-10-07) | +128 055 | +3.23 | 1.96 | +104 704 (2.8) | 0.57 | +172 314 | -44 259 |
| _Zufallsstartwert_ | | | | | | | |
| Hauptmodell mit Zufallsstartwert 1 statt 0 | +156 071 | +4.00 | 2.27 | +133 742 (3.4) | 0.54 | +186 321 | -30 251 |
| Hauptmodell mit Zufallsstartwert 2 statt 0 | +44 744 | +1.25 | 0.78 | +87 881 (2.6) | -0.70 | +108 834 | -64 090 |
| Hauptmodell mit Zufallsstartwert 3 statt 0 | +176 158 | +4.28 | 2.56 | +130 078 (3.4) | 0.86 | +195 711 | -19 553 |
| Hauptmodell mit Zufallsstartwert 4 statt 0 | +82 743 | +2.33 | 1.57 | +102 140 (3.1) | -0.24 | +126 233 | -43 490 |

Spanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): +15 206 bis +176 158 €.
Allein der Zufallsstartwert bewegt das Hauptmodell zwischen +44 744 und +176 158 € (t 0.78 bis 2.56): so groß ist das Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt.

### Was ein Prognosefehler kostet (ex post)

| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t | gekappt ±200 | t | 00-06 | 06-10 | 10-16 | 16-20 | 20-24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Konstante | +4.58 | 3.2 | +2.05 | 2.5 | +4.71 | +3.84 | +10.20 | +1.92 | +9.59 |
| Solar | -7.90 | -6.1 | -7.64 | -12.9 | – | -11.47 | -7.69 | -7.55 | – |
| Wind an Land | -3.81 | -1.7 | -4.79 | -5.9 | -6.18 | -8.06 | +5.00 | -7.00 | -11.06 |
| Wind auf See | -5.92 | -2.2 | -4.72 | -4.0 | -9.30 | -8.02 | -3.58 | -10.49 | -8.52 |
| Last | +0.75 | 1.1 | -0.02 | -0.1 | -0.46 | -1.08 | +1.86 | +2.42 | -0.63 |

n = 35 712 Viertelstunden, R² = 0.03, gekappt 0.12. t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt": Spread auf ±200 €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–": Fehler schwankt dort zu wenig (Standardabweichung unter 250 MW) für eine sinnvolle Steigung.

### Stimmen die Zeitstempel der Wetterdaten?

Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1" = mindestens 24 h alt, „Tag 2" = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).

| Wettermodell | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |
|---|---|---:|---:|---:|---:|
| icon_eu | Tag 1 (behauptet ≥ 24 h) | 41 712 | 41 709 | 24 / 27 / 29 h | 0 |
| icon_eu | Tag 2 (behauptet ≥ 48 h) | 41 712 | 41 712 | 48 / 51 / 53 h | 0 |
| ecmwf_ifs | Tag 1 (behauptet ≥ 24 h) | 41 952 | 41 759 | 24 / 27 / 41 h | 0 |
| ecmwf_ifs | Tag 2 (behauptet ≥ 48 h) | 41 952 | 41 759 | 48 / 51 / 65 h | 0 |

Gültigkeitszeiten 2026-06-14 bis 2026-10-11, wo es beide Datenarten gibt. Ein Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide haben, exakt einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet" zählt Werte aus einem Lauf mit kürzerem Vorlauf als angegeben.
Gemessene Veröffentlichung live mitgeschnittener Läufe: icon_eu 2.87–4.22 h nach Laufstart (71 Läufe; im Archiv angesetzt: 4.5 h); ecmwf_ifs 6.12–7.5 h nach Laufstart (37 Läufe; im Archiv angesetzt: 8.5 h).


<sub>Gerechnet am 2026-10-08 22:59 UTC, Code aa795f7, Wetterdaten akderekaan/de-power-forecast-data @ 58d14fac3406.</sub>

<!-- RESULTS:END -->

## Live-Track-Record

Jeden Tag schreibt eine GitHub Action zwischen 10:45 und 11:50 die Positionen für morgen nach
`signals/` und committet sie. Das Verfahren ist dasselbe wie im Backtest: das Modell des
Liefermonats, trainiert auf dem, was am ersten Tag des Monats bekannt war, dieselbe
Schwellenregel und derselbe Verfügbarkeitsfilter für jedes Feature (ein Test prüft, dass
Live und Backtest für denselben Tag dieselben Positionen liefern). Der Commit ist der
Zeitstempel: Das Signal existierte vor der Auktion. Sobald der ID-AEP veröffentlicht ist,
wird mit derselben PnL-Funktion abgerechnet (`live/ledger.csv`). Ein Signal, das erst nach
11:50 fertig ist, wird markiert und nie gezählt.

Der Live-Teil ist der einzige Test, den vorher niemand gesehen hat. Alles im Backtest wurde
mindestens einmal angeschaut, auch wenn das Hauptmodell vorher feststand.

<!-- LIVE:START -->
_Noch kein abgerechneter Tag._
<!-- LIVE:END -->

## Methode

### Daten und wann sie bekannt sind

| Quelle | Inhalt | gilt als bekannt ab |
|---|---|---|
| ENTSO-E A44, ohne Key: Energy-Charts (SMARD) | Day-Ahead-Preis DE-LU je Viertelstunde | 13:30 am Vortag der Lieferung (Ergebnis gegen 12:45) |
| netztransparenz.de `IdAep`, ohne Zugang: CSV-Download der Webseite | ID-AEP je Viertelstunde (Ausstiegs-Benchmark, Label) | 00:00 zwei Tage nach Lieferung; konservativ, beobachtet wurde die Veröffentlichung am Folgetag |
| [de-power-forecast-data](https://huggingface.co/datasets/akderekaan/de-power-forecast-data) | ICON-EU und ECMWF IFS an 16 Punkten, mit `available_at` | laut `available_at`, gegen die Daten geprüft (Ergebnisteil) |
| dito | Installierte Leistung (Energy-Charts) | Wert von vor zwei Monaten |
| dito | Ist-Erzeugung A75 und ÜNB-Prognose A69 | nur ex post: Teil 1 und Trainingsziel der zweistufigen Variante, nie ein Feature |
| ENTSO-E A65, ohne Key: Energy-Charts | Last und Day-Ahead-Lastprognose | nur ex post (Teil 1). Nicht im Modell: Wann ein gespeicherter Wert veröffentlicht oder ob er später revidiert wurde, sagt keine der Quellen |

**Wetter, zwei Arten von Daten.** Für die ganze Historie gibt es das Archiv der
Previous Runs (Open-Meteo): für jede Gültigkeitszeit den Wert, der etwa 24 h und etwa 48 h
vorher vorhergesagt wurde. Ab dem 10. Juni 2026 kommen vollständige Läufe dazu (bis zum
28. September nachgeladen, seitdem live mitgeschnitten), mit jeder Vorlaufzeit ab 24 h. Ab
Mitte Juni sind die Features deshalb frischer als davor. Das war echte, zur Entscheidung
verfügbare Information. Die Robustheitstabelle zeigt die Variante, die die vollständigen
Läufe auf das Archivformat zurückschneidet.

Zeitraum ab 1. Oktober 2025: Seitdem läuft Day-Ahead in Viertelstunden. Ein Regime.

### Teil 1: Was ein Prognosefehler in Euro kostet (ex post)

Regression je Viertelstunde: Spread (ID-AEP − Day-Ahead) auf die Fehler der ÜNB-Day-Ahead-Prognose
(Ist − Prognose) für Solar, Wind an Land, Wind auf See und Last, in GW. Newey-West-Standardfehler
mit einem Tag Lags, zusätzlich getrennt nach Tageszeit. Das übersetzt einen Prognosefehler in
€/MWh. Die ÜNB-Prognose erscheint um 18:00, also nach der Auktion: Sie erklärt Spreads, sie
handelt nie.

### Teil 2: Die Strategie (ex ante)

- **Features um 11:00 D-1**, jede Quelle nach ihrer eigenen Verfügbarkeit gefiltert:
  - Wetter je Modell: Windleistungs-Proxy an Land und auf See, Einstrahlung, Klarheitsindex,
    Temperatur, Bewölkung, Revision gegenüber dem Stand 24 h vorher, Uneinigkeit ECMWF − ICON.
    Nur Prognosen, die mindestens 24 h vor ihrer Gültigkeit gemacht wurden.
  - Leistungs-Proxy: Wind- und Solar-MW (Proxy × installierte Leistung).
  - Preise: Day-Ahead-Preise von D-1.
  - Spread-Historie: nur Tage, deren ID-AEP um 11:00 bekannt war (D-3 und älter).
  - Kalender: Viertelstunde, Wochentag, bundesweiter Feiertag, Sonnenstand.
- **Modell**: Gradient Boosting (scikit-learn, feste Einstellungen) auf den Spread, Ausreißer im
  Trainingsziel auf das 1.–99. Perzentil gekappt. Vorhersage ist das Mittel aus fünf Fits mit
  verschiedenen Zufallsstartwerten.
- **Handel**: Vorzeichen der Vorhersage, nur wenn ihr Betrag die Schwelle übersteigt. Die
  Schwelle wählt ein Modell, das die letzten 28 Trainingstage nicht gesehen hat, auf genau diesen
  Tagen. Danach wird auf dem ganzen Fenster neu trainiert.
- **Walk-forward**: Monat M wird mit einem Modell gehandelt, das nur Labels kennt, die vor der
  Entscheidung für M's ersten Tag bekannt waren. Der erste Testmonat braucht 60 gelabelte Tage.

Diese Einstellungen standen vor dem ersten Backtest auf echten Daten fest. Geändert wurde danach
zweierlei, beides aus Gründen, die nicht am PnL hängen:

1. Die Lastprognose flog aus den Features, weil ihr Veröffentlichungszeitpunkt nicht belegbar ist.
2. Das Modell mittelt fünf Zufallsstartwerte statt einen. Der Startwert steuert nur die
   zufällige Early-Stopping-Stichprobe im Gradient Boosting, hat das Ergebnis eines einzelnen
   Modells aber stark verschoben. Mitteln ist reine Varianzreduktion und wurde beschlossen,
   bevor sein eigenes Ergebnis feststand.

Beides hat den PnL im Test verändert. Die alten Varianten (mit Lastprognose, einzelne Modelle je
Startwert) stehen in der Robustheitstabelle.

### Die Latte: Baselines

| Baseline | Regel |
|---|---|
| Immer long / immer short | jede Viertelstunde, gleiche Größe |
| Vorzeichen je Viertelstunde (28 T) | Vorzeichen des mittleren Spreads derselben Uhrzeit über die letzten 28 bekannten Tage |
| Letztes bekanntes Vorzeichen | Vorzeichen derselben Viertelstunde am neuesten bekannten Tag (D-3) |

Verdient eine Baseline Geld, ist das eine Risikoprämie oder ein Kalendereffekt, kein Alpha aus
der Prognose. **Vorab festgelegtes Kriterium:** Das Modell zählt nur, wenn es jede Baseline im
Tages-PnL mit t > 2 (Newey-West) schlägt. Das Urteil steht automatisch über den Ergebnistabellen.

### Kosten

10 MW je gehandelter Viertelstunde, 0,25 €/MWh je Seite, 1 €/MWh Slippage gegenüber dem ID-AEP
beim Ausstieg, alles in `dps/config.py`. Das sind Annahmen, keine Gebührenliste einer Börse; die
Tabelle „Kostenempfindlichkeit" zeigt den PnL für 0 bis 5 €/MWh Slippage und die Gewinnschwelle.
Fehlt der ID-AEP (unter 500 MW Umsatz), wird die Position mit 10 €/MWh Verlust gebucht statt
still verworfen.

### Robustheit

Nach dem ersten echten Backtest wurde geprüft, wie stark das Ergebnis an den vorab gewählten
Einstellungen hängt: andere Schwellenregeln, Größe nach Signalstärke, andere Verlustfunktion,
stärkere Regularisierung, Bagging, ein zweistufiges Modell über die ÜNB-Prognosefehler,
weggelassene Feature-Gruppen, anderer Datenstand, anderer Startmonat, einzelne Modelle statt des
Mittels und andere Zufallsstartwerte.
Alle Varianten stehen in der Tabelle im Ergebnisteil, auch die schlechten, und werden mit
`python -m dps robustness` neu gerechnet. Die Tabelle ist kein Menü: Die beste Zeile als
Strategie zu nehmen hieße, sich an den Testzeitraum anzupassen.

## Ehrliche Grenzen

- **Der Ausstieg ist eine Benchmark.** Siehe oben. Die Gewinnschwelle sagt, wie gut echte
  Ausführung gegen den ID-AEP sein müsste; ob sie das ist, kann nur ein Desk mit Orderbuchdaten
  beantworten.
- **Kurze Historie.** Gut neun Monate Test, Training ab Oktober 2025. Saisonalität lernt das
  Modell nicht, die Schwelle stützt sich auf 28 Tage und springt von Monat zu Monat.
- **Wenige Tage tragen viel.** Siehe Spike-Tabelle. Ein t um 2 auf neun Monaten mit dicken
  Rändern ist dünn. Ein einzelnes Modell schwankt schon mit dem Zufallsstartwert stark; das Mittel
  aus fünf schwankt weniger, aber nicht gar nicht (Robustheitstabelle).
- **Wetter-Frische wechselt Mitte Juni 2026.** Siehe „Daten".
- **Revisionen.** Day-Ahead-Preise und ID-AEP werden nicht revidiert. Die installierte Leistung
  ist der heutige Datenstand des Monats zwei Monate vor Lieferung, nicht die damals
  veröffentlichte Zahl. Bei einem Bestand von rund 100 GW Solar und 65 GW Wind sind die
  Nachmeldungen für einen Monat klein, null sind sie nicht.
- **Feiertage.** Nur bundesweite; regionale wie Fronleichnam fehlen.
- **Keine Marktwirkung.** Die eigene Order ändert weder den Day-Ahead-Preis noch den ID-AEP.

## Wie geprüft wird

- `tests/test_lookahead.py` baut die Features für einen Tag, verändert dann alles, was zur
  Entscheidung noch nicht bekannt war, und verlangt identische Features: Day-Ahead-Preise ab
  dem Liefertag, ID-AEP ab D-2, Ist-Last, Lastprognosen späterer Tage, installierte Leistung
  noch nicht nutzbarer Monate, später veröffentlichtes Wetter. Das läuft für einen normalen
  Tag, für den Umstellungstag mit 100 Viertelstunden und für eine frühe Live-Entscheidung um
  10:40. Kontrolltests zeigen, dass der Test Änderungen überhaupt sieht.
- `tests/test_pipeline.py`: In einer synthetischen Welt mit eingebautem Signal findet die
  Pipeline es, in reinem Rauschen findet sie nichts. Kein Training auf Labels, die zur
  Entscheidung unbekannt waren. Live liefert für denselben Tag dieselben Positionen wie der
  Backtest. Ein zu spät fertiges Signal wird nicht gezählt.
- `python -m dps checks` prüft die Zeitstempel der Wetterdaten gegen die Daten selbst
  (Tabelle im Ergebnisteil). Das kann kein Unit-Test.
- `reports/backtest.json` hält fest, woraus gerechnet wurde: Code-Commit, Revision des
  Wetter-Datasets und Stand des lokalen Caches.

## Lokal

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m dps demo                # ganze Pipeline auf synthetischen Daten, ohne Keys
python -m dps demo --noise --out demo-noise   # Welt ohne Signal: Modell sollte nicht handeln
python -m pytest                  # Tests, u. a. der Lookahead-Test

python -m dps fetch --full        # Preise, Last, ID-AEP seit 2025-10-01 nach data/ (geht ohne Keys)
python -m dps run                 # Teil 1, Teil 2, Report, README-Abschnitt
python -m dps run --robustness    # dazu alle Varianten und die Datenprüfung (~15 min)
python -m dps signal --day 2026-10-10 --force   # Signal von Hand; nach 11:50 als spät markiert
```

`DPS_HF_REVISION=<commit>` liest das Wetter-Dataset in genau der Revision, die in
`reports/backtest.json` steht.

Die Demo-Zahlen sind erfunden. Die synthetische Welt hat ein absichtlich eingebautes Signal
(der Markt preist nur mit ICON-EU), damit man sieht, dass die Pipeline es findet. In der
`--noise`-Welt soll sie nichts finden, und genau das prüft ein Test.

## Auf GitHub betreiben

1. Repository-Secrets: `ENTSOE_API_KEY`, `NTP_CLIENT_ID`, `NTP_CLIENT_SECRET`. Ohne sie läuft alles
   über Energy-Charts und den CSV-Download von netztransparenz.de; für den Dauerbetrieb sind die
   offiziellen APIs aber robuster (`cp .env.example .env` für lokal).
2. Settings → Actions → General → Workflow permissions: „Read and write".
3. `Backtest` einmal von Hand starten (füllt den Daten-Cache und den Ergebnis-Abschnitt).
4. `Live` läuft danach täglich von selbst: Signal-Slots alle zehn Minuten im Fenster, eine
   Abrechnung am Nachmittag.

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
  robustness.py alle getesteten Varianten auf demselben Walk-forward
  checks.py     Prüfung der Wetter-Zeitstempel gegen die Daten
  metrics.py    Kennzahlen, HAC-t
  report.py     Chart, REPORT.md, README-Abschnitte
  live.py       Signal und Abrechnung
  synthetic.py  synthetische Welt für Demo und Tests
```

## Lizenz

Code: MIT. Daten: ENTSO-E Transparency Platform, netztransparenz.de (die vier deutschen ÜNB),
Open-Meteo/DWD/ECMWF und Energy-Charts über das de-power-forecast-Dataset; bitte deren
Nutzungsbedingungen beachten. Kein Anlagerat.
