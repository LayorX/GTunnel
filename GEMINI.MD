# GTunnel 專案開發規劃書 (v2.1 - MVP 優先版)

本文檔根據 `SPEC.txt` 的需求，並結合 MVP (最小可行性產品) 優先的開發策略，提供一份實現端對端網頁代理隧道的詳細技術規劃、開發步驟與架構設計。

---

## 1. MVP 開發策略調整 (MVP Strategy Pivot)

在與使用者討論後，我們達成共識：為了以最快速度驗證核心功能循環（請求 → 擷取 → 重寫 → 呈現），**第一版 MVP 將暫不使用 Firebase**。

我們將採用更直接的方式：**直接利用 Gemini API (Tool) 的請求與返回機制來完成數據傳輸**。這將大幅簡化初始設定，讓我們能專注於本地代理與遠端擷取的程式邏輯。

Firebase 的整合將被視為**第二階段的擴展功能**，當我們需要處理超出 API 回應長度限制的複雜網頁（如包含 CSS/JS/圖片）時，再將其引入。

---

## 2. 整體框架 (Overall Architecture)

### 2.1 MVP 簡化架構 (Simplified MVP Architecture)

在 MVP 階段，數據直接透過 Gemini 的工具呼叫（Tool Call）來回傳遞，流程極度簡化。

```mermaid
graph TD
    subgraph "A) 本地端 (User's Machine)"
        A1[使用者瀏覽器] -- 1. 輸入 URL --> A2[本地 Flask 代理 App];
        A2 -- 2. 呼叫 Gemini 工具 --> B1{Gemini API / Tool Call};
        B1 -- 5. 將 HTML 字串結果返回 --> A2;
        A2 -- 6. 重寫 HTML 後呈現給 --> A1;
    end

    subgraph "B) 遠端執行器 (Cloud Server)"
        B1 -- 3. 觸發遠端工具 --> C1[GTunnel-CLI 後端 (Cloud Run)];
        C1 -- 4. 擷取 HTML --> D1[目標網站];
    end

    style A2 fill:#9cf,stroke:#333,stroke-width:2px
    style C1 fill:#f9f,stroke:#333,stroke-width:2px
```

### 2.2 完整功能架構 (Future Full-Feature Architecture)

（此為未來擴展藍圖，當 MVP 完成後，我們將朝此架構演進以支援更複雜的功能）

```mermaid
graph TD
    subgraph "A) 本地端 (User's Machine)"
        A1[使用者瀏覽器] -- 1. 開啟 http://127.0.0.1:5000 --> A2[本地 Flask 代理 App];
        A2 -- 2. 將請求寫入 Firebase --> B1[Firebase Firestore (請求隊列)];
        A2 -- 8. 監聽到數據後拉取 --> B2[Firebase Firestore (結果儲存)];
        A2 -- 9. 重寫 HTML/CSS 後呈現給 --> A1;
    end

    subgraph "B) 通訊隧道層 (Google Cloud)"
        B1 -- 4. 觸發遠端執行器 --> C1;
        C1 -- 7. 將擷取結果寫入 --> B2;
    end

    subgraph "C) 遠端執行器層 (Cloud Server)"
        C1[GTunnel-CLI 後端 (Cloud Run)] -- 5. 訪問外部網路 --> D1[目標網站];
        D1 -- 6. 回傳 HTML/CSS/JS/圖片 --> C1;
    end
```

---

## 3. 技術選型與原因 (Technology Stack)

| 組件 | 技術選型 | 原因 |
| :--- | :--- | :--- |
| **本地代理 App** | **Python + Flask** | 依據 SPEC 要求。Flask 輕量且易於上手，非常適合做為本地代理伺服器。 |
| **遠端執行器** | **Python + Flask** | 保持技術棧統一，簡化開發。它將被封裝成一個 Gemini 可呼叫的工具。 |
| **內容擷取/解析** | **Requests + BeautifulSoup4** | `Requests` 用於穩定地擷取網頁，`BeautifulSoup4` 則是用於後續在**本地端**進行 HTML 重寫的關鍵。 |
| **數據隧道** | **Gemini API (MVP)** / **Firebase (未來)** | **MVP 階段**，直接使用 Gemini API 的工具回傳機制，簡單直接。**未來**為處理大數據量和非同步任務，將導入 Firebase Firestore。 |
| **部署平台** | **Google Cloud Run** | 遠端執行器的最佳選擇。Serverless 架構，支援 Docker，完美符合需求。 |

---

## 4. 開發待辦清單 (TODOLIST) - MVP 階段

### Part A: 遠端執行器 (GTunnel-CLI Backend) 開發
- [x] **專案設定**: 初始化 Flask 專案，安裝 `Flask`, `requests`。
- [x] **建立核心工具函式**: `fetch_html(url: str) -> str`
- [x] **封裝為 API 端點**: 建立 `/execute_tool` 路由，模擬 Gemini Tool Call。
- [x] **部署準備**: 編寫 `Dockerfile`。
- [x] **部署到 Google Cloud Run**

### Part B: 本地代理 (Flask Proxy App) 開發
- [x] **專案設定**: 初始化 Flask 專案，安裝 `Flask`, `beautifulsoup4`, `google-generativeai`。
- [x] **UI 介面**: 建立根路由 (`/`)。
- [x] **核心代理路由 (`/proxy`)**: 完成 Gemini 呼叫、遠端請求、HTML 重寫的完整邏輯。
- [x] **環境設定**: 建立 `.env` 檔案以管理 API 金鑰和遠端 URL。

---

## 5. 階段性功能交付 (Milestones)

