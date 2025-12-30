-- Staging: Access Logs
-- BigQuery版（TIMESTAMPパーティション対応）

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
        
        -- ステータスカテゴリ
        case
            when status between 200 and 299 then 'success'
            when status between 300 and 399 then 'redirect'
            when status between 400 and 499 then 'client_error'
            when status between 500 and 599 then 'server_error'
            else 'unknown'
        end as status_category,
        
        -- レスポンスサイズ（KB）
        cast(size as float64) / 1024 as response_size_kb,
        
        -- レスポンスタイム（秒）
        response_time as response_time_sec
        
    from source
)

select * from cleaned