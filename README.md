# Stocker — AI 美股分析器

本地部署的美股追蹤與分析工具，提供即時串流行情、互動圖表、金融報告 PDF 閱讀及 AI 智能分析。支援繁體中文 / English 雙語介面。

## 功能

- **即時行情追蹤** — 每 5 秒自動更新價格，支援多支美股同時監控
- **互動圖表** — 支援 MA/RSI/MACD/Volume 等技術指標，可個別開關顯示
- **SEC 財報下載** — 自動從 SEC EDGAR 下載 10-K / 10-Q 年報季報
- **金融機構分析報告** — 收集各大銀行及投行的分析師評級及預測
- **行業新聞** — 按行業分類顯示報告，每天自動收集行業新聞
- **股票歸檔** — 刪除時自動歸檔，保留所有資料，可隨時恢復追蹤
- **事件提醒** — 財報日期、除息日自動追蹤，進入頁面前提醒查看
- **持倉管理** — 記錄持倉數量及成本，即時計算累計損益
- **多語言** — 繁體中文 (預設) / English 雙語切換
- **檔案管理** — 下載報告分類存儲，提供直接下載

## 技術棧

| 組件 | 技術 |
|------|------|
| 後端 | Python Flask |
| 數據庫 | SQLite (核心) + 獨立 SQLite (時序) |
| 前端 | 原生 HTML/CSS/JS + i18n |
| 圖表 | Chart.js |
| PDF | PDF.js |
| 股票數據 | yfinance |
| 財報來源 | SEC EDGAR (10-K / 10-Q) |
| 行業新聞 | Yahoo Finance |
| 分析報告 | yfinance analyst + Yahoo Finance Analysis |
| AI 分析 | OpenAI API |

## 快速開始

### 1. 安裝依賴

```bash
cd ~/repos/Stocker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 啟動

```bash
source .venv/bin/activate
python app.py
```

或使用啟動腳本：

```bash
chmod +x run.sh
./run.sh
```

### 3. 訪問

- 本機: http://localhost:5000
- 區域網絡: http://192.168.31.230:5000

## 每晚自動排程（必須設定）

每晚 20:00 自動執行 `nightly_tasks.py`，依序完成三項任務：

| 順序 | 任務 | 來源 | 說明 |
|------|------|------|------|
| 1 | SEC 財報下載 | SEC EDGAR | 下載追蹤 ticker 的最新 10-K / 10-Q |
| 2 | 行業新聞收集 | Yahoo Finance | 收集各行業板塊新聞及分析 |
| 3 | 金融機構分析報告 | yfinance + Yahoo | 收集分析師評級、目標價、盈利預測 |

### 手動執行

```bash
cd ~/repos/Stocker
source .venv/bin/activate
python nightly_tasks.py
```

### 設定 Cron 排程（必要步驟）

系統依賴 AI Agent 的排程功能來自動執行每晚任務。部署後必須建立以下排程工作：

**排程設定：**
- **時間：** 每天 20:00 (`0 20 * * *`)
- **腳本：** `~/repos/Stocker/nightly_tasks.py`
- **執行方式：** `cd ~/repos/Stocker && source .venv/bin/activate && python nightly_tasks.py`

**AI Agent Prompt（排程任務提示詞）：**

```
執行 Stocker 每晚排程任務。運行 `cd ~/repos/Stocker && source .venv/bin/activate && python nightly_tasks.py`。

這個腳本會依序執行三個任務：
1. SEC 財報 PDF 下載 (10-K / 10-Q)
2. 行業新聞收集 (Yahoo Finance)
3. 金融機構分析報告 (分析師評級 + 預測)

