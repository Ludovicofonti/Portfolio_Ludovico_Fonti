from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_all_partitioned_dbt_models_require_partition_filters():
    project_config = (PROJECT_DIR / "dbt" / "dbt_project.yml").read_text(
        encoding="utf-8"
    )
    assert project_config.count("+partition_by:") == project_config.count(
        "+require_partition_filter: true"
    )


def test_incremental_fact_filters_the_bigquery_destination_partition():
    fact_model = (
        PROJECT_DIR / "dbt" / "models" / "marts" / "fct_track_chart_daily.sql"
    ).read_text(encoding="utf-8")
    assert "incremental_predicates" in fact_model
    assert "DBT_INTERNAL_DEST.chart_date" in fact_model


def test_partial_dates_are_safely_cast_for_invalid_spotify_values():
    macros = (PROJECT_DIR / "dbt" / "macros" / "cross_database.sql").read_text(
        encoding="utf-8"
    )
    partial_date_macro = macros.split("{% macro parse_partial_date", maxsplit=1)[1]
    partial_date_macro = partial_date_macro.split("{% endmacro %}", maxsplit=1)[0]

    assert partial_date_macro.count("safe_cast(") == 3
    assert "cast({{ expression }}" not in partial_date_macro.replace("safe_cast(", "")
