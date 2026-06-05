# Stocker — AI 美股分析器 SPEC (v2)

## 1. 概覽

Stocker 是一個本地部署的 AI 美股追蹤與分析工具，提供 Web 介面讓用戶管理追蹤清單、查看即時串流行情、收集金融報告並進行 AI 分析。

### 技術棧
- **後端:** Python Flask
- **核心數據庫:** SQLite (tickers, reports, events, files)
- **時序數據庫:** 獨立 SQLite (daily_prices, intraday_ticks) — 分離以提升效能
- **前端:** 原生 HTML/CSS/JS (無框架)
- **圖表:** Chart.js (CDN)
- **PDF Viewer:** PDF.js (CDN)
- **股票數據:** yfinance
- **AI 分析:** OpenAI API
- **設計風格:** 深色 fintech dashboard

### 初始追蹤清單
TSLA, NVDA, TE, GLW, MRVU, IBM

---

## 2. 功能模組

### 2.1 股票追蹤管理
- 新增/刪除追蹤的美股 ticker
- 每個 ticker 自動記錄：名稱、產業、加入日期
- 主頁面以列表顯示所有追蹤中的股票

### 2.2 股票列表主頁 — 即時串流
每個 ticker 顯示：
- **代碼 + 公司名稱**
- **即時價格:** 每 5 秒自動輪詢更新 ($及漲跌幅)
- **T-1 昨日表現:** 昨收價、漲跌幅(%)
- **一周走勢圖:** 極簡迷你折線圖 (7天)
- **持倉數量 + 總價:** 用戶手動設定
- **累計損益總額:** (現價 - 成本) × 持倉
- **累計損益比例:** 損益 / (成本 × 持倉) × 100%

### 2.3 股票詳情頁 — 互動圖表
- **大型走勢圖:** 可切換 1M/3M/6M/1Y
- **可選技術指標面板:**
  - MA 線: MA5 / MA20 / MA60 (可個別開關)
  - RSI 14
  - MACD (12/26/9)
  - 交易量副圖 (Volume bars，紅綠配色)
- **基本面資訊:** 市值、PE ratio、EPS、52周高低
- **最近新聞:** 標題 + 來源 + 日期
- **下一次財報日期:** 顯眼提醒標記
- **用戶備註:** dismiss 機制

### 2.4 事件提醒系統
- 追蹤每個 ticker 的下一次 earnings date
- 已知的未來事件在頁面頂部 banner 提醒
- 用戶可標記「已知悉」(dismissed)
- 每次進入詳情頁如未查看仍會提醒
- 提醒類型：財報發布、除息日

### 2.5 金融報告系統 — PDF + AI 聯動 ⭐
- **報告收集:** 定期從公開來源抓取金融機構報告 (PDF)
- **AI 摘要:** 每份報告生成 ~50字中文摘要
- **AI 分析結構化:** 分析結果包含多個標題 + 內容段落
- **報告列表:** 顯示摘要、來源、日期、關聯 ticker
- **報告詳情頁 (核心功能):**
  - **左側:** PDF.js 嵌入式 PDF viewer，支援滾動及頁面導航
  - **右側:** AI 綜合分析，每點為可折疊標題+內容
  - **聯動:** 點擊右側分析標題 → 左側 PDF 自動跳轉到對應頁碼及位置
  - AI 分析時記錄每個要點對應的 PDF 頁碼

### 2.6 檔案管理
- 按分類存放下載的報告 PDF/文件
- 檔案列表顯示：檔名、分類、大小、日期
- 提供直接下載按鈕
- 分類：earnings, analyst_report, news, sec_filing

---

## 3. 數據庫設計

### 3.1 核心數據庫 (stocker.db)

#### `tickers` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| symbol | TEXT UNIQUE | 股票代碼 |
| name | TEXT | 公司名稱 |
| sector | TEXT | 產業 |
| shares_held | REAL | 持倉數量 |
| cost_basis | REAL | 成本價 |
| added_at | DATETIME | 加入時間 |

#### `reports` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| title | TEXT | 報告標題 |
| source | TEXT | 來源 |
| url | TEXT | 原文連結 |
| summary | TEXT | AI 摘要 (~50字) |
| analysis | TEXT | AI 分析 (JSON: [{title, content, page}]) |
| content | TEXT | 原文內容 |
| file_path | TEXT | 本地 PDF 檔案路徑 |
| category | TEXT | 分類 |
| published_at | DATETIME | 發布時間 |
| created_at | DATETIME | 收集時間 |

