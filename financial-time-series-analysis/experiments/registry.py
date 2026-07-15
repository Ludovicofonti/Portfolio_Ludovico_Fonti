"""Experiment tracking locale in DuckDB."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb

from .metadata import canonical_json

SCHEMA = """
create table if not exists experiment_runs (
  experiment_id varchar, run_id varchar primary key, run_timestamp timestamptz, git_commit varchar,
  data_start timestamptz, data_end timestamptz, data_version varchar, asset varchar, frequency varchar,
  target varchar, horizon integer, model_name varchar, hyperparameters_json varchar, feature_set_json varchar,
  cost_scenario varchar, random_seed bigint, primary_metric varchar, primary_metric_value double,
  baseline_metric_value double, net_sharpe double, max_drawdown double, status varchar, artifact_path varchar
)
"""


class ExperimentRegistry:
    def __init__(self, path: str | Path = "data/experiments.duckdb"):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self.path)) as connection: connection.execute(SCHEMA)

    def register(self, record: dict) -> str:
        run = dict(record); run.setdefault("run_id", uuid4().hex); run.setdefault("experiment_id", run["run_id"])
        run.setdefault("run_timestamp", datetime.now(timezone.utc)); run.setdefault("status", "completed")
        run["hyperparameters_json"] = canonical_json(run.pop("hyperparameters", {}))
        run["feature_set_json"] = canonical_json(run.pop("feature_set", []))
        with duckdb.connect(str(self.path)) as connection:
            columns = [row[1] for row in connection.execute("pragma table_info('experiment_runs')").fetchall()]
        values = [run.get(column) for column in columns]
        with duckdb.connect(str(self.path)) as connection:
            connection.execute(f"insert into experiment_runs ({','.join(columns)}) values ({','.join('?' for _ in columns)})", values)
        return str(run["run_id"])

    def latest(self, limit: int = 20):
        with duckdb.connect(str(self.path), read_only=True) as connection:
            return connection.execute("select * from experiment_runs order by run_timestamp desc limit ?", [limit]).df()

    def update_status(self, run_id: str, status: str, **fields) -> None:
        """Aggiorna atomicamente lo stato e un sottoinsieme di metriche della run."""
        with duckdb.connect(str(self.path)) as connection:
            columns = {row[1] for row in connection.execute("pragma table_info('experiment_runs')").fetchall()}
            updates = {key: value for key, value in fields.items() if key in columns and key != "run_id"}
            updates["status"] = status
            assignments = ",".join(f"{key}=?" for key in updates)
            connection.execute(
                f"update experiment_runs set {assignments} where run_id=?",
                [*updates.values(), run_id],
            )
