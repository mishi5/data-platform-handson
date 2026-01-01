{{
  config(
    materialized='incremental',
    unique_key=['url_path', 'date'],
    on_schema_change='sync_all_columns',
    partition_by={
      'field': 'date',
      'data_type': 'date'
    }
  )
}}

-- URL別パフォーマンス分析（Incremental版）
-- Macroを活用した効率的な増分更新

WITH access_logs AS (
    SELECT * FROM {{ ref('stg_access_logs') }}
    
    {% if is_incremental() %}
      -- 増分実行: 前回実行以降のデータのみ処理
      WHERE DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})
    {% else %}
      -- 初回実行: 過去30日分のデータを処理
      WHERE {{ recent_days('request_timestamp', 30) }}
    {% endif %}
),

url_stats AS (
    SELECT
        url_path,
        DATE(request_timestamp) AS date,
        
        -- 基本統計
        COUNT(*) AS total_requests,
        COUNT(DISTINCT client_ip) AS unique_visitors,
        
        -- パフォーマンス統計（Macroを使用）
        {{ performance_stats('response_time_sec', 3) }},
        
        -- パーセンタイル（Macroを使用）
        {{ percentile('response_time_sec', [50, 90, 95, 99]) }},
        
        -- レスポンスサイズ
        ROUND(AVG(response_size_kb), 2) AS avg_response_size_kb,
        
        -- エラー統計（Macroを使用）
        COUNTIF({{ is_http_error('status_code') }}) AS error_count,
        COUNTIF({{ is_server_error('status_code') }}) AS server_error_count,
        COUNTIF({{ is_client_error('status_code') }}) AS client_error_count,
        
        -- エラー率
        ROUND(SAFE_DIVIDE(
            COUNTIF({{ is_http_error('status_code') }}),
            COUNT(*)
        ) * 100, 2) AS error_rate_percent
        
    FROM access_logs
    GROUP BY url_path, date
)

SELECT * FROM url_stats
