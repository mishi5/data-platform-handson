-- Staging: Access Logs
-- BigQuery版（Macro使用）

with source as (
    select * from {{ source('raw', 'access') }}
),

cleaned as (
    select
        -- タイムスタンプ（既にTIMESTAMP型）
        timestamp as request_timestamp,
        
        -- IPアドレス
        ip as client_ip,
        
        -- HTTPメソッド
        upper(method) as http_method,
        
        -- URL（クエリパラメータを除く）
        split(url, '?')[offset(0)] as url_path,
        url as full_url,
        
        -- ステータスコード
        status as status_code,
        
        -- ステータスカテゴリ（Macroを使用）
        {{ error_category('status') }} as status_category,
        
        -- レスポンスサイズ（KB）
        cast(size as float64) / 1024 as response_size_kb,
        
        -- レスポンスタイム（秒）
        response_time as response_time_sec
        
    from source
)

select * from cleaned