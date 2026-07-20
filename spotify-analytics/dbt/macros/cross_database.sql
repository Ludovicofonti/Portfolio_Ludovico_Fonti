{% macro is_integer(expression) -%}
    {%- if target.type == 'bigquery' -%}
        regexp_contains(cast({{ expression }} as string), r'^-?[0-9]+$')
    {%- else -%}
        {{ expression }} ~ '^-?[0-9]+$'
    {%- endif -%}
{%- endmacro %}

{% macro date_diff_days(end_date, start_date) -%}
    {%- if target.type == 'bigquery' -%}
        date_diff({{ end_date }}, {{ start_date }}, day)
    {%- else -%}
        {{ end_date }} - {{ start_date }}
    {%- endif -%}
{%- endmacro %}

{% macro month_start(expression) -%}
    {%- if target.type == 'bigquery' -%}
        date_trunc({{ expression }}, month)
    {%- else -%}
        date_trunc('month', {{ expression }})
    {%- endif -%}
{%- endmacro %}

{% macro aggregate_boolean_or(expression) -%}
    {%- if target.type == 'bigquery' -%}
        logical_or({{ expression }})
    {%- else -%}
        bool_or({{ expression }})
    {%- endif -%}
{%- endmacro %}

{% macro raw_partition_filter(column_name) -%}
    {%- if target.type == 'bigquery' -%}
        {{ column_name }} >= date_sub(current_date(), interval 365 day)
    {%- else -%}
        1 = 1
    {%- endif -%}
{%- endmacro %}

{% macro parse_partial_date(expression) -%}
    case
        when {{ expression }} is null then null
        when length({{ expression }}) = 4 then cast({{ expression }} || '-01-01' as date)
        when length({{ expression }}) = 7 then cast({{ expression }} || '-01' as date)
        else cast({{ expression }} as date)
    end
{%- endmacro %}
