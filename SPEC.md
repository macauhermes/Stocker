# Stocker — AI 美股分析器 SPEC (v3.2)

## 1. 概覽

Stocker 是一個本地部署的 AI 美股追蹤與分析工具，提供 Web 介面讓用戶管理追蹤清單、查看即時串流行情、收集金融報告並進行 AI 分析。

### 技術棧
- **後端:** Python Flask
- **核心數據庫:** SQLite (tickers, reports, events, files)
- **時序數據庫:** 獨立 SQLite (daily_prices, intraday_ticks) — 分離以提升效能
- **前端:** 原生 HTML/CSS/JS (無框架)
- **圖表:** Chart.js + chartjs-plugin-zoom (CDN) — 觸控手勢 + 十字線 + zoom/pan
- **PDF Viewer:** PDF.js (CDN)
- **股票數據:** 多源備援鏈（見 §2.10）— yfinance 主 → Yahoo 直接 → Stooq → CoinGecko → 自訂 JSONPath
- **財報來源:** SEC EDGAR (10-K / 10-Q) + SpaceX-style S-1/424B4
- **行業新聞:** Yahoo Finance 行業頁面
- **分析報告:** yfinance analyst + Yahoo Finance Analysis
- **AI 分析:** OpenAI API
- **設計風格:** 深色 fintech dashboard, mobile-first 320px 適配

### 初始追蹤清單
TSLA, NVDA, TE, GLW, MRVU, IBM

---

## 2. 功能模組

### 2.1 股票追蹤管理 — 歸檔機制
- 新增追蹤的美股 ticker
- **歸檔（軟刪除）：** 刪除時自動歸檔，停止追蹤新聞及財報，但保留所有已下載資料
- **歸檔區域：** 主頁「歸檔」頁籤顯示所有已歸檔的 ticker
- **一鍵恢復：** 從歸檔區域恢復追蹤，保留持倉記錄及歷史資料
- **自動恢復：** 重新新增相同 ticker 時自動恢復，保留 shares_held 和 cost_basis
- 每個 ticker 自動記錄：名稱、產業（yfinance 自動分類）、加入日期

### 2.2 行業分類與行業新聞
- 每個追蹤中的 ticker 自動從 yfinance 取得行業分類 (sector)
- **行業新聞頁面：** 獨立 `/industry` 頁面，按行業分類顯示報告
- **行業卡片：** 顯示每個行業的 ticker 數量及報告數量
- **行業篩選：** 點擊行業卡片查看該行業的所有相關報告
- **報告篩選：** 主頁報告標籤可按行業 pill 按鈕篩選

### 2.3 股票列表主頁 — 即時串流
每個 ticker 顯示：
- **代碼 + 公司名稱 + 行業標籤**
- **即時價格:** 每 5 秒自動輪詢更新 ($及漲跌幅)
- **T-1 昨日表現:** 昨收價、漲跌幅(%)
- **一周走勢圖:** 極簡迷你折線圖 (7天)
- **持倉數量 + 總價:** 用戶手動設定
- **累計損益總額:** (現價 - 成本) × 持倉
- **累計損益比例:** 損益 / (成本 × 持倉) × 100%
- **歸檔按鈕：** 每列末尾的「歸檔」按鈕

### 2.4 股票詳情頁 — 互動圖表
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

### 2.5 事件提醒系統
- 追蹤每個 ticker 的下一次 earnings date
- 已知的未來事件在頁面頂部 banner 提醒
- 用戶可標記「已知悉」(dismissed)
- 每次進入詳情頁如未查看仍會提醒
- 提醒類型：財報發布、除息日、**價格提醒 (v3.4)** — 用戶自訂閾值，價格觸發時自動記一筆 event_type='price_alert' 並自動 disable，需手動 rearm 才會再觸發

### 2.6 金融報告系統 — PDF + AI 聯動
- **報告收集:** 定期從公開來源抓取金融機構報告
- **SEC EDGAR 財報下載:** 自動下載最新的 10-K / 10-Q 財報 PDF/HTML
- **金融機構分析報告:** 收集各大銀行及投行的分析師評級及預測
- **AI 摘要:** 每份報告生成 ~50字中文摘要
- **AI 分析結構化:** 分析結果包含多個標題 + 內容段落
- **報告列表:** 顯示摘要、來源、日期、關聯 ticker
- **報告詳情頁 (核心功能):**
  - **左側:** PDF.js 嵌入式 PDF viewer，支援滾動及頁面導航
  - **右側:** AI 綜合分析，每點為可折疊標題+內容
  - **聯動:** 點擊右側分析標題 → 左側 PDF 自動跳轉到對應頁碼及位置
  - AI 分析時記錄每個要點對應的 PDF 頁碼

