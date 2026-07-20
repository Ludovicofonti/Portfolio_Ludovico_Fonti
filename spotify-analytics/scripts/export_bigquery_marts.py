import argparse
import csv
import json
from pathlib import Path

from google.cloud import bigquery

try:
    from scripts.bigquery_config import BigQueryConfig
except ModuleNotFoundError:  # Direct execution: python scripts/export_bigquery_marts.py
    from bigquery_config import BigQueryConfig

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_DIR / "evidence" / "sources" / "spotify_public"
ALLOW_EMPTY = {"mart_chart_entries_exits"}


def parse_args():
    parser = argparse.ArgumentParser(description="Export bounded BigQuery marts for Evidence.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--history-days", type=int, default=365)
    return parser.parse_args()


def query_for_table(config, table, history_days):
    table_id = f"`{config.project}.{config.marts_dataset}.{table.table_id}`"
    fields = {field.name for field in table.schema}
    predicate = ""
    if "chart_date" in fields:
        predicate = f" where chart_date >= date_sub(current_date(), interval {history_days} day)"
    return f"select * from {table_id}{predicate}"


def export_marts(client, config, output, history_days=365):
    if history_days < 1 or history_days > 3650:
        raise ValueError("history_days must be between 1 and 3650")
    output.mkdir(parents=True, exist_ok=True)
    exported = {}
    tables = sorted(
        (
            table
            for table in client.list_tables(f"{config.project}.{config.marts_dataset}")
            if table.table_id.startswith(("mart_", "fct_"))
        ),
        key=lambda table: table.table_id,
    )
    if not tables:
        raise RuntimeError(f"No dbt marts found in {config.project}.{config.marts_dataset}")

    for table_item in tables:
        table = client.get_table(table_item.reference)
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=config.maximum_bytes_billed)
        result = client.query(
            query_for_table(config, table, history_days),
            location=config.location,
            job_config=job_config,
        ).result()
        rows = list(result)
        if not rows and table.table_id not in ALLOW_EMPTY:
            raise ValueError(f"Refusing to publish empty dataset: {table.table_id}")

        target = output / f"{table.table_id}.csv"
        temporary = target.with_suffix(".csv.tmp")
        field_names = [field.name for field in result.schema]
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(field_names)
            writer.writerows([row.get(field) for field in field_names] for row in rows)
        temporary.replace(target)
        exported[table.table_id] = len(rows)
    return exported


def main():
    args = parse_args()
    config = BigQueryConfig.from_env()
    client = bigquery.Client(project=config.project, location=config.location)
    print(json.dumps(export_marts(client, config, args.output, args.history_days), indent=2))


if __name__ == "__main__":
    main()
