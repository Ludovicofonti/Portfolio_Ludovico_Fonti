"""CLI unica della piattaforma financial time series."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipelines.platform import ResearchOptions, platform_status, regenerate_report, run_research

PROJECT_ROOT = Path(__file__).resolve().parent


@contextmanager
def pipeline_lock():
    lock_path = PROJECT_ROOT / "data" / ".financial_ts.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Un'altra pipeline è già attiva: {lock_path}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        lock_path.unlink(missing_ok=True)


def backup_database() -> Path:
    source = PROJECT_ROOT / "data" / "finance.duckdb"
    if not source.exists():
        raise FileNotFoundError(source)
    destination_dir = PROJECT_ROOT / "data" / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"finance_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.duckdb"
    shutil.copy2(source, destination)
    return destination


def run_dbt() -> None:
    subprocess.run(
        [
            "dbt",
            "build",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--vars",
            json.dumps({"enable_crypto_models": True}),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def run_ingestion(args) -> None:
    from pipelines.run_ingestion import main as ingest

    start = datetime.fromisoformat(args.start).astimezone(timezone.utc) if args.start else None
    ingest(
        crypto_only=True,
        symbols=[args.symbol],
        intervals=args.intervals.split(","),
        start_time=start,
        orderbook=not args.no_orderbook,
        onchain=not args.no_onchain,
    )


def research_options(args) -> ResearchOptions:
    horizon = args.horizon
    if horizon is None:
        horizon = 24 if args.task in {"volatility", "tail"} else 1
    return ResearchOptions(
        symbol=args.symbol,
        interval=args.interval,
        horizon=horizon,
        model=args.model,
        task=args.task,
    )


def add_common_research_arguments(parser):
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--horizon", type=int, choices=(1, 4, 24))
    parser.add_argument(
        "--task", choices=("return", "direction", "volatility", "tail"), default="return"
    )
    parser.add_argument(
        "--model",
        choices=("auto", "ridge_return", "arima_return", "sarima_return",
                 "ridge_direction", "garch_student_t_1_1", "ridge_tail"),
        default="auto",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="financial-ts")
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Ingestione crypto incrementale")
    ingest.add_argument("--symbol", default="BTCUSDT")
    ingest.add_argument("--intervals", default="1h,4h,1d")
    ingest.add_argument("--start")
    ingest.add_argument("--no-orderbook", action="store_true")
    ingest.add_argument("--no-onchain", action="store_true")

    commands.add_parser("transform", help="Esegue dbt build")
    evaluate = commands.add_parser("evaluate", help="Walk-forward, costi, rischio e report")
    add_common_research_arguments(evaluate)

    report = commands.add_parser("report", help="Rigenera il report da una run tracciata")
    report.add_argument("--run-id")

    commands.add_parser("backup", help="Crea una copia consistente del DuckDB a pipeline ferma")

    run = commands.add_parser("run", help="Pipeline completa end-to-end")
    add_common_research_arguments(run)
    run.add_argument("--intervals", default="1h,4h,1d")
    run.add_argument("--start")
    run.add_argument("--no-orderbook", action="store_true")
    run.add_argument("--no-onchain", action="store_true")
    run.add_argument("--skip-ingest", action="store_true")
    run.add_argument("--skip-dbt", action="store_true")

    commands.add_parser("status", help="Stato dati, mart e report")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "status":
            print(json.dumps(platform_status(), indent=2, default=str))
            return 0
        with pipeline_lock():
            if args.command == "ingest":
                run_ingestion(args)
            elif args.command == "transform":
                run_dbt()
            elif args.command == "evaluate":
                print(json.dumps(run_research(research_options(args)), indent=2, default=str))
            elif args.command == "report":
                print(json.dumps(regenerate_report(args.run_id), indent=2, default=str))
            elif args.command == "backup":
                print(backup_database())
            elif args.command == "run":
                if not args.skip_ingest:
                    run_ingestion(args)
                if not args.skip_dbt:
                    run_dbt()
                print(json.dumps(run_research(research_options(args)), indent=2, default=str))
        return 0
    except Exception as exc:
        logging.exception("Pipeline fallita")
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
