# Stocker — 美股追蹤工具 SPEC

## 1. 概覽

Stocker 是一個本地部署的美股追蹤與分析工具，提供 Web 介面讓用戶管理追蹤清單、查看即時行情、收集金融報告並進行 AI 分析。

### 技術棧
- **後端:** Python Flask
- **數據庫:** SQLite (本地)
- **前端:** 原生 HTML/CSS/JS (無框架，單頁應用風格)
- **圖表:** Chart.js (CDN)
- **股票數據:** yfinance
- **AI 分析:** OpenAI API (報告摘要/分析)
- **設計風格:** 深色 fintech dashboard (Revolut 風格)

### 初始追蹤清單
TSLA, NVDA, TE, GLW, MRVU, IBM

---

## 2. 功能模組

### 2.1 股票追蹤管理 (Ticker Management)
- 新增/刪除追蹤的美股 ticker
- 每個 ticker 自動記錄：名稱、產業、加入日期
- 主頁面以卡片/列表顯示所有追蹤中的股票

### 2.2 股票列表主頁 (Stock Dashboard)
每個 ticker 顯示：
- **代碼 + 公司名稱**
- **T+0 當日表現:** 當前價格、漲跌幅(%)
- **T-1 昨日表現:** 收盤價、漲跌幅(%)
- **一周走勢圖:** 極簡迷你折線圖 (7天)
- **持倉數量:** 用戶手動設定
- **累計損益總額:** (現價 - 成本) × 持倉
- **累計損益比例:** 損益 / (成本 × 持倉) × 100%

### 2.3 股票詳情頁 (Stock Detail)
- **大型走勢圖:** 可切換 1M/3M/6M/1Y 時間範圍
- **技術指標:** MA5/MA20/MA60, RSI, MACD
- **基本面資訊:** 市值、PE ratio、EPS、52周高低
- **最近新聞:** 標題 + 來源 + 日期 (從 yfinance 或 web scraping)
- **下一次財報日期:** 顯眼提醒標記
- **用戶備註:** 可記錄是否已查看詳情 (dismiss 機制)

### 2.4 事件提醒系統 (Event Reminders)
- 追蹤每個 ticker 的下一次 earnings date
- 已知的未來事件在頁面頂部 banner 提醒
- 用戶可標記「已知悉」(dismissed)，但每次進入詳情頁如未查看仍會提醒
- 提醒類型：財報發布、除息日

### 2.5 金融報告系統 (Reports)
- **報告收集:** 定期從公開來源抓取金融機構報告
- **AI 摘要:** 每份報告生成 ~50字中文摘要
- **AI 分析:** 對報告內容進行深度分析 (影響評級、關聯股票、關鍵數據)
- **報告列表:** 顯示摘要、來源、日期、關聯 ticker
- **報告詳情頁:** 左半邊原文，右半邊 AI 分析結果 (split view)

### 2.6 檔案管理 (File Manager)
- 按分類存放下載的報告 PDF/文件
- 檔案列表顯示：檔名、分類、大小、日期
- 提供直接下載按鈕
- 分類：earnings, analyst_report, news, sec_filing

---

## 3. 數據庫設計 (SQLite)

### `tickers` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| symbol | TEXT UNIQUE | 股票代碼 |
| name | TEXT | 公司名稱 |
| sector | TEXT | 產業 |
| shares_held | REAL | 持倉數量 |
| cost_basis | REAL | 成本價 |
| added_at | DATETIME | 加入時間 |

### `daily_prices` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| ticker_id | INTEGER FK | 關聯 ticker |
| date | DATE | 日期 |
| open | REAL | 開盤價 |
| high | REAL | 最高 |
| low | REAL | 最低 |
| close | REAL | 收盤 |
| volume | INTEGER | 成交量 |

### `reports` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| title | TEXT | 報告標題 |
| source | TEXT | 來源 |
| url | TEXT | 原文連結 |
| summary | TEXT | AI 摘要 (~50字) |
| analysis | TEXT | AI 分析 |
| content | TEXT | 原文內容 |
| file_path | TEXT | 本地檔案路徑 |
| category | TEXT | 分類 |
| published_at | DATETIME | 發布時間 |
| created_at | DATETIME | 收集時間 |

### `events` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| ticker_id | INTEGER FK | 關聯 ticker |
| event_type | TEXT | earnings/dividend |
| event_date | DATE | 事件日期 |
| title | TEXT | 事件描述 |
| dismissed | BOOLEAN | 是否已知悉 |
| dismissed_at | DATETIME | 知悉時間 |

### `files` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| filename | TEXT | 檔案名 |
| category | TEXT | 分類 |
| file_path | TEXT | 儲存路徑 |
| file_size | INTEGER | 檔案大小 |
| report_id | INTEGER FK | 關聯報告 |
| created_at | DATETIME | 建立時間 |

---

## 4. API 路由設計

### 頁面路由
- `GET /` — 主頁 (股票列表 + 報告列表 tabs)
- `GET /stock/<symbol>` — 股票詳情頁
- `GET /report/<id>` — 報告詳情頁 (split view)
- `GET /files` — 檔案管理頁面