#### `events` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| ticker_id | INTEGER FK | 關聯 ticker |
| event_type | TEXT | earnings/dividend |
| event_date | DATE | 事件日期 |
| title | TEXT | 事件描述 |
| dismissed | BOOLEAN | 是否已知悉 |
| dismissed_at | DATETIME | 知悉時間 |

#### `files` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| filename | TEXT | 檔案名 |
| category | TEXT | 分類 |
| file_path | TEXT | 儲存路徑 |
| file_size | INTEGER | 檔案大小 |
| report_id | INTEGER FK | 關聯報告 |
| created_at | DATETIME | 建立時間 |

### 3.2 時序數據庫 (timeseries.db) — 獨立檔案

#### `daily_prices` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| ticker_id | INTEGER | 關聯 ticker ID |
| date | TEXT | YYYY-MM-DD |
| open | REAL | 開盤價 |
| high | REAL | 最高 |
| low | REAL | 最低 |
| close | REAL | 收盤 |
| volume | INTEGER | 成交量 |
| UNIQUE(ticker_id, date) | | |

#### `intraday_ticks` 表 (即時價格快取)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| ticker_id | INTEGER | 關聯 ticker ID |
| timestamp | TEXT | ISO timestamp |
| price | REAL | 即時價格 |
| volume | INTEGER | 成交量 |

---

## 4. API 路由設計

### 頁面路由
- `GET /` — 主頁 (股票列表 + 報告列表 tabs)
- `GET /stock/<symbol>` — 股票詳情頁
- `GET /report/<id>` — 報告詳情頁 (PDF + AI split view)
- `GET /files` — 檔案管理頁面

### API 路由 (JSON)
- `GET /api/tickers` — 取得所有追蹤 ticker (含即時價格)
- `POST /api/tickers` — 新增 ticker
- `DELETE /api/tickers/<symbol>` — 刪除 ticker
- `PUT /api/tickers/<symbol>` — 更新持倉/成本
- `GET /api/tickers/stream` — **即時價格流** (每5秒輪詢端點)
- `GET /api/stock/<symbol>/detail` — 取得詳細資訊
- `GET /api/stock/<symbol>/chart-data?range=...&indicators=...` — 圖表數據
- `POST /api/stock/<symbol>/refresh` — 強制刷新數據
- `GET /api/reports` — 取得報告列表
- `POST /api/reports/collect` — 觸發報告收集
- `GET /api/reports/<id>` — 取得報告詳情 (含 PDF 路徑)
- `GET /api/reports/<id>/pdf` — **取得報告 PDF 檔案**
- `POST /api/events/<id>/dismiss` — 標記事件已知悉
- `GET /api/events/active` — 取得未處理事件
- `GET /api/files` — 取得檔案列表
- `GET /api/files/<id>/download` — 下載檔案

---

## 5. 頁面設計

