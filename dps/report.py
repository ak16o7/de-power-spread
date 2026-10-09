"""Turn reports/backtest.json + explain.json into a chart, REPORT.md and the README section."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd

from . import config, explain

LOG = logging.getLogger(__name__)

LABEL = {"model": "Modell", "always_long": "Immer long", "always_short": "Immer short",
         "slot_sign_28d": "Vorzeichen je Viertelstunde (28 T)", "last_known_sign": "Letztes bekanntes Vorzeichen"}
ORDER = ["model", "always_long", "always_short", "slot_sign_28d", "last_known_sign"]
# reference categorical palette (light), fixed order: model first
COLOR = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
POS, NEG = "#2a78d6", "#e34948"   # diverging pair for monthly PnL sign


def _fmt(x, nd=0, signed=False):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "–"
    s = f"{x:+,.{nd}f}" if signed else f"{x:,.{nd}f}"
    # German: thousands with a narrow space, decimal comma
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", " ")


def chart(results: pd.DataFrame, out: Path, title_note: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = results.copy()
    res["day"] = pd.to_datetime(res["day"].astype(str))
    days = pd.date_range(res["day"].min(), res["day"].max(), freq="D")
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(9, 6.4), height_ratios=[2.2, 1], facecolor=SURFACE,
                                 constrained_layout=True)
    for a in (ax, bx):
        a.set_facecolor(SURFACE)
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            a.spines[side].set_color(GRID)
        a.tick_params(colors=INK2, labelsize=8.5)
        a.grid(axis="y", color=GRID, linewidth=0.8)
        a.set_axisbelow(True)
    for s in ORDER:
        g = res[res["strategy"] == s]
        if g.empty:
            continue
        cum = g.groupby("day")["net"].sum().reindex(days, fill_value=0).cumsum() / 1000
        ax.plot(cum.index, cum.to_numpy(), color=COLOR[s], linewidth=2.0, label=LABEL[s],
                zorder=3 if s == "model" else 2)
        if s == "model":
            ax.annotate(f"{LABEL[s]}  {_fmt(cum.iloc[-1], 1, signed=True)} k€", (cum.index[-1], cum.iloc[-1]),
                        xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=INK)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_ylabel("Kumulierter Netto-PnL, Tsd. €", color=INK2, fontsize=9)
    ax.set_title(f"Day-Ahead → ID-AEP: Modell gegen Baselines{title_note}", loc="left", color=INK, fontsize=11)
    leg = ax.legend(loc="best", frameon=False, fontsize=8.5)
    for t in leg.get_texts():
        t.set_color(INK)
    m = res[res["strategy"] == "model"]
    monthly = m.groupby(m["day"].dt.to_period("M"))["net"].sum() / 1000
    x = range(len(monthly))
    bx.bar(x, monthly.to_numpy(), color=[POS if v >= 0 else NEG for v in monthly], width=0.7,
           edgecolor=SURFACE, linewidth=2)
    bx.set_xticks(list(x), [p.strftime("%m/%y") for p in monthly.index])
    bx.axhline(0, color=INK2, linewidth=0.8)
    bx.set_ylabel("Modell je Monat, Tsd. €", color=INK2, fontsize=9)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def verdict(bt: dict) -> list[str]:
    """The pre-stated pass/fail check and the numbers that decide whether it matters."""
    m = bt["strategies"]["model"]
    vs = bt["model_vs"]
    won = [f"{LABEL[b]} (t {_fmt(v['t_hac'], 2)})" for b, v in vs.items() if (v.get("t_hac") or 0) > 2]
    lost = [f"{LABEL[b]} (t {_fmt(v['t_hac'], 2)})" for b, v in vs.items() if not (v.get("t_hac") or 0) > 2]
    passed = bt.get("verdict", {}).get("passed", not lost)
    L = ["**Urteil nach dem vorab festgelegten Kriterium** (das Modell zählt nur, wenn es jede Baseline "
         "im Tages-PnL mit t > 2 schlägt): " + ("**erfüllt**." if passed else "**nicht erfüllt**.")]
    if won:
        L[-1] += f" Geschlagen: {', '.join(won)}."
    if lost:
        L[-1] += f" Nicht geschlagen: {', '.join(lost)}."
    be = (bt.get("break_even_slippage_eur_mwh") or {}).get("model")
    ls = (bt.get("long_short") or {}).get("model")
    sp = (bt.get("spike_sensitivity") or {}).get("model", {})
    wb = next((v for k, v in sp.items() if k.startswith("without_best_")), None)
    nbest = next((k.split("_")[2] for k in sp if k.startswith("without_best_")), "10")
    bullets = []
    if be is not None:
        bullets.append(f"- **Gewinnschwelle der Ausführung:** Das Modell verdient {_fmt(m['eur_per_mwh'], 2, True)} €/MWh "
                       f"netto bei {_fmt(bt['assumptions']['slippage_eur_mwh'], 1)} €/MWh Slippage. Kostet der Ausstieg "
                       f"mehr als {_fmt(be, 1)} €/MWh gegenüber dem ID-AEP, ist der Gewinn weg. Ob echte Ausführung das "
                       "schafft, kann dieser Backtest nicht zeigen: Der ID-AEP ist ein Index, kein Preis, zu dem man "
                       "handeln kann.")
    if ls:
        bullets.append(f"- **Long gegen Short:** long {_fmt(ls['long_net_eur'], 0, True)} € auf {_fmt(ls['long_mwh'])} MWh, "
                       f"short {_fmt(ls['short_net_eur'], 0, True)} € auf {_fmt(ls['short_mwh'])} MWh.")
    if wb is not None:
        bullets.append(f"- **Spitzen:** ohne die {nbest} besten Tage bleiben {_fmt(wb, 0, True)} € "
                       f"von {_fmt(m['net_eur'], 0, True)} €.")
    return L + ([""] + bullets if bullets else [])


def markdown(bt: dict, ex: dict | None, image: str = "reports/pnl.png", rob: dict | None = None,
             chk: dict | None = None) -> str:
    from . import checks, robustness
    a = bt["assumptions"]
    tp = bt["test_period"]
    L = [f"Testzeitraum {tp['from']} bis {tp['to']} ({tp['days']} Tage, walk-forward, jeder Monat out-of-sample). "
         f"Position {a['size_mw']:.0f} MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg bewertet "
         f"zum ID-AEP (Benchmark, kein handelbarer Preis). "
         f"Kosten: {_fmt(a['fee_eur_mwh_per_leg'], 2)} €/MWh je Seite, {_fmt(a['slippage_eur_mwh'], 1)} €/MWh Slippage "
         f"beim Ausstieg, {_fmt(a['missing_exit_penalty_eur_mwh'], 0)} €/MWh Strafe, wenn der ID-AEP fehlt.\n",
         *verdict(bt), "",
         f"![PnL]({image})\n",
         "| Strategie | Netto € | €/MWh | MWh | Treffer | Sharpe (ann.) | t (HAC) | Max. Drawdown € | Schlechtester Tag € | ID-AEP fehlte |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in ORDER:
        v = bt["strategies"].get(s)
        if not v:
            continue
        name = f"**{LABEL[s]}**" if s == "model" else LABEL[s]
        L.append(f"| {name} | {_fmt(v['net_eur'], 0, True)} | {_fmt(v['eur_per_mwh'], 2, True)} | {_fmt(v['mwh'])} | "
                 f"{_fmt(None if v['hit_rate'] is None else v['hit_rate'] * 100, 0)} % | {_fmt(v['sharpe_daily_ann'], 2)} | "
                 f"{_fmt(v['t_daily_hac'], 2)} | {_fmt(v['max_drawdown_eur'])} | {_fmt(v['worst_day_eur'])} | {v['missing_exit_qh']} |")
    mc = bt.get("model_vs_capped", {})
    cap = mc.get("cap_eur_mwh")
    L += ["", "**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):", "",
          "| gegen | Ø €/Tag | t (HAC) |" + (f" Ø €/Tag, Spread gekappt ±{cap:.0f} | t |" if mc else ""),
          "|---|---:|---:|" + ("---:|---:|" if mc else "")]
    for b, v in bt["model_vs"].items():
        extra = f" {_fmt(mc[b]['mean_eur_per_day'], 1, True)} | {_fmt(mc[b]['t_hac'], 2)} |" if b in mc else ""
        L.append(f"| {LABEL[b]} | {_fmt(v['mean_eur_per_day'], 1, True)} | {_fmt(v['t_hac'], 2)} |" + extra)
    sp = bt.get("spike_sensitivity")
    if sp:
        first = next(iter(sp.values()))
        caps = [k for k in first if k != "top10_qh_net_eur" and not k.startswith("without_best_")]
        wb = next((k for k in first if k.startswith("without_best_")), None)
        wb_head = f" ohne die {wb.split('_')[2]} besten Tage |" if wb else ""
        L += ["", "**Spike-Abhängigkeit**: Netto-PnL in €, wenn der Spread auf ±X €/MWh begrenzt wäre (t in Klammern). "
              "Was unter der Kappung verschwindet, kam aus wenigen Preisspitzen.", "",
              "| Strategie | ungekappt | davon 10 größte Viertelstunden |" + wb_head + " "
              + " | ".join(f"±{c}" for c in caps) + " |",
              "|---|---:|---:|" + ("---:|" if wb else "") + "---:|" * len(caps)]
        for s in ORDER:
            row = sp.get(s)
            if not row:
                continue
            cells = " | ".join(f"{_fmt(row[c]['net_eur'], 0, True)} ({_fmt(row[c]['t_daily_hac'], 1)})" for c in caps)
            wb_cell = f" {_fmt(row[wb], 0, True)} |" if wb else ""
            L.append(f"| {LABEL[s]} | {_fmt(bt['strategies'][s]['net_eur'], 0, True)} | "
                     f"{_fmt(row['top10_qh_net_eur'], 0, True)} |{wb_cell} {cells} |")
    slips = list(next(iter(bt["slippage_sensitivity"].values())).keys())
    be = bt.get("break_even_slippage_eur_mwh") or {}
    L += ["", "**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh gegenüber dem ID-AEP) von", "",
          "| Strategie | " + " | ".join(_fmt(float(k), 1) for k in slips) + " |" + (" Gewinnschwelle €/MWh |" if be else ""),
          "|---|" + "---:|" * len(slips) + ("---:|" if be else "")]
    for s in ORDER:
        row = bt["slippage_sensitivity"].get(s)
        if row:
            b = be.get(s)
            L.append(f"| {LABEL[s]} | " + " | ".join(_fmt(row[k], 0, True) for k in slips) + " |"
                     + (f" {_fmt(b, 1) if b is not None and b > 0 else '– (verliert schon ohne Slippage)'} |" if be else ""))
    ls = bt.get("long_short")
    if ls:
        L += ["", "**Long- und Short-Seite** (netto €, in Klammern MWh)", "",
              "| Strategie | long | short |", "|---|---:|---:|"]
        for s in ORDER:
            r = ls.get(s)
            if r:
                L.append(f"| {LABEL[s]} | {_fmt(r['long_net_eur'], 0, True)} ({_fmt(r['long_mwh'])}) | "
                         f"{_fmt(r['short_net_eur'], 0, True)} ({_fmt(r['short_mwh'])}) |")
    L += ["", "**Modell je Monat**", "", "| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |", "|---|---:|---:|---:|---:|"]
    th = {m["month"]: m for m in bt["months"]}
    for mon, v in bt["model_monthly"].items():
        mm = th.get(mon, {})
        L.append(f"| {mon} | {_fmt(v['net_eur'], 0, True)} | {_fmt(v['mwh'])} | {_fmt(mm.get('threshold'), 0)} | "
                 f"{mm.get('train_days', '–')} |")
    L += ["", "### Robustheit: alle getesteten Varianten", "",
          "Gleicher Walk-forward, gleiche Kosten. Vor dem ersten Backtest auf echten Daten stand nur die erste "
          "Version fest (erste Zeile). Danach wurde das Hauptmodell zweimal geändert: Die Lastprognose flog raus, "
          "weil ihr Veröffentlichungszeitpunkt nicht belegbar ist, und die Vorhersage ist jetzt das Mittel aus fünf "
          "Startwerten, weil ein einzelnes Modell stark am Startwert hing. Beides hat den PnL im Test erhöht. Alle "
          "anderen Varianten kamen danach, und alle stehen hier, auch die schlechten. Die beste Zeile zur Strategie "
          "zu erklären wäre Anpassung an den Testzeitraum: Die Tabelle zeigt, wie unsicher die Hauptzahl ist.", "",
          robustness.markdown(rob)]
    L += ["### Was ein Prognosefehler kostet (ex post)", "", explain.markdown(ex) if ex else "_fehlt_"]
    L += ["### Stimmen die Zeitstempel der Wetterdaten?", "",
          "Der Lookahead-Test prüft, dass der Code jedes `available_at` respektiert. Ob die Stempel selbst stimmen, "
          "lässt sich prüfen, wo das Dataset beide Arten von Prognosen hat: Archivwerte („Tag 1“ = mindestens "
          "24 h alt, „Tag 2“ = 48 h) und vollständige Läufe (nachgeladen oder live mitgeschnitten).", "",
          checks.markdown(chk)]
    prov = bt.get("provenance") or {}
    if prov:
        rev = ", ".join(prov.get("hf_revisions") or []) or "–"
        cc = str(prov.get("code_commit") or "–")
        cc = cc[:7] + ("+dirty" if cc.endswith("+dirty") else "")
        L += ["", f"<sub>Gerechnet am {bt['generated_at'][:16].replace('T', ' ')} UTC, Code {cc}, "
                  f"Wetterdaten {prov.get('hf_dataset')} @ {rev[:12] if rev != '–' else rev}.</sub>"]
    return "\n".join(L) + "\n"


def update_section(path: Path, name: str, body: str) -> bool:
    """Replace the text between <!-- name:START --> and <!-- name:END --> in a file."""
    if not path.is_file():
        return False
    text = path.read_text()
    pat = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        return False
    new = pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)
    if new != text:
        path.write_text(new)
    return True


def run(readme: bool = True, title_note: str = "") -> str:
    rep = Path(config.REPORTS_DIR)
    bt = json.loads((rep / "backtest.json").read_text())
    ex_path = rep / "explain.json"
    ex = json.loads(ex_path.read_text()) if ex_path.is_file() else None
    rob_path = rep / "robustness.json"
    rob = json.loads(rob_path.read_text()) if rob_path.is_file() else None
    chk_path = rep / "checks.json"
    chk = json.loads(chk_path.read_text()) if chk_path.is_file() else None
    chart(pd.read_parquet(rep / "backtest.parquet"), rep / "pnl.png", title_note)
    (rep / "REPORT.md").write_text("# Backtest-Report\n\n" + markdown(bt, ex, image="pnl.png", rob=rob, chk=chk))
    body = markdown(bt, ex, image=f"{rep.as_posix()}/pnl.png", rob=rob, chk=chk)
    if readme:
        update_section(Path(config.README), "RESULTS", body)
    LOG.info("report written to %s", rep / "REPORT.md")
    return body
