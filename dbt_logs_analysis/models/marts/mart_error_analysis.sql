-- エラー分析
-- ビジネス用途: 障害対応、品質改善

WITH app_errors AS (
    SELECT
        date(event_timestamp) AS date,
        extract(HOUR FROM event_timestamp) AS hour,
        log_level,
        event_action,
        error_type,
        error_message,
        user_id,
        client_ip,
        endpoint
    FROM {{ ref('stg_app_logs') }}
    WHERE log_level = 'ERROR'
),

access_errors AS (
    SELECT
        date(request_timestamp) AS date,
        extract(HOUR FROM request_timestamp) AS hour,
        status_code,
        status_category,
        http_method,
        url_path,
        client_ip
    FROM {{ ref('stg_access_logs') }}
    WHERE status_category IN ('client_error', 'server_error')
),

app_error_summary AS (
    SELECT
        date,
        hour,
        'app_error' AS error_source,
        error_type AS error_detail,
        count(*) AS error_count,
        count(DISTINCT user_id) AS affected_users,
        count(DISTINCT client_ip) AS affected_ips
    FROM app_errors
    GROUP BY date, hour, error_type
),

access_error_summary AS (
    SELECT
        date,
        hour,
        'http_error' AS error_source,
        concat('HTTP ', cast(status_code AS string)) AS error_detail,
        count(*) AS error_count,
        0 AS affected_users,
        count(DISTINCT client_ip) AS affected_ips
    FROM access_errors
    GROUP BY date, hour, status_code
),

combined_errors AS (
    SELECT * FROM app_error_summary
    UNION ALL
    SELECT * FROM access_error_summary
)

SELECT
    *,
    sum(error_count)
        OVER (PARTITION BY date ORDER BY hour)
        AS cumulative_errors_today
FROM combined_errors
ORDER BY date DESC, hour DESC, error_count DESC
