-- エラー分析
-- ビジネス用途: 障害対応、品質改善

with app_errors as (
    select
        date(event_timestamp) as date,
        extract(hour from event_timestamp) as hour,
        log_level,
        event_action,
        error_type,
        error_message,
        user_id,
        client_ip,
        endpoint
    from {{ ref('stg_app_logs') }}
    where log_level = 'ERROR'
),

access_errors as (
    select
        date(request_timestamp) as date,
        extract(hour from request_timestamp) as hour,
        status_code,
        status_category,
        http_method,
        url_path,
        client_ip
    from {{ ref('stg_access_logs') }}
    where status_category in ('client_error', 'server_error')
),

app_error_summary as (
    select
        date,
        hour,
        'app_error' as error_source,
        error_type as error_detail,
        count(*) as error_count,
        count(distinct user_id) as affected_users,
        count(distinct client_ip) as affected_ips
    from app_errors
    group by date, hour, error_type
),

access_error_summary as (
    select
        date,
        hour,
        'http_error' as error_source,
        concat('HTTP ', cast(status_code as string)) as error_detail,
        count(*) as error_count,
        0 as affected_users,
        count(distinct client_ip) as affected_ips
    from access_errors
    group by date, hour, status_code
),

combined_errors as (
    select * from app_error_summary
    union all
    select * from access_error_summary
)

select
    *,
    sum(error_count) over (partition by date order by hour) as cumulative_errors_today
from combined_errors
order by date desc, hour desc, error_count desc