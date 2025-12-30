-- Staging: Application Logs
-- BigQuery版（TIMESTAMPパーティション対応）

with source as (
    select * from {{ source('raw', 'app') }}
),

cleaned as (
    select
        -- タイムスタンプ（既にTIMESTAMP型）
        timestamp as event_timestamp,
        
        -- ログレベル
        upper(level) as log_level,
        
        -- アクション
        action as event_action,
        
        -- ユーザー情報
        user_id,
        session_id,
        
        -- パフォーマンス
        duration_ms,
        cast(duration_ms as float64) / 1000 as duration_sec,
        
        -- エラー情報
        error_type,
        error_message,
        
        -- リクエスト情報
        ip as client_ip,
        endpoint
        
    from source
)

select * from cleaned