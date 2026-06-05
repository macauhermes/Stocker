# Stocker — AI 美股分析器

本地部署的美股追蹤與分析工具，提供即時串流行情、互動圖表、金融報告 PDF 閱讀及 AI 智能分析。

## 功能

- **即時行情追蹤** — 每 5 秒自動更新價格，支援多支美股同時監控
- **互動圖表** — 支援 MA/RSI/MACD/Volume 等技術指標，可個別開關顯示
- **金融報告** — 自動從 SEC EDGAR 下載 10-K / 10-Q 財報，PDF 原文閱讀 + AI 分析聯動
- **行業新聞** — 按行業分類顯示報告，每天自動收集行業新聞
- **股票歸檔** — 刪除時自動歸檔，保留所有資料，可隨時恢復追蹤
- **事件提醒** — 財報日期、除息日自動追蹤，進入頁面前提醒查看
- **持倉管理** — 記錄持倉數量及成本，即時計算累計損益
- **檔案管理** — 下載報告分類存儲，提供直接下載

## 技術棧

| 組件 | 技術 |
|------|------|
| 後端 | Python Flask |
| 數據庫 | SQLite (核心) + 獨立 SQLite (時序) |
| 前端 | 原生 HTML/CSS/JS |
| 圖表 | Chart.js |
| PDF | PDF.js |
| 股票數據 | yfinance |
| 財報來源 | SEC EDGAR |
| 行業新聞 | Yahoo Finance |
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

## 項目結構

```
Stocker/
├── app.py               # Flask 主應用 (API 路由)
├── models.py            # 核心數據庫操作 (含歸檔機制)
├── tsdb.py              # 時序數據庫操作
├── services/
│   ├── stock_data.py    # yfinance 數據服務
│   ├── report_collector.py  # 報告收集
│   ├── earnings_downloader.py  # SEC EDGAR 財報下載
│   ├── industry_collector.py   # 行業新聞收集
│   └── ai_analyzer.py   # AI 分析服務
├── static/css/style.css # 深色主題樣式
├── templates/           # HTML 模板
│   ├── base.html        # 基礎模板
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
│       ├── analyst_report/
│       ├── news/        # 行業新聞
│       └── sec_filing/
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

## 自動化排程

| 時間 | 任務 | 說明 |
|------|------|------|
| 每天 20:00 | SEC 財報下載 | 下載所有追蹤 ticker 的最新 10-K / 10-Q |
| 每天 20:00 | 行業新聞收集 | 從 Yahoo Finance 收集各行業新聞 |
| 每 5 秒 | 即時價格更新 | 前端輪詢更新價格顯示 |

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

## 功能詳情

### 股票歸檔
- 刪除觀察中的股票時自動歸檔（軟刪除）
- 歸檔後停止追蹤新聞及財報，但保留所有已下載資料
- 可隨時從「歸檔」頁籤恢復追蹤
- 重新新增相同 ticker 自動恢復，保留持倉記錄

### 行業分類與新聞
- 每個追蹤中的 ticker 自動從 yfinance 取得行業分類
- 獨立行業新聞頁面，按行業分類顯示報告
- 行業卡片顯示每個行業的 ticker 數量及報告數量
- 每天晚上 8:00 自動收集行業新聞

### SEC 財報下載
- 自動從 SEC EDGAR 下載最新的 10-K (年報) 和 10-Q (季報)
- 支援 HTML 及 PDF 格式
- 每天晚上 8:00 自動執行
- 下載後自動記錄到數據庫

## SPEC

完整需求文檔見 [SPEC.md](SPEC.md)
