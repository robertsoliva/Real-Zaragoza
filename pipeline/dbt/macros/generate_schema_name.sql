{# Routes bronze/silver/gold models to dev_bronze/dev_silver/dev_gold when the
   active target isn't prod. This is what makes `dbt run --target dev` (used by
   CI and local dev work) hit a separate copy of the warehouse instead of the
   real bronze/silver/gold datasets `target: prod` writes to -- deliberately
   fails toward dev-prefixed (safer) rather than toward prod on any unexpected
   target name. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set base_schema = custom_schema_name | trim if custom_schema_name is not none else target.schema -%}
    {%- if target.name == 'prod' -%}
        {{ base_schema }}
    {%- else -%}
        dev_{{ base_schema }}
    {%- endif -%}
{%- endmacro %}
