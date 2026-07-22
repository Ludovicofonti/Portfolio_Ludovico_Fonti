{% macro is_integer(expression) -%}
    regexp_contains(cast({{ expression }} as string), r'^-?[0-9]+$')
{%- endmacro %}

{% macro date_diff_days(end_date, start_date) -%}
    date_diff({{ end_date }}, {{ start_date }}, day)
{%- endmacro %}

{% macro month_start(expression) -%}
    date_trunc({{ expression }}, month)
{%- endmacro %}

{% macro aggregate_boolean_or(expression) -%}
    logical_or({{ expression }})
{%- endmacro %}

{% macro raw_partition_filter(column_name) -%}
    {{ column_name }} >= date_sub(current_date(), interval 365 day)
{%- endmacro %}

{% macro parse_partial_date(expression) -%}
    case
        when {{ expression }} is null then null
        when length({{ expression }}) = 4 then cast({{ expression }} || '-01-01' as date)
        when length({{ expression }}) = 7 then cast({{ expression }} || '-01' as date)
        else cast({{ expression }} as date)
    end
{%- endmacro %}
