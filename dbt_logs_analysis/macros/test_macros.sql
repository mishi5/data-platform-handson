{#
  マクロのテスト用
  実行方法: dbt run-operation test_performance_stats
#}

{% macro test_performance_stats() %}
  {% set test_sql %}
    SELECT 
      {{ performance_stats('response_time', 3) }}
    FROM `data-platform-handson-1223.logs_database_staging.stg_access_logs`
    LIMIT 1
  {% endset %}
  
  {{ log("Generated SQL:", info=true) }}
  {{ log(test_sql, info=true) }}
  
  {% set result = run_query(test_sql) %}
  {{ log("Result:", info=true) }}
  {{ log(result, info=true) }}
{% endmacro %}


{% macro test_percentile() %}
  {% set test_sql %}
    SELECT 
      {{ percentile('response_time_sec', [50, 90, 95]) }}
    FROM `data-platform-handson-1223.logs_database_staging.stg_access_logs`
  {% endset %}
  
  {{ log("Generated SQL:", info=true) }}
  {{ log(test_sql, info=true) }}
  
  {% set result = run_query(test_sql) %}
  {{ log("Result:", info=true) }}
  {{ log(result, info=true) }}
{% endmacro %}
