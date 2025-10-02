# 1. 使用官方 Python 映像作為基礎
FROM python:3.10-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 安裝依賴項
# 首先複製 pyproject.toml 以利用 Docker 的層快取
COPY pyproject.toml .
# 安裝專案依賴 (包括 gunicorn)
RUN pip install --no-cache-dir .

# 4. 複製應用程式程式碼
COPY main.py .

# 5. 設定環境變數
# Cloud Run 會自動設定這個 PORT 環境變數，我們預設為 8080
ENV PORT 8080

# 6. 執行應用程式
# 使用 gunicorn 作為 WSGI 伺服器
# --workers 3 是一個合理的起點
# --bind 0.0.0.0:${PORT} 讓 gunicorn 監聽所有介面，並使用 Cloud Run 提供的端口
# main:app 指向 main.py 文件中的 app 物件
CMD gunicorn --workers 3 --bind 0.0.0.0:$PORT main:app