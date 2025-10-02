import requests
from flask import Flask, request, jsonify

# 初始化 Flask app
app = Flask(__name__)

def fetch_html(url: str) -> tuple[str | None, str | None]:
    """
    抓取給定 URL 的 HTML 內容。

    Args:
        url: 目標網頁的 URL。

    Returns:
        一個元組 (html, error)。如果成功，html 是頁面內容，error 是 None。
        如果失敗，html 是 None，error 是錯誤訊息。
    """
    try:
        # 發送 GET 請求，設定 10 秒超時
        response = requests.get(url, timeout=10)
        # 檢查請求是否成功
        response.raise_for_status()
        # 返回 HTML 內容
        return response.text, None
    except requests.exceptions.RequestException as e:
        # 處理所有 requests 可能的異常
        error_message = f"抓取 URL 時發生錯誤: {e}"
        print(error_message)
        return None, error_message

@app.route("/execute_tool", methods=["POST"])
def execute_tool():
    """
    模擬 Gemini 工具呼叫的端點。
    接收 Gemini 的 function_call 請求，執行 fetch_html，並返回 function_response。
    """
    try:
        # 獲取請求的 JSON 數據
        req_data = request.get_json()
        if not req_data:
            return jsonify({"error": "無效的 JSON 請求"}), 400

        # 從請求中解析出函式呼叫的參數
        # 根據 Gemini 的格式，參數位於 function_call.args
        function_call = req_data.get("function_call")
        if not function_call or function_call.get("name") != "fetch_html":
            return jsonify({"error": "無效的 function_call 或名稱不匹配"}), 400
        
        args = function_call.get("args", {})
        url = args.get("url")

        if not url:
            return jsonify({"error": "請求的 args 中未提供 'url'"}), 400

        # 執行核心功能
        html_content, error = fetch_html(url)

        if error:
            # 如果抓取失敗，也以工具回應的格式返回錯誤
            response_data = {
                "content": f"抓取失敗: {error}"
            }
        else:
            # 成功，將 HTML 內容放入回應
            response_data = {
                "content": html_content
            }
        
        # 構建 Gemini期望的 function_response 格式
        tool_response = {
            "function_response": {
                "name": "fetch_html",
                "response": response_data
            }
        }
        
        return jsonify(tool_response)

    except Exception as e:
        # 處理意外錯誤
        print(f"處理 /execute_tool 時發生未知錯誤: {e}")
        return jsonify({"error": f"伺服器內部錯誤: {e}"}), 500

# 允許直接執行此文件來啟動一個測試伺服器
if __name__ == '__main__':
    # 監聽所有網路介面，方便測試
    app.run(host='0.0.0.0', port=8080, debug=True)