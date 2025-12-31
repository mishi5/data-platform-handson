-- URL別パフォーマンス分析 v2（Macro活用版）

with access_logs as (
    select * from {{ ref('stg_access_logs') }}
    where {{ recent_days('request_timestamp', 30) }}  -- Macro使用
),

url_stats as (
    select
        url_path,
        date(request_timestamp) as date,
        
        -- 基本統計
        count(*) as total_requests,
        count(distinct client_ip) as unique_visitors,
        
        -- パフォーマンス統計（Macroを使用）
        {{ performance_stats('response_time_sec', 3) }},
        
        -- パーセンタイル（Macroを使用）
        {{ percentile('response_time_sec', [50, 90, 95, 99]) }},
        
        -- レスポンスサイズ
        round(avg(response_size_kb), 2) as avg_response_size_kb,
        
        -- エラー統計（Macroを使用）
        countif({{ is_http_error('status_code') }}) as error_count,
        countif({{ is_server_error('status_code') }}) as server_error_count,
        countif({{ is_client_error('status_code') }}) as client_error_count,
        
        -- エラー率
        round(safe_divide(
            countif({{ is_http_error('status_code') }}),
            count(*)
        ) * 100, 2) as error_rate_percent
        
    from access_logs
    group by url_path, date
)

select * from url_stats
order by date desc, total_requests desc