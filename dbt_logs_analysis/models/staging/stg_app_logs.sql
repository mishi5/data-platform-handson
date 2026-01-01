-- Staging: Application Logs
-- BigQuery版（TIMESTAMPパーティション対応）

WITH source AS (
    SELECT * FROM {{ source('raw', 'app') }}
),

cleaned AS (
    SELECT
        -- タイムスタンプ（既にTIMESTAMP型）
        timestamp AS event_timestamp,

        -- ログレベル
        upper(level) AS log_level,

        -- アクション
        action AS event_action,

        -- ユーザー情報
        user_id,
        session_id,

        -- パフォーマンス
        duration_ms,
        cast(duration_ms AS float64) / 1000 AS duration_sec,

        -- エラー情報
        error_type,
        error_message,

        -- リクエスト情報
        ip AS client_ip,
        endpoint

    FROM source
)

SELECT * FROM cleaned
