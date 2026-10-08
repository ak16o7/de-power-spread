"""python -m dps <command>

  fetch      prices, load and ID-AEP into data/ (ENTSOE_API_KEY, NTP_CLIENT_ID/SECRET)
  explain    part 1: spread vs. TSO day-ahead forecast errors -> reports/explain.json
  backtest   part 2: walk-forward strategy vs. baselines -> reports/backtest.*
  report     chart, reports/REPORT.md and the RESULTS section of README.md
  run        explain + backtest + report
  signal     live: tomorrow's positions -> signals/YYYY-MM-DD.csv (10:45-11:50 local)
  settle     live: book signals whose ID-AEP is out -> live/ledger.csv, README
  demo       the whole pipeline on synthetic data, no keys needed (numbers are made up)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from . import config, util

LOG = logging.getLogger("dps")


def _date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def demo(out: Path, noise: bool) -> int:
    from . import backtest, explain, hf, report, synthetic
    out.mkdir(parents=True, exist_ok=True)
    start, end = config.START, config.START + timedelta(days=330)
    config.DATA_DIR = str(out / "data")
    config.REPORTS_DIR = str(out / "reports")
    os.environ["DPS_HF_LOCAL"] = str(out / "hf")
    os.environ["DPS_NOW"] = f"{end + timedelta(days=3)}T12:00:00Z"
    hf.weather.cache_clear()
    hf.capacity.cache_clear()
    LOG.info("building a synthetic world (%s, alpha=%s) in %s", "noise" if noise else "planted signal", not noise, out)
    synthetic.make(out / "data", out / "hf", start, end, alpha=not noise, seed=1)
    explain.run(start, end)
    bt = backtest.run(start, end)
    report.run(readme=False, title_note=" – SYNTHETISCHE DATEN")
    print(json.dumps({s: {k: v[k] for k in ("net_eur", "eur_per_mwh", "t_daily_hac")}
                      for s, v in bt["strategies"].items()}, indent=1))
    print(f"\nSynthetic demo written to {out / 'reports'} -- every number there is made up.")
    return 0


def main(argv: list[str] | None = None) -> int:
    util.setup_logging()
    ap = argparse.ArgumentParser(prog="dps", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--full", action="store_true", help="refetch everything since START")
    f.add_argument("--recent-days", type=int, default=7)
    f.add_argument("--only", nargs="*", choices=["da", "load", "id_aep"])
    for name in ("explain", "backtest", "run"):
        p = sub.add_parser(name)
        p.add_argument("--start")
        p.add_argument("--end", help="exclusive delivery day")
    sub.add_parser("report")
    s = sub.add_parser("signal")
    s.add_argument("--day", help="delivery day, default tomorrow")
    s.add_argument("--force", action="store_true", help="ignore the time window (late signals are never counted)")
    sub.add_parser("settle")
    d = sub.add_parser("demo")
    d.add_argument("--out", default="demo")
    d.add_argument("--noise", action="store_true", help="a world without signal: nothing should earn")
    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        from . import fetch
        rep = fetch.run(full=a.full, recent_days=a.recent_days, **({"sources": tuple(a.only)} if a.only else {}))
        print(json.dumps(rep, indent=1))
        return 1 if all(v.startswith("ERROR") for v in rep.values()) else 0
    if a.cmd in ("explain", "run"):
        from . import explain
        explain.run(_date(a.start), _date(a.end))
    if a.cmd in ("backtest", "run"):
        from . import backtest
        backtest.run(_date(a.start), _date(a.end))
    if a.cmd in ("report", "run"):
        from . import report
        report.run()
    if a.cmd == "signal":
        from . import live
        print(json.dumps(live.signal(_date(a.day), force=a.force), indent=1))
    if a.cmd == "settle":
        from . import live
        print(json.dumps(live.settle(), indent=1))
    if a.cmd == "demo":
        return demo(Path(a.out), a.noise)
    return 0


if __name__ == "__main__":
    sys.exit(main())
