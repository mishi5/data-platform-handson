-- URL別パフォーマンス分析 v2（Macro活用版）

WITH access_logs AS (
    SELECT * FROM {{ ref('stg_access_logs') }}
    WHERE {{ recent_days('request_timestamp', 30) }}  -- Macro使用
),

url_stats AS (
    SELECT
        url_path,
        date(request_timestamp) AS date,

        -- 基本統計
        count(*) AS total_requests,
        count(DISTINCT client_ip) AS unique_visitors,

        -- パフォーマンス統計（Macroを使用）
        {{ performance_stats('response_time_sec', 3) }},

        -- パーセンタイル（Macroを使用）
        {{ percentile('response_time_sec', [50, 90, 95, 99]) }},

        -- レスポンスサイズ
        round(avg(response_size_kb), 2) AS avg_response_size_kb,

        -- エラー統計（Macroを使用）
        countif({{ is_http_error('status_code') }}) AS error_count,
        countif({{ is_server_error('status_code') }}) AS server_error_count,
        countif({{ is_client_error('status_code') }}) AS client_error_count,

        -- エラー率
        round(safe_divide(
            countif({{ is_http_error('status_code') }}),
            count(*)
        ) * 100, 2) AS error_rate_percent

    FROM access_logs
    GROUP BY url_path, date
)

SELECT * FROM url_stats
ORDER BY date DESC, total_requests DESC
