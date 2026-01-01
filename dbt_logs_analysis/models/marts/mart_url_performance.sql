-- URL別パフォーマンス分析
-- ビジネス用途: パフォーマンス監視、ボトルネック特定

WITH access_logs AS (
    SELECT * FROM {{ ref('stg_access_logs') }}
),

url_stats AS (
    SELECT
        -- URL情報
        url_path,

        -- 日付（パーティション活用）
        date(request_timestamp) AS date,

        -- リクエスト統計
        count(*) AS total_requests,
        count(DISTINCT client_ip) AS unique_visitors,

        -- パフォーマンス統計
        round(avg(response_time_sec), 3) AS avg_response_time,
        round(max(response_time_sec), 3) AS max_response_time,
        round(min(response_time_sec), 3) AS min_response_time,
        round(stddev(response_time_sec), 3) AS stddev_response_time,

        -- レスポンスサイズ統計
        round(avg(response_size_kb), 2) AS avg_response_size_kb,
        round(sum(response_size_kb), 2) AS total_response_size_kb,

        -- ステータス別集計
        countif(status_category = 'success') AS success_count,
        countif(status_category = 'redirect') AS redirect_count,
        countif(status_category = 'client_error') AS client_error_count,
        countif(status_category = 'server_error') AS server_error_count,

        -- エラー率
        round(safe_divide(
            countif(status_category IN ('client_error', 'server_error')),
            count(*)
        ) * 100, 2) AS error_rate_percent

    FROM access_logs
    GROUP BY url_path, date
),

url_rankings AS (
    SELECT
        *,
        -- 遅いURLランキング
        row_number()
            OVER (PARTITION BY date ORDER BY avg_response_time DESC)
            AS slowest_rank,
        -- エラーが多いURLランキング
        row_number()
            OVER (
                PARTITION BY date
                ORDER BY client_error_count + server_error_count DESC
            )
            AS most_errors_rank
    FROM url_stats
)

SELECT * FROM url_rankings