### Milestone 1: MVP - 純文字網頁代理驗證
- **目標**: 驗證**無 Firebase**的端到端代理流程，成功代理一個純 HTML 頁面。
- **完成標準**:
    1. 遠端執行器已部署在 Cloud Run 上。
    2. 本地 Flask App 能夠運行。
    3. 在本地 App (`http://127.0.0.1:5000`) 輸入 `http://example.com`，能夠看到該網頁的文字內容和連結。
    4. **數據透過 Gemini Tool 的回傳值直接傳輸。**
    5. 網頁中的所有連結都已被重寫為指向本地代理。
    6. 點擊任一連結，能觸發一次新的代理請求，並成功載入下一頁的內容。
- **此階段不包含**: Firebase 整合、CSS、圖片、JS 的載入。

### Milestone 2: 引入 Firebase 與富內容支援 (未來階段)
- **目標**: 解決數據量限制，開始支援 CSS 與圖片等靜態資源。
- **完成標準**: 整合 Firebase 作為數據隧道，實現「完整功能架構圖」中的流程，使代理的網頁能基本還原其原始樣式與佈局。

---

## v2.2 - 開發與部署日誌

本節記錄了從開發完成到成功部署的完整除錯歷程。

### 1. 程式碼實作與修正

- **`local_proxy`**: 經歷了多次 `replace` 操作失敗後，最終採用 `write_file` 完整覆蓋的方式，成功寫入包含 BeautifulSoup 重寫邏輯的 `main.py`。
- **`remote_executor`**: 將其 API 端點從標準的 REST API 修改為模擬 Gemini Tool Call 的 `/execute_tool` 路由，使其能被 `local_proxy` 正確呼叫。
- **Gemini Tool Call 流程修正**: 修正了 `local_proxy` 的核心邏輯。原先錯誤地認為 Gemini API 會直接返回工具執行的結果 (`function_response`)，修正後改為正確的兩階段流程：
    1. 從 Gemini 得到執行指令 (`function_call`)。
    2. `local_proxy` 主動使用 `requests` 呼叫遠端服務來執行指令。

### 2. 部署與除錯歷程

將 `remote_executor` 部署到 Google Cloud Run 的過程遇到了一系列挑戰，以下是按時間順序的解決記錄：

1.  **問題：帳單未啟用 (`Billing Not Found`)**
    - **現象**: 執行 `gcloud services enable` 時失敗。
    - **原因**: Google Cloud 專案未綁定有效的帳單帳戶。
    - **解決**: 使用者在 Cloud Console 中為專案連結了帳單帳戶。

2.  **問題：映像倉庫不存在 (`Repository Not Found`)**
    - **現象**: 執行 `gcloud builds submit` 在推送映像階段失敗。
    - **原因**: 用於存放 Docker 映像的 Artifact Registry 倉庫尚未建立。
    - **解決**: 重新執行 `gcloud artifacts repositories create` 指令，成功建立倉庫。

3.  **問題：容器無法啟動 (`Container Failed to Start`) - 第一次**
    - **現象**: `gcloud run deploy` 失敗，日誌顯示容器無法在指定端口上監聽。
    - **原因**: `Dockerfile` 中使用 `gunicorn` 作為伺服器，但 `gunicorn` 未被添加到 `pyproject.toml` 的依賴項中。
    - **解決**: 將 `gunicorn` 添加到依賴項，並簡化 `Dockerfile` 中的安裝指令。

4.  **問題：容器無法啟動 (`Container Failed to Start`) - 第二次**
    - **現象**: 即使修正了依賴，部署仍然失敗。
    - **原因**: `Dockerfile` 中的 `CMD` 指令使用了 `exec` 格式 (`["..."]`)，導致 `$PORT` 環境變數無法被 shell 解析，`gunicorn` 未在正確的端口上啟動。
    - **解決**: 將 `CMD` 指令修改為 `shell` 格式 (`gunicorn ...`)，使其能正確讀取環境變數。

5.  **問題：模型不可用 (`404 Model Not Found`)**
    - **現象**: 本地測試時，應用程式報錯，提示 `gemini-1.5-flash-latest` 模型找不到。
    - **原因**: 使用者的帳號/區域無法使用該特定模型。
    - **解決**: 臨時修改 `main.py` 以列出所有可用模型，並根據列表結果將模型名稱更換為可用的 `models/gemini-flash-latest`。

6.  **問題：語法錯誤 (`IndentationError`)**
    - **現象**: 在修復模型問題後，本地執行 `main.py` 時出現縮排錯誤。
    - **原因**: 多次 `replace` 操作可能引入了不可見的定位字元 (Tab) 與空格的混用。
    - **解決**: 使用 `replace` 將整個函式替換為格式正確的版本，消除潛在的縮排問題。

7.  **問題：遠端呼叫被拒 (`403 Forbidden`)**
    - **現象**: 本地代理呼叫遠端 Cloud Run 服務時，收到 `403 Forbidden` 錯誤。
    - **原因**: 在先前多次部署失敗的過程中，允許公開訪問的 IAM 策略未能成功應用。
    - **解決**: 指導使用者執行 `gcloud run services add-iam-policy-binding` 指令，手動為服務授予公開呼叫權限。

### 3. 當前狀態與後續步驟

- **當前狀態**: 在執行 `add-iam-policy-binding` 指令時，再次遇到權限問題 (`PERMISSION_DENIED`)。
- **根本原因**: 使用者帳號 `yor31117@gmail.com` 缺少 `run.services.setIamPolicy` 權限，無法修改 Cloud Run 服務的存取策略。
- **後續步驟**: 使用者需要在 Google Cloud Console 的 IAM 頁面，為自己的帳號添加 **"Cloud Run Admin"** 角色，然後再次執行 `gcloud run services add-iam-policy-binding` 指令。完成後，整個專案即可投入使用。