# Backtest-Report

Testzeitraum 2026-01-01 bis 2026-10-06 (279 Tage, walk-forward, jeder Monat out-of-sample). Position 10 MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg zum ID-AEP. Kosten: 0.25 €/MWh je Seite, 1.0 €/MWh Slippage beim Ausstieg, 10.0 €/MWh Strafe, wenn der ID-AEP fehlt.

![PnL](pnl.png)

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

