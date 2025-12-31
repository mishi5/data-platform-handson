{#
  HTTPステータスコードのエラー判定用マクロ集
  
  使用例:
    WHERE {{ is_http_error('status_code') }}
    CASE WHEN {{ is_server_error('status') }} THEN 'critical' END
    {{ error_category('status_code') }} as status_type
#}

{% macro is_http_error(status_code_column) %}
  {#
    HTTPエラー（4xx, 5xx）かどうかを判定
    
    引数:
      status_code_column: HTTPステータスコードのカラム名
    
    戻り値:
      ブール式（400以上ならエラー）
    
    例:
      WHERE {{ is_http_error('status_code') }}
      → WHERE status_code >= 400
  #}
  {{ status_code_column }} >= 400
{% endmacro %}


{% macro is_server_error(status_code_column) %}
  {#
    サーバーエラー（5xx）かどうかを判定
    
    引数:
      status_code_column: HTTPステータスコードのカラム名
    
    戻り値:
      ブール式（500以上ならサーバーエラー）
    
    例:
      COUNTIF({{ is_server_error('status') }}) as server_errors
      → COUNTIF(status >= 500) as server_errors
  #}
  {{ status_code_column }} >= 500
{% endmacro %}


{% macro is_client_error(status_code_column) %}
  {#
    クライアントエラー（4xx）かどうかを判定
    
    引数:
      status_code_column: HTTPステータスコードのカラム名
    
    戻り値:
      ブール式（400-499の範囲ならクライアントエラー）
    
    例:
      COUNTIF({{ is_client_error('status') }}) as client_errors
      → COUNTIF(status >= 400 AND status < 500) as client_errors
  #}
  {{ status_code_column }} >= 400 AND {{ status_code_column }} < 500
{% endmacro %}


{% macro error_category(status_code_column) %}
  {#
    HTTPステータスコードをカテゴリに分類
    
    引数:
      status_code_column: HTTPステータスコードのカラム名
    
    戻り値:
      CASE式（success/redirect/client_error/server_error/unknown）
    
    分類:
      200-299: success（成功）
      300-399: redirect（リダイレクト）
      400-499: client_error（クライアントエラー）
      500-599: server_error（サーバーエラー）
      その他: unknown（不明）
    
    例:
      {{ error_category('status_code') }} as status_category
      → CASE
          WHEN status_code BETWEEN 200 AND 299 THEN 'success'
          WHEN status_code BETWEEN 300 AND 399 THEN 'redirect'
          ...
        END as status_category
  #}
  CASE
    WHEN {{ status_code_column }} BETWEEN 200 AND 299 THEN 'success'
    WHEN {{ status_code_column }} BETWEEN 300 AND 399 THEN 'redirect'
    WHEN {{ status_code_column }} BETWEEN 400 AND 499 THEN 'client_error'
    WHEN {{ status_code_column }} BETWEEN 500 AND 599 THEN 'server_error'
    ELSE 'unknown'
  END
{% endmacro %}