### 2.7 檔案管理
- 按分類存放下載的報告 PDF/文件
- 檔案列表顯示：檔名、分類、大小、日期
- 提供直接下載按鈕
- 分類：earnings, analyst_report, news, sec_filing, industry

### 2.8 多語言支援
- **繁體中文 (預設)** / English 雙語切換
- 導航欄語言切換按鈕 (中/EN)
- 所有頁面文字支援 data-i18n 屬性
- 語言偏好保存在 localStorage
- 動態內容切換語言時自動重新渲染

### 2.9 手機 UI 優化 (v3.2)
- **320px 安全區:** 確保窄屏幕無水平滾動
- **44px 觸控目標:** Apple HIG 標準，所有按鈕/連結 min-height: 44px
- **卡片式列表:** 取代傳統表格，便於滑動操作
- **底部 Tab 導航:** 主頁/行業/投行/數據源/檔案
- **FAB 浮動按鈕:** 主頁右下角「+」直接打開新增股票
- **智能更新 badge:** 頂部顯示「盤中/盤後/週末 + 間隔秒數」

### 2.10 多源數據備援鏈 (v3.2, wealthlens-style)

借鏡 wealthlens 設計，每類數據有主源、備源、最後手段，單一服務故障不影響平台：

| 數據 | 主源 | 備援 1 | 備援 2 | 備援 3 | 最後手段 |
|------|------|--------|--------|--------|----------|
| 美股歷史價 | yfinance | Yahoo Finance 直接 API | Stooq | — | — |
| 港股/A股/日股 | Yahoo 直接 | yfinance | Stooq | — | — |
| 加密貨幣 (BTC-USD 等) | Yahoo 直接 | CoinGecko | yfinance | — | — |
| 自訂基金/債券 | **DB-stored JSONPath** | — | — | — | — |

**自訂 JSONPath 數據源:**
- `GET /api/sources` 列出 / `POST` 新增 / `PUT /:id` 編輯 / `DELETE /:id` 刪除
- 每個源支援：`url`（含 `{symbol}` placeholder）+ `date_path` + `price_path` + 可選 `open_path`/`high_path`/`low_path`/`volume_path`/`symbol_match`
- JSONPath 子集支援：`$.a.b.c`、`$.a[0].b`、`$.a[*].b`、`$['key with spaces']`
- 日期格式自動偵測：ISO、Unix 秒/毫秒、MM/DD/YYYY
- 啟用狀態（`enabled=0/1`）+ 優先級（`priority`）控制載入順序
- 自訂源在歷史價解析鏈中優先於 Yahoo

### 2.11 智能更新頻率 + 即時推送 (v3.2)

**智能輪詢頻率** (wealthlens-style):
- 美股盤中（週一至五 09:30-16:00 ET）→ **3 秒**
- 美股盤後（04:00-20:00 ET）→ **15 秒**
- 平日收盤後 → **60 秒**
- 週末/假日 → **300 秒（5 分鐘）**
- `GET /api/refresh-interval` 返回當前建議間隔 + 原因

**SSE 即時推送:**
- `GET /api/stream/tickers` 為 Server-Sent Events 端點
- 按智能頻率推送所有追蹤股票的當前快照
- 前端可選擇用 polling 或 SSE client 訂閱

### 2.12 股票搜索 + 預覽 (v3.2)

- **Autocomplete:** 輸入框 200ms debounce → `GET /api/search?q=`
- 內置 33 個熱門股 (US + HK + CN + JP + TW + Crypto) 即時匹配（無網絡）
- Yahoo Finance search API 補完冷門股
- **預覽卡片:** 500ms debounce → `POST /api/tickers/preview` 顯示股名/即時價/漲跌幅/PE/EPS/市值/行業
- 點擊建議項自動填入並重新預覽
- 支援多市場推斷：`.HK` / `.SS` / `.SZ` / `.T` / `.TW` / `-USD` → US/HK/CN/JP/TW/CRYPTO

### 2.13 SEC 文件 (v3.2)

- `sec_filing` category 收納 S-1 / 424B4 / 8-A12B / FWP / CERT 等
- 上市前公司（如 SpaceX SPCX）無 10-K/10-Q 時，招股書即主要財務來源
- 已內建 SPCX 7 份招股書 (424B4/S-1/EU Prospectus/FWP/8-A12B/Listing Cert)

---

## 3. 數據庫設計

### 3.1 核心數據庫 (stocker.db)

#### `tickers` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| symbol | TEXT UNIQUE | 股票代碼 |
| name | TEXT | 公司名稱 |
| sector | TEXT | 產業 (yfinance 自動分類) |
| shares_held | REAL | 持倉數量 |
| cost_basis | REAL | 成本價 |
| added_at | DATETIME | 加入時間 |
| archived | INTEGER | 是否歸檔 (0=活躍, 1=歸檔) |
| archived_at | DATETIME | 歸檔時間 |