### 5.1 主頁面 — 即時串流
```
┌─────────────────────────────────────────────────────┐
│  Stocker            [股票] [報告] [檔案]       [+新增] │
├─────────────────────────────────────────────────────┤
│ ⚠️ 提醒 banner (如有未處理事件)                         │
├─────────────────────────────────────────────────────┤
│ ┌─────────┬────────┬────────┬─────┬───────┬────────┐ │
│ │ Ticker  │ 即時價  │ T-1    │ 持倉│ 損益  │ 週圖   │ │
│ ├─────────┼────────┼────────┼─────┼───────┼────────┤ │
│ │ TSLA    │$419.20 │$423.70 │ 100 │+$1234 │ ~~~    │ │
│ │         │ -1.06% │        │     │ +5.2% │        │ │
│ │ NVDA    │$218.50 │$214.80 │ 50  │+$890  │ ~~~    │ │
│ │         │ +1.72% │        │     │ +3.1% │        │ │
│ └─────────┴────────┴────────┴─────┴───────┴────────┘ │
│  (每 5 秒自動更新價格，無需刷新頁面)                     │
│                                                       │
│ [報告 tab]                                            │
│ ┌────────────────────────────────────────────────┐   │
│ │ 📄 報告標題... AI摘要五十字... 來源  2026-06-05 │   │
│ └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 5.2 股票詳情頁 — 互動圖表
```
┌─────────────────────────────────────────────────────┐
│ ← 返回   TSLA - Tesla Inc.           ⚠️ 財報 06/20   │
├─────────────────────────────────────────────────────┤
│ [1M] [3M] [6M] [1Y]   指標: ☑MA ☑RSI ☑MACD ☑Volume │
│ ┌─────────────────────────────────────────────────┐  │
│ │          大型走勢圖 (含可選指標)                   │  │
│ │  ──── MA5  ──── MA20  ──── MA60                │  │
│ ├─────────────────────────────────────────────────┤  │
│ │ ▊▊ ▊  ▊▊▊  ▊  ▊▊▊▊ ▊▊  ▊▊ (交易量副圖)        │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─────────────┬──────────────┬──────────────┐        │
│ │ 市值 $xxx   │ PE: xx.xx    │ 52W: $xx-$xx │        │
│ │ EPS: $x.xx  │ 分析師評級    │ 除息日: xx   │        │
│ └─────────────┴──────────────┴──────────────┘        │
│ 最近新聞                                              │
│ • 新聞標題1                                2026-06-05 │
│ [已知悉] 持倉: [___] 成本: [___] [保存]                │
└─────────────────────────────────────────────────────┘
```

### 5.3 報告詳情頁 — PDF + AI 聯動 ⭐
```
┌─────────────────────────────────────────────────────┐
│ ← 返回   報告標題                            2026-06 │
├────────────────────────┬────────────────────────────┤
│    PDF Viewer (左側)    │    AI 分析 (右側)            │
│                        │                            │
│  ┌──────────────────┐  │  ▶ 1. 整體市場影響評估       │
│  │                  │  │    內容... (點擊→PDF跳p.3)  │
│  │  [PDF 原文]      │  │                            │
│  │  支援滾動/翻頁   │  │  ▶ 2. 關聯股票分析          │
│  │                  │  │    TSLA, NVDA...           │
│  │                  │  │                            │
│  │                  │  │  ▶ 3. 關鍵財務數據          │
│  │                  │  │    營收增長...              │
│  │                  │  │                            │
│  │                  │  │  ▶ 4. 投資建議要點          │
│  │                  │  │    建議買入...              │
│  └──────────────────┘  │                            │
│  [◀ 上一頁] [3/12] [下一頁 ▶] │                       │
└────────────────────────┴────────────────────────────┘
```

---

## 6. 數據更新策略

- **即時價格:** 前端每 5 秒輪詢 `/api/tickers/stream`，後端從 yfinance 取最新價
- **歷史數據:** 每日首次訪問時更新，存入時序數據庫
- **新聞/事件:** 每次訪問詳情頁時更新
- **報告收集:** 手動觸發或 cron 定時 (每 3 小時)
- **AI 分析:** 收集到新報告後自動觸發，結構化為標題+內容+頁碼

---

## 7. 檔案結構

```
Stocker/
├── SPEC.md
├── app.py              # Flask 主應用
├── models.py           # 核心數據庫 models
├── tsdb.py             # 時序數據庫操作
├── services/
│   ├── stock_data.py   # yfinance 數據服務
│   ├── report_collector.py  # 報告收集
│   └── ai_analyzer.py  # AI 分析服務
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js      # 主應用邏輯 + 5秒輪詢
│       ├── charts.js   # 圖表 + 指標 + Volume
│       └── detail.js   # 詳情頁邏輯
├── templates/
│   ├── base.html       # 基礎模板 (PDF.js CDN)
│   ├── index.html      # 主頁
│   ├── stock_detail.html
│   ├── report_detail.html  # PDF viewer + AI 聯動
│   └── files.html
├── data/
│   ├── stocker.db      # 核心 SQLite
│   ├── timeseries.db   # 時序 SQLite (分離)
│   └── files/          # 檔案儲存
├── requirements.txt
└── run.sh
```

---

## 8. 設計規範

- **主題:** 深色背景 (#0a0a0f)，卡片 (#141419)
- **強調色:** 綠色上漲 (#00c853)，紅色下跌 (#ff1744)
- **字體:** Inter (Google Fonts)
- **按鈕:** 圓角藥丸形 (9999px radius)
- **卡片:** 12px 圓角，無陰影
- **即時更新:** 綠色閃爍動畫表示價格上漲，紅色閃爍表示下跌
