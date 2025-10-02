from dotenv import load_dotenv

# 在應用程式啟動時載入 .env 檔案中的環境變數
load_dotenv()

import os
import requests
import json
from flask import Flask, request, render_template_string, url_for
from urllib.parse import urljoin
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
from bs4 import BeautifulSoup

# --- Flask App 設定 ---
app = Flask(__name__)

# --- Gemini 設定 ---
def get_gemini_model():
    """初始化並返回 Gemini 模型"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("錯誤：未設定 GEMINI_API_KEY。")
    genai.configure(api_key=api_key)

    # 遠端工具的 FunctionDeclaration
    fetch_html_func = FunctionDeclaration(
        name="fetch_html",
        description="根據提供的 URL，擷取網站的 HTML 內容。",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要擷取 HTML 的目標 URL。"
                }
            },
            "required": ["url"]
        },
    )

    # 建立工具
    remote_tool = Tool(
        function_declarations=[fetch_html_func],
    )

    # 設定模型
    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        tools=[remote_tool]
    )
    return model

# --- HTML 模板 ---
HOME_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GTunnel 代理</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f9; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 2em; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #444; }
        .url-input { width: 100%; padding: 0.8em; font-size: 1em; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .submit-btn { display: block; width: 100%; padding: 0.8em 1em; font-size: 1em; margin-top: 1em; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .submit-btn:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>GTunnel 網頁代理</h1>
        <form action="{{ url_for('proxy') }}" method="get">
            <input type="url" name="url" class="url-input" placeholder="請輸入要代理的網址..." required>
            <button type="submit" class="submit-btn">開始代理</button>
        </form>
    </div>
</body>
</html>
'''

# --- 路由 ---
@app.route('/')
def home():
    """顯示主頁面，提供 URL 輸入框。"""
    return render_template_string(HOME_PAGE_TEMPLATE)

@app.route('/proxy')
def proxy():
    """
    核心代理路由。
    1. 從查詢參數中獲取目標 URL。
    2. 呼叫 Gemini 模型，獲得執行 'fetch_html' 工具的指令 (function_call)。
    3. 使用 requests 向我們部署的遠端執行器發送請求，執行該指令。
    4. 從遠端執行器的回應中提取 HTML 內容。
    5. 使用 BeautifulSoup 解析和重寫 HTML。
    6. 將修改後的 HTML 返回給瀏覽器。
    """
    target_url = request.args.get('url')
    if not target_url:
        return "錯誤：請提供 'url' 參數。", 400

    remote_executor_url = os.environ.get("REMOTE_EXECUTOR_URL")
    if not remote_executor_url:
        return "錯誤：未設定 REMOTE_EXECUTOR_URL 環境變數。", 500

    try:
        # --- 步驟 2: 請求 Gemini 生成工具呼叫 ---
        model = get_gemini_model()
        response = model.generate_content(
            f"請使用 fetch_html 工具擷取此 URL 的內容: {target_url}",
            tool_config={'function_calling_config': 'ANY'}
        )
        
        # 從模型的回應中獲取 function_call
        part = response.candidates[0].content.parts[0]
        if not (part.function_call and part.function_call.name == "fetch_html"):
            return f"錯誤：Gemini 未能生成有效的 fetch_html 工具呼叫。模型回應: {response.text}", 500
        
        function_call = part.function_call

        # --- 步驟 3: 執行工具呼叫 ---
        # 將 Gemini 生成的 function_call 對象作為請求體，發送到遠端執行器
        api_response = requests.post(
            remote_executor_url,
            headers={"Content-Type": "application/json"},
            # 將 function_call.args 轉換為普通字典
            json={"function_call": {"name": function_call.name, "args": dict(function_call.args)}}
        )
        api_response.raise_for_status() # 如果請求失敗則拋出異常
        
        # --- 步驟 4: 提取 HTML ---
        # 解析遠端執行器返回的 JSON
        tool_response = api_response.json()
        html_content = tool_response['function_response']['response']['content']

        if "抓取失敗" in html_content:
             return f"錯誤：遠端執行器無法抓取該網頁。詳細資訊: {html_content}", 500

        # --- 步驟 5: HTML 重寫 ---
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for tag in soup.find_all(href=True):
            original_url = tag['href']
            absolute_url = urljoin(target_url, original_url)
            tag['href'] = url_for('proxy', url=absolute_url)

        for tag in soup.find_all(src=True):
            original_url = tag['src']
            absolute_url = urljoin(target_url, original_url)
            tag['src'] = url_for('proxy', url=absolute_url)

        # --- 步驟 6: 返回重寫後的 HTML ---
        return str(soup)

    except requests.exceptions.RequestException as e:
        return f"呼叫遠端執行器時發生網路錯誤: {e}", 500
    except Exception as e:
        print(f"代理請求 '{target_url}' 失敗: {e}")
        return f"處理請求時發生嚴重錯誤: {e}", 500

# --- 主程式入口 ---
if __name__ == '__main__':
    # 使用 waitress 作為生產環境的 WSGI 伺服器，更穩定
    # from waitress import serve
    # serve(app, host='0.0.0.0', port=5000)
    app.run(host='127.0.0.1', port=5000, debug=True)