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
    return s.replace(",", " ")


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
    leg = ax.legend(loc="upper left", frameon=False, fontsize=8.5)
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


def markdown(bt: dict, ex: dict | None, image: str = "reports/pnl.png") -> str:
    a = bt["assumptions"]
    tp = bt["test_period"]
    L = [f"Testzeitraum {tp['from']} bis {tp['to']} ({tp['days']} Tage, walk-forward, jeder Monat out-of-sample). "
         f"Position {a['size_mw']:.0f} MW je gehandelter Viertelstunde, Einstieg zum Day-Ahead-Preis, Ausstieg zum ID-AEP. "
         f"Kosten: {a['fee_eur_mwh_per_leg']} €/MWh je Seite, {a['slippage_eur_mwh']} €/MWh Slippage beim Ausstieg, "
         f"{a['missing_exit_penalty_eur_mwh']} €/MWh Strafe, wenn der ID-AEP fehlt.\n",
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
    L += ["", "**Modell minus Baseline**, Tages-PnL (t > 2: Vorsprung jenseits von Rauschen):", "",
          "| gegen | Ø €/Tag | t (HAC) |", "|---|---:|---:|"]
    for b, v in bt["model_vs"].items():
        L.append(f"| {LABEL[b]} | {_fmt(v['mean_eur_per_day'], 1, True)} | {_fmt(v['t_hac'], 2)} |")
    slips = list(next(iter(bt["slippage_sensitivity"].values())).keys())
    L += ["", "**Kostenempfindlichkeit**: Netto-PnL in € bei Slippage (€/MWh) von", "",
          "| Strategie | " + " | ".join(slips) + " |", "|---|" + "---:|" * len(slips)]
    for s in ORDER:
        row = bt["slippage_sensitivity"].get(s)
        if row:
            L.append(f"| {LABEL[s]} | " + " | ".join(_fmt(row[k], 0, True) for k in slips) + " |")
    L += ["", "**Modell je Monat**", "", "| Monat | Netto € | MWh | Schwelle €/MWh | Trainingstage |", "|---|---:|---:|---:|---:|"]
    th = {m["month"]: m for m in bt["months"]}
    for mon, v in bt["model_monthly"].items():
        mm = th.get(mon, {})
        L.append(f"| {mon} | {_fmt(v['net_eur'], 0, True)} | {_fmt(v['mwh'])} | {_fmt(mm.get('threshold'), 0)} | "
                 f"{mm.get('train_days', '–')} |")
    L += ["", "### Was ein Prognosefehler kostet (ex post)", "", explain.markdown(ex) if ex else "_fehlt_"]
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
    chart(pd.read_parquet(rep / "backtest.parquet"), rep / "pnl.png", title_note)
    (rep / "REPORT.md").write_text("# Backtest-Report\n\n" + markdown(bt, ex, image="pnl.png"))
    body = markdown(bt, ex, image=f"{rep.as_posix()}/pnl.png")
    if readme:
        update_section(Path(config.README), "RESULTS", body)
    LOG.info("report written to %s", rep / "REPORT.md")
    return body
