# AWS Lambda Python 3.12 ベースイメージ
FROM public.ecr.aws/lambda/python:3.12

# 作業ディレクトリ
WORKDIR ${LAMBDA_TASK_ROOT}

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app.py .

# Lambda handler を指定
CMD ["app.lambda_handler"]