### API 路由 (JSON)
- `GET /api/tickers` — 取得所有追蹤 ticker
- `POST /api/tickers` — 新增 ticker
- `DELETE /api/tickers/<symbol>` — 刪除 ticker
- `PUT /api/tickers/<symbol>` — 更新持倉/成本
- `GET /api/stock/<symbol>/prices?range=1m|3m|6m|1y` — 取得歷史價格
- `GET /api/stock/<symbol>/detail` — 取得詳細資訊 (基本面+新聞+事件)
- `GET /api/stock/<symbol>/chart-data` — 圖表數據 (含技術指標)
- `POST /api/stock/<symbol>/refresh` — 強制刷新數據
- `GET /api/reports` — 取得報告列表
- `POST /api/reports/collect` — 觸發報告收集
- `GET /api/reports/<id>` — 取得報告詳情
- `POST /api/events/<id>/dismiss` — 標記事件已知悉
- `GET /api/events/active` — 取得未處理事件
- `GET /api/files` — 取得檔案列表
- `GET /api/files/<id>/download` — 下載檔案

---

## 5. 頁面設計

### 5.1 主頁面
```
┌─────────────────────────────────────────────┐
│  Stocker        [股票] [報告] [檔案]    [+新增] │
├─────────────────────────────────────────────┤
│ ⚠️ 提醒 banner (如有未處理事件)                 │
├─────────────────────────────────────────────┤
│ ┌─────────┬──────┬──────┬─────┬──────┬─────┐ │
│ │ Ticker  │ 現價 │ 漲跌 │ 持倉│ 損益 │ 迷你圖│ │
│ ├─────────┼──────┼──────┼─────┼──────┼─────┤ │
│ │ TSLA    │ $xxx │ +x%  │ 100 │+$xxx │ ~~~ │ │
│ │ NVDA    │ $xxx │ -x%  │ 50  │-$xxx │ ~~~ │ │
│ └─────────┴──────┴──────┴─────┴──────┴─────┘ │
│                                              │
│ [報告 tab]                                    │
│ ┌──────────────────────────────────────────┐ │
│ │ 📄 報告標題...  AI摘要五十字...  2026-06-05│ │
│ │ 📄 報告標題...  AI摘要五十字...  2026-06-04│ │
│ └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 5.2 股票詳情頁
```
┌─────────────────────────────────────────────┐
│ ← 返回   TSLA - Tesla Inc.    ⚠️ 財報 06/20   │
├─────────────────────────────────────────────┤
│ [1M] [3M] [6M] [1Y]                          │
│ ┌─────────────────────────────────────────┐  │
│ │          大型走勢圖 + MA線               │  │
│ └─────────────────────────────────────────┘  │
│ ┌─────────────┬──────────────┬──────────────┐│
│ │ 市值 $xxx   │ PE: xx.xx    │ 52W: $xx-$xx ││
│ │ EPS: $x.xx  │ 分析師評級    │ 除息日: xx   ││
│ └─────────────┴──────────────┴──────────────┘│
│ 最近新聞                                      │
│ • 新聞標題1                        2026-06-05 │
│ • 新聞標題2                        2026-06-04 │
│ [已知悉] 持倉: [___] 成本: [___] [保存]        │
└─────────────────────────────────────────────┘
```

### 5.3 報告詳情頁 (Split View)
```
┌─────────────────────────────────────────────┐
│ ← 返回   報告標題                    2026-06-05│
├──────────────────┬──────────────────────────┤
│     原文內容      │      AI 綜合分析           │
│                  │                          │
│ (左側滾動)       │  • 影響評級: 正面          │
│                  │  • 關聯股票: TSLA, NVDA    │
│                  │  • 關鍵數據摘要            │
│                  │  • 投資建議要點            │
└──────────────────┴──────────────────────────┘
```

---

## 6. 數據更新策略

- **股票行情:** 每次訪問頁面時從 yfinance 拉取最新數據 (帶 cache)
- **歷史數據:** 每日首次訪問時更新，存入 SQLite
- **新聞/事件:** 每次訪問詳情頁時更新
- **報告收集:** 手動觸發或 cron 定時 (每 3 小時)
- **AI 分析:** 收集到新報告後自動觸發

---

## 7. 檔案結構

```
Stocker/
├── SPEC.md
├── app.py              # Flask 主應用
├── models.py           # 數據庫 models
├── services/
│   ├── stock_data.py   # yfinance 數據服務
│   ├── report_collector.py  # 報告收集
│   └── ai_analyzer.py  # AI 分析服務
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js      # 主應用邏輯
│       ├── charts.js   # 圖表相關
│       └── detail.js   # 詳情頁邏輯
├── templates/
│   ├── base.html       # 基礎模板
│   ├── index.html      # 主頁
│   ├── stock_detail.html
│   ├── report_detail.html
│   └── files.html
├── data/
│   ├── stocker.db      # SQLite 數據庫
│   └── files/          # 檔案儲存
│       ├── earnings/
│       ├── analyst_report/
│       ├── news/
│       └── sec_filing/
├── requirements.txt
└── run.sh              # 啟動腳本
```

---

## 8. 設計規範

- **主題:** 深色背景 (#0a0a0f)，卡片 (#141419)
- **強調色:** 綠色上漲 (#00c853)，紅色下跌 (#ff1744)
- **字體:** Inter (Google Fonts)
- **按鈕:** 圓角藥丸形 (9999px radius)
- **卡片:** 12px 圓角，無陰影
- **響應式:** 支援桌面及平板
