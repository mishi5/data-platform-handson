-- URL別パフォーマンス分析
-- ビジネス用途: パフォーマンス監視、ボトルネック特定

with access_logs as (
    select * from {{ ref('stg_access_logs') }}
),

url_stats as (
    select
        -- URL情報
        url_path,
        
        -- 日付（パーティション活用）
        date(request_timestamp) as date,
        
        -- リクエスト統計
        count(*) as total_requests,
        count(distinct client_ip) as unique_visitors,
        
        -- パフォーマンス統計
        round(avg(response_time_sec), 3) as avg_response_time,
        round(max(response_time_sec), 3) as max_response_time,
        round(min(response_time_sec), 3) as min_response_time,
        round(stddev(response_time_sec), 3) as stddev_response_time,
        
        -- レスポンスサイズ統計
        round(avg(response_size_kb), 2) as avg_response_size_kb,
        round(sum(response_size_kb), 2) as total_response_size_kb,
        
        -- ステータス別集計
        countif(status_category = 'success') as success_count,
        countif(status_category = 'redirect') as redirect_count,
        countif(status_category = 'client_error') as client_error_count,
        countif(status_category = 'server_error') as server_error_count,
        
        -- エラー率
        round(safe_divide(
            countif(status_category in ('client_error', 'server_error')),
            count(*)
        ) * 100, 2) as error_rate_percent
        
    from access_logs
    group by url_path, date
),

url_rankings as (
    select
        *,
        -- 遅いURLランキング
        row_number() over (partition by date order by avg_response_time desc) as slowest_rank,
        -- エラーが多いURLランキング
        row_number() over (partition by date order by client_error_count + server_error_count desc) as most_errors_rank
    from url_stats
)

select * from url_rankings