#### `reports` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| title | TEXT | 報告標題 |
| source | TEXT | 來源 (SEC EDGAR, Industry News, Analyst 等) |
| url | TEXT | 原文連結 |
| summary | TEXT | AI 摘要 (~50字) |
| analysis | TEXT | AI 分析 (JSON: [{title, content, page}]) |
| content | TEXT | 原文內容 |
| file_path | TEXT | 本地 PDF/HTML 檔案路徑 |
| category | TEXT | 分類 (earnings, news, analyst_report, industry, sec_filing) |
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

#### `custom_data_sources` 表 (v3.2)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 源名稱 |
| url | TEXT | API URL（含 `{symbol}` placeholder） |
| date_path | TEXT | JSONPath 取日期 |
| price_path | TEXT | JSONPath 取收盤價 |
| open_path | TEXT | JSONPath 取開盤價（可選） |
| high_path | TEXT | JSONPath 取最高（可選） |
| low_path | TEXT | JSONPath 取最低（可選） |
| volume_path | TEXT | JSONPath 取成交量（可選） |
| symbol_match | TEXT | JSONPath 過濾特定 symbol（可選） |
| priority | INTEGER | 載入順序（數字愈小愈先） |
| enabled | INTEGER | 啟用 0/1 |
| notes | TEXT | 備註 |
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
- `GET /` — 主頁 (股票列表 + 報告列表 + 歸檔 tabs)
- `GET /stock/<symbol>` — 股票詳情頁
- `GET /report/<id>` — 報告詳情頁 (PDF + AI split view)
- `GET /industry` — 行業新聞頁面
- `GET /files` — 檔案管理頁面

### API 路由 (JSON)
- `GET /api/tickers` — 取得所有活躍 ticker (含即時價格)
- `POST /api/tickers` — 新增 ticker (已歸檔的自動恢復)
- `DELETE /api/tickers/<symbol>` — **歸檔** ticker (軟刪除)
- `POST /api/tickers/<symbol>/restore` — **恢復**歸檔的 ticker
- `GET /api/tickers/archived` — 取得所有歸檔的 ticker
- `PUT /api/tickers/<symbol>` — 更新持倉/成本
- `GET /api/tickers/stream` — **即時價格流** (每5秒輪詢端點)
- `GET /api/stock/<symbol>/detail` — 取得詳細資訊
- `GET /api/stock/<symbol>/chart-data?range=...&indicators=...` — 圖表數據
- `POST /api/stock/<symbol>/refresh` — 強制刷新數據
- `GET /api/sectors` — 取得所有行業分類
- `GET /api/sectors/<sector>/reports` — 取得指定行業的報告
- `GET /api/industry/data` — 行業統計數據 (ticker數+報告數)
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

### 5.1 主頁面 — 即時串流 + 歸檔 + 多語言
```
┌─────────────────────────────────────────────────────────┐
│  Stocker     [主頁] [行業] [檔案]              [中] [EN] │
├─────────────────────────────────────────────────────────┤
│ ⚠️ 提醒 banner (如有未處理事件)                             │
├─────────────────────────────────────────────────────────┤
│ [股票 tab]                                               │
│ ┌─────────┬────────┬────────┬─────┬───────┬──────┬────┐ │
│ │ Ticker  │ 即時價  │ 漲跌%  │ 持倉│ 損益  │ 週圖 │ 歸檔│ │
│ ├─────────┼────────┼────────┼─────┼───────┼──────┼────┤ │
│ │ TSLA    │$419.20 │ -1.06% │ 100 │+$1234 │ ~~~  │ 🗑 │ │
│ │ Tech    │        │        │     │ +5.2% │      │    │ │
│ └─────────┴────────┴────────┴─────┴───────┴──────┴────┘ │
│                                                          │
│ [報告 tab]  篩選: [全部] [Technology] [Consumer] [金融]    │
│ ┌────────────────────────────────────────────────────┐  │
│ │ 📄 報告標題... AI摘要五十字... 來源  2026-06-05     │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ [歸檔 tab]                                               │
│ ┌─────────┬──────────────┬──────────┬──────────┬──────┐ │
│ │ Symbol  │ Name         │ Sector   │ 歸檔日期 │ 操作 │ │
│ ├─────────┼──────────────┼──────────┼──────────┼──────┤ │
│ │ MRVU    │ Direxion...  │ N/A      │ 06-05    │ 恢復 │ │
│ └─────────┴──────────────┴──────────┴──────────┴──────┘ │
└─────────────────────────────────────────────────────────┘
```

