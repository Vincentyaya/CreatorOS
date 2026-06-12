FROM python:3.12-slim

WORKDIR /app

# 装系统依赖 + 视频下载工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir you-get

# 分步安装依赖（减少内存峰值）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# Render 会用 PORT 环境变量
EXPOSE 10000

CMD ["python", "server.py"]
