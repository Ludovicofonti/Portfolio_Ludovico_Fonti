import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Run ingestion, dbt-BigQuery and Evidence export.")
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Build from existing raw snapshots without network access.",
    )
    return parser.parse_args()


def run(command, cwd=PROJECT_DIR, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main():
    args = parse_args()
    if not args.skip_extract:
        run([sys.executable, "scripts/refresh_public_data.py", "--extract-only"])
    run([sys.executable, "scripts/load_bigquery_raw.py"])

    dbt_env = os.environ.copy()
    dbt_env["DBT_PROFILES_DIR"] = str(PROJECT_DIR / "dbt")
    dbt_executable = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    run(
        [str(dbt_executable), "build", "--target", "bigquery"],
        cwd=PROJECT_DIR / "dbt",
        env=dbt_env,
    )
    run([sys.executable, "scripts/export_bigquery_marts.py"])


if __name__ == "__main__":
    main()
