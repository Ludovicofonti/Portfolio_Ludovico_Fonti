import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run ingestion and dbt transformations in BigQuery."
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Run dbt from existing BigQuery raw tables without acquiring new data.",
    )
    return parser.parse_args()


def run(command, cwd=PROJECT_DIR, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main():
    args = parse_args()
    if not args.skip_ingest:
        run([sys.executable, "scripts/refresh_public_data.py"])

    dbt_env = os.environ.copy()
    dbt_env["DBT_PROFILES_DIR"] = str(PROJECT_DIR / "dbt")
    dbt_executable = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    run(
        [str(dbt_executable), "build", "--target", "bigquery"],
        cwd=PROJECT_DIR / "dbt",
        env=dbt_env,
    )


if __name__ == "__main__":
    main()