### 5.2 行業新聞頁面
```
┌─────────────────────────────────────────────────────────┐
│  Stocker     [主頁] [行業] [檔案]              [中] [EN] │
├─────────────────────────────────────────────────────────┤
│ 行業新聞與報告                              [收集行業新聞] │
│ ┌───────────────┬───────────────┬───────────────┐       │
│ │ Technology    │ Consumer      │ Industrials   │       │
│ │ 3 追蹤標的    │ 1 追蹤標的     │ 1 追蹤標的     │       │
│ │ 9 報告        │ 3 報告        │ 15 報告       │       │
│ └───────────────┴───────────────┴───────────────┘       │
│                                                          │
│ [已選擇: Technology]                                      │
│ ┌────────────────────────────────────────────────────┐  │
│ │ 📄 NVDA 10-Q (2026-05-20)                         │  │
│ │ 📄 NVDA 10-K (2026-02-25)                         │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.3 股票詳情頁 — 互動圖表
```
┌─────────────────────────────────────────────────────┐
│ ← 返回   TSLA - Tesla Inc.           ⚠️ 財報 06/20   │
├─────────────────────────────────────────────────────┤
│ [1M] [3M] [6M] [1Y]   指標: ☑MA ☑RSI ☑MACD ☑Volume │
│ ┌─────────────────────────────────────────────────┐  │
│ │          大型走勢圖 (含可選指標)                   │  │
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

### 5.4 報告詳情頁 — PDF + AI 聯動
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
│  └──────────────────┘  │                            │
│  [◀ 上一頁] [3/12] [下一頁 ▶] │                       │
└────────────────────────┴────────────────────────────┘
```

---

## 6. 數據更新策略 — 每晚統一排程 ⭐

所有資料收集統一在每晚 20:00 由 `nightly_tasks.py` 執行：

| 任務 | 說明 | 來源 |
|------|------|------|
| **SEC 財報下載** | 追蹤 ticker 的最新 10-K / 10-Q 年報/季報 | SEC EDGAR |
| **行業新聞收集** | 各行業板塊的新聞及分析 | Yahoo Finance |
| **金融機構分析報告** | 分析師評級、目標價、盈利預測 | yfinance + Yahoo Finance |

其他即時更新：
- **即時價格:** 前端每 5 秒輪詢 `/api/tickers/stream`
- **歷史數據:** 每日首次訪問時更新，存入時序數據庫
- **AI 分析:** 收集到新報告後自動觸發

---

## 7. 檔案結構

```
Stocker/
├── SPEC.md
├── README.md
├── app.py              # Flask 主應用
├── models.py           # 核心數據庫 models (含歸檔機制)
├── tsdb.py             # 時序數據庫操作
├── nightly_tasks.py    # 每晚排程統一入口 ⭐
├── services/
│   ├── stock_data.py   # yfinance 數據服務
│   ├── report_collector.py  # 報告收集
│   ├── earnings_downloader.py  # SEC EDGAR 財報下載
│   ├── industry_collector.py   # 行業新聞收集
│   ├── analyst_collector.py    # 金融機構分析報告 ⭐
│   └── ai_analyzer.py  # AI 分析服務
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── i18n.css    # 語言切換器樣式
│   └── js/
│       └── i18n.js     # 多語言翻譯系統
├── templates/
│   ├── base.html       # 基礎模板 (PDF.js CDN + i18n)
│   ├── index.html      # 主頁 (股票+報告+歸檔)
│   ├── stock_detail.html
│   ├── report_detail.html  # PDF viewer + AI 聯動
│   ├── industry.html   # 行業新聞頁面
│   └── files.html
├── data/
│   ├── stocker.db      # 核心 SQLite
│   ├── timeseries.db   # 時序 SQLite (分離)
│   └── files/          # 檔案儲存
│       ├── earnings/   # SEC 財報
│       ├── analyst_report/  # 分析師報告
│       ├── news/       # 行業新聞
│       └── sec_filing/
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
- **多語言:** 繁體中文 (預設) / English，導航欄切換

---

## 9. 自動化排程 — 每晚統一執行

| 時間 | 任務 | 腳本 | 說明 |
|------|------|------|------|
| 每天 20:00 | **統一排程** | `nightly_tasks.py` | 依序執行以下三項任務 |
| | 1. SEC 財報下載 | `earnings_downloader.py` | 下載追蹤 ticker 的最新 10-K / 10-Q |
| | 2. 行業新聞收集 | `industry_collector.py` | 從 Yahoo Finance 收集各行業新聞 |
| | 3. 金融機構分析報告 | `analyst_collector.py` | 收集分析師評級及預測 |
| 每 5 秒 | 即時價格更新 | 前端輪詢 | 更新價格顯示 |

### 排程執行流程
```
nightly_tasks.py
├── [1/3] earnings_downloader.py
│   └── 為每個追蹤 ticker 下載 SEC 10-K / 10-Q
├── [2/3] industry_collector.py
│   └── 為每個行業板塊收集 Yahoo Finance 新聞
└── [3/3] analyst_collector.py
    └── 為每個追蹤 ticker 收集分析師評級及預測
```
