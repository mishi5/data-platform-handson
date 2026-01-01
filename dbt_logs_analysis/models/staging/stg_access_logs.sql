-- Staging: Access Logs
-- BigQuery版（Macro使用）

WITH source AS (
    SELECT * FROM {{ source('raw', 'access') }}
),

cleaned AS (
    SELECT
        -- タイムスタンプ（既にTIMESTAMP型）
        timestamp AS request_timestamp,

        -- IPアドレス
        ip AS client_ip,

        -- HTTPメソッド
        upper(method) AS http_method,

        -- URL（クエリパラメータを除く）
        split(url, '?')[offset(0)] AS url_path,
        url AS full_url,

        -- ステータスコード
        status AS status_code,

        -- ステータスカテゴリ（Macroを使用）
        {{ error_category('status') }} AS status_category,

        -- レスポンスサイズ（KB）
        cast(size AS float64) / 1024 AS response_size_kb,

        -- レスポンスタイム（秒）
        response_time AS response_time_sec

    FROM source
)

SELECT * FROM cleaned