完成後回報每個任務的結果摘要，包括總共收集了多少份新報告，以及各 ticker/行業的分佈。
```

> **注意：** 如果使用 Hermes Agent，可直接建立 cron job：
> ```
> cronjob create --schedule "0 20 * * *" --prompt "上述提示詞"
> ```
> 若使用其他排程系統（如 Linux crontab），直接執行：
> ```
> 0 20 * * * cd ~/repos/Stocker && .venv/bin/python nightly_tasks.py >> /tmp/stocker_nightly.log 2>&1
> ```

## 項目結構

```
Stocker/
├── app.py               # Flask 主應用 (API 路由)
├── models.py            # 核心數據庫操作 (含歸檔機制)
├── tsdb.py              # 時序數據庫操作
├── nightly_tasks.py     # 每晚排程統一入口
├── services/
│   ├── stock_data.py    # yfinance 數據服務
│   ├── report_collector.py  # 報告收集
│   ├── earnings_downloader.py  # SEC EDGAR 財報下載
│   ├── industry_collector.py   # 行業新聞收集
│   ├── analyst_collector.py    # 金融機構分析報告
│   └── ai_analyzer.py   # AI 分析服務
├── static/
│   ├── css/
│   │   ├── style.css    # 深色主題樣式
│   │   └── i18n.css     # 語言切換器樣式
│   └── js/
│       └── i18n.js      # 多語言翻譯系統 (100+ key)
├── templates/
│   ├── base.html        # 基礎模板 (PDF.js + i18n)
│   ├── index.html       # 主頁 (股票+報告+歸檔)
│   ├── stock_detail.html # 股票詳情 (互動圖表)
│   ├── report_detail.html # 報告詳情 (PDF + AI)
│   ├── industry.html    # 行業新聞頁面
│   └── files.html       # 檔案管理
├── data/
│   ├── stocker.db       # 核心數據庫
│   ├── timeseries.db    # 時序數據庫
│   └── files/           # 下載檔案存儲
│       ├── earnings/    # SEC 財報
│       ├── analyst_report/ # 分析師報告
│       ├── news/        # 行業新聞
│       └── sec_filing/  # SEC 文件
├── requirements.txt
└── run.sh
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/tickers` | 所有活躍 ticker 含即時價格 |
| GET | `/api/tickers/stream` | 輕量價格流 (5秒輪詢用) |
| POST | `/api/tickers` | 新增 ticker |
| PUT | `/api/tickers/<symbol>` | 更新持倉/成本 |
| DELETE | `/api/tickers/<symbol>` | 歸檔 ticker (軟刪除) |
| POST | `/api/tickers/<symbol>/restore` | 恢復歸檔的 ticker |
| GET | `/api/tickers/archived` | 所有歸檔的 ticker |
| GET | `/api/stock/<symbol>/detail` | 股票詳細資訊 |
| GET | `/api/stock/<symbol>/chart-data` | 圖表數據 (含技術指標) |
| GET | `/api/sectors` | 所有行業分類 |
| GET | `/api/sectors/<sector>/reports` | 指定行業的報告 |
| GET | `/api/industry/data` | 行業統計數據 |
| GET | `/api/reports` | 報告列表 |
| GET | `/api/reports/<id>` | 報告詳情 |
| GET | `/api/reports/<id>/pdf` | 報告 PDF 檔案 |
| GET | `/api/events/active` | 未處理事件 |
| POST | `/api/events/<id>/dismiss` | 標記事件已知悉 |
| GET | `/api/files` | 檔案列表 |
| GET | `/api/files/<id>/download` | 下載檔案 |

## 初始追蹤清單

TSLA, NVDA, TE, GLW, MRVU, IBM

## 環境變數

| 變數 | 說明 | 必需 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 金鑰 (報告 AI 分析用) | 否 (未設定時使用本地分析) |

## 設計

深色 fintech dashboard 風格：
- 背景: `#0a0a0f`
- 卡片: `#141419`
- 上漲: `#00c853` (綠)
- 下跌: `#ff1744` (紅)
- 強調: `#494fdf` (藍)

## SPEC

完整需求文檔見 [SPEC.md](SPEC.md)
