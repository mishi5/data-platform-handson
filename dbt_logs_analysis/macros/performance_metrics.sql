{#
  パフォーマンスメトリクス計算用マクロ集
  
  使用例:
    SELECT 
      {{ performance_stats('response_time', 3) }},
      {{ percentile('response_time', [50, 90, 95, 99]) }}
    FROM logs
#}

{% macro performance_stats(metric_column, decimals=3) %}
  {#
    パフォーマンスメトリクスの基本統計量を計算
    
    引数:
      metric_column: 数値型のメトリクスカラム名
      decimals: 小数点以下の桁数（デフォルト: 3）
    
    戻り値:
      4つのカラム定義（平均、最小、最大、標準偏差）
    
    生成されるカラム:
      - avg_{metric_column}: 平均値
      - min_{metric_column}: 最小値
      - max_{metric_column}: 最大値
      - stddev_{metric_column}: 標準偏差
    
    例:
      {{ performance_stats('response_time_sec', 3) }}
      → ROUND(AVG(response_time_sec), 3) as avg_response_time_sec,
        ROUND(MIN(response_time_sec), 3) as min_response_time_sec,
        ROUND(MAX(response_time_sec), 3) as max_response_time_sec,
        ROUND(STDDEV(response_time_sec), 3) as stddev_response_time_sec
  #}
  ROUND(AVG({{ metric_column }}), {{ decimals }}) as avg_{{ metric_column }},
  ROUND(MIN({{ metric_column }}), {{ decimals }}) as min_{{ metric_column }},
  ROUND(MAX({{ metric_column }}), {{ decimals }}) as max_{{ metric_column }},
  ROUND(STDDEV({{ metric_column }}), {{ decimals }}) as stddev_{{ metric_column }}
{% endmacro %}


{% macro percentile(metric_column, percentiles=[50, 90, 95, 99]) %}
  {#
    パーセンタイル（百分位数）を計算
    
    引数:
      metric_column: 数値型のメトリクスカラム名
      percentiles: パーセンタイルのリスト（デフォルト: [50, 90, 95, 99]）
    
    戻り値:
      指定されたパーセンタイルごとのカラム定義
    
    生成されるカラム:
      - p50_{metric_column}: 中央値（50パーセンタイル）
      - p90_{metric_column}: 90パーセンタイル
      - p95_{metric_column}: 95パーセンタイル
      - p99_{metric_column}: 99パーセンタイル
    
    パーセンタイルとは:
      - p50: データの50%がこの値以下（中央値）
      - p90: データの90%がこの値以下
      - p95: データの95%がこの値以下（上位5%の境界）
      - p99: データの99%がこの値以下（上位1%の境界）
    
    例:
      {{ percentile('response_time_sec', [50, 90, 95, 99]) }}
      → APPROX_QUANTILES(response_time_sec, 100)[OFFSET(50)] as p50_response_time_sec,
        APPROX_QUANTILES(response_time_sec, 100)[OFFSET(90)] as p90_response_time_sec,
        APPROX_QUANTILES(response_time_sec, 100)[OFFSET(95)] as p95_response_time_sec,
        APPROX_QUANTILES(response_time_sec, 100)[OFFSET(99)] as p99_response_time_sec
  #}
  {% for p in percentiles %}
  {#- BigQueryのAPPROX_QUANTILES関数を使用してパーセンタイルを計算 -#}
  APPROX_QUANTILES({{ metric_column }}, 100)[OFFSET({{ p }})] as p{{ p }}_{{ metric_column }}
  {%- if not loop.last %},{% endif %}
  {% endfor %}
{% endmacro %}
