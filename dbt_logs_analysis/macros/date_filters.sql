{#
  日付フィルタリング用のマクロ集
  
  使用例:
    WHERE {{ recent_days('created_at', 7) }}
    WHERE {{ date_between('order_date', '2025-01-01', '2025-01-31') }}
    WHERE {{ current_month('timestamp') }}
#}

{% macro recent_days(timestamp_column, days=30) %}
  {#
    過去N日間のデータをフィルタ
    
    引数:
      timestamp_column: タイムスタンプ型のカラム名
      days: 過去何日間か（デフォルト: 30日）
    
    戻り値:
      WHERE句で使用できるフィルタ条件
    
    例:
      WHERE {{ recent_days('request_timestamp', 7) }}
      → WHERE request_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  #}
  {{ timestamp_column }} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{ days }} DAY)
{% endmacro %}


{% macro date_between(timestamp_column, start_date, end_date) %}
  {#
    特定期間のデータをフィルタ
    
    引数:
      timestamp_column: タイムスタンプ型のカラム名
      start_date: 開始日（YYYY-MM-DD形式の文字列）
      end_date: 終了日（YYYY-MM-DD形式の文字列）
    
    戻り値:
      WHERE句で使用できるフィルタ条件
    
    例:
      WHERE {{ date_between('order_date', '2025-01-01', '2025-01-31') }}
      → WHERE order_date BETWEEN TIMESTAMP('2025-01-01') AND TIMESTAMP('2025-01-31')
  #}
  {{ timestamp_column }} BETWEEN TIMESTAMP('{{ start_date }}') AND TIMESTAMP('{{ end_date }}')
{% endmacro %}


{% macro current_month(timestamp_column) %}
  {#
    当月のデータをフィルタ
    
    引数:
      timestamp_column: タイムスタンプ型のカラム名
    
    戻り値:
      WHERE句で使用できるフィルタ条件（年と月が現在と一致）
    
    例:
      WHERE {{ current_month('created_at') }}
      → WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP())
            AND EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM CURRENT_TIMESTAMP())
  #}
  EXTRACT(YEAR FROM {{ timestamp_column }}) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP())
  AND EXTRACT(MONTH FROM {{ timestamp_column }}) = EXTRACT(MONTH FROM CURRENT_TIMESTAMP())
{% endmacro %}
