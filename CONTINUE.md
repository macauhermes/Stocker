你是陳仔0號的 Hermes Agent。被 cron 每 1 小時叫醒。

## 當前狀態（截至最後一次手動執行 2026-06-13）

**Stocker repo**: ~/repos/Stocker/，git 已 push commit ded10a5 (v3.3.1)
**Latest commit**: ded10a5 [P3] enhance Prometheus metrics + add /health + /api/metrics/summary
**Server**: localhost:5000（python app.py 跑緊）
**Branch**: main
**Remote**: git@github.com:macauhermes/Stocker.git

**已完成嘅改進 (v3.2)**:
1. ✅ 多源數據備援鏈 (multi_source.py) — yfinance → Yahoo → Stooq → CoinGecko → 自訂 JSONPath
2. ✅ 智能更新頻率 (3s/15s/60s/300s) + SSE endpoint
3. ✅ 觸控走勢圖 (chartjs-plugin-zoom + hammerjs + 十字線)
4. ✅ 股票搜索 + 預覽 (200ms debounce autocomplete)
5. ✅ 手機 UI (320px + 44px + FAB + bottom-nav 5 tab)
6. ✅ 自訂 JSONPath 數據源管理頁 /sources
7. ✅ SPCX 7 份 SEC 招股書 (data/files/sec_filing/)

**v3.4.16 (2026-08-25) — 行業新聞 panel 連接 + 之前係 stub 嘅 endpoint 修復**:
- ✅ `/api/industry/<sector>/news` 由 stub `return jsonify([])` 改為真正 query `reports` table where `category='industry'` + file_path basename 以 `<safe_sector>_industry_` 開頭；123 篇 Consumer Cyclical / 139 篇 Industrials / 159 篇 Technology news 終於 surfacing
- ✅ Normalise sector name 跟 `services/industry_collector.safe_sector` 用 `re.sub(r'[^\w\-]', '_', sector[:40]).strip('_')`，所以「Consumer Cyclical」(space) match 到 file_path「Consumer_Cyclical」(underscore)
- ✅ `/industry` sector 詳情 panel 拆成兩個：上面「行業新聞」card + 下面「行業報告」card，兩個 endpoint 平行 fetch (`Promise.allSettled`)，獨立 loading + empty state
- ✅ Prometheus 新增 `stocker_industry_news_requests_total{status=ok|empty}` counter + `/api/metrics/summary` 嘅 `industry_news: {total, ok, empty}` block
- ✅ 4 個新 zh + 4 個新 en i18n keys (industry.news / industry.no_news / industry.news_error / industry.news_count)
- ✅ `.card-meta` CSS class (右側 muted "{n} 篇" 計數 badge)
- ✅ Touch: app.py (1 endpoint), services/metrics.py (1 metric + summary block), templates/industry.html (1 new card + parallel fetch), static/css/components.css (.card-meta), static/js/i18n.js (8 keys), README.md (1 條)

**v3.4.15 (2026-08-25) — `/api/events/sync` 500 AttributeError fix**:
- ✅ `/api/events/sync` 引用咗唔存在嘅 `models.get_active_tickers()` — calendar 嘅「同步」掣由 v3.3 ships 起就壞咗，每次撳都 500 AttributeError
- ✅ 改用 `models.get_all_tickers()`（已經 filter `archived = 0`，功能一樣）
- ✅ Smoke test: POST sync 返 `{synced: 16, errors: []}`；calendar 2026-08 → 4 events (NVDA earnings 8/27、IBM/MSFT dividends 等)
- ✅ Calendar 從 0 events → 16 events，所有 10 隻 tracked tickers 都有 earnings/dividend 行
- ✅ Touch 1 line in app.py — pure function name fix, zero behavior change
- ✅ Grepped app.py for other missing model function references — no other latent bugs
- Commit: d507433

**v3.4.14 (2026-08-25) — Stocks-tab filter row**:
- ✅ Dashboard stock list 加 filter row — sector pills (dynamic from /api/tickers data, count desc) + sort dropdown (5 options: 代碼/漲跌幅/現價/市值/持倉股數) + holdings-only toggle pill + filter count badge
- ✅ Distinguish empty states: 冇股票 vs 過濾後冇 stock (filter_alt_off icon, no "+ Add" CTA)
- ✅ 10 zh + 10 en i18n keys — section label, 5 sort options, toggle text, count format `{shown}/{total}`, empty-filtered state
- ✅ Pure frontend — caches allTickers at module scope, applyStockFilters() filters+sorts+re-renders; 零 backend / DB / schema 改動
- ✅ JS validated node --check; smoke test: filter row markup all 6 IDs reach browser, 5 sort options rendered, /api/tickers has all 5 required fields (sector/shares_held/change_percent/current_price/market_cap)
- Commit: f8d9bb1

**v3.4.12 (2026-08-25) — README API docs 補完**:
- ✅ README API 端點表補入 14 個 missing routes：完整 `/api/banks/*` 集群 (10 個) + `/api/init-data` + `/api/reports/collect` + `/api/stock/<symbol>/refresh` + `/api/industry/<sector>/news` + `/api/banks/reports/<id>/download`
- ✅ 初始追蹤清單更新為 TSLA, NVDA, TE, GLW, MRVU, IBM, MSFT, GS, MS, SPCX (與 stock-list 對齊)
- ✅ 純文檔修正，零 backend / DB / template 改動
- Commit: <next>


**v3.4 補完 (2026-08-25)**:
- ✅ Prometheus 暴露 stocker_alerts_total{enabled=true|false} + stocker_alerts_triggered_total counter
- ✅ /api/metrics/summary 加入 `alerts: {enabled, disabled, triggered_total}` 區塊
- ✅ 三條觸發路徑都 inc counter: /api/stock/<sym>/refresh, /api/alerts/check, nightly_tasks.py
- ✅ _update_business_gauges() 從 price_alerts 表即時拉 enabled/disabled split

**v3.4.3 (2026-08-25)**:
- ✅ `/api/reports` 新增 search/filter 能力 — `?q=&category=&source=&ticker=&limit=&include_total=`
- ✅ `models.search_reports()` + `count_search_results()` — AND-combined filters, case-insensitive
- ✅ Ticker filter 由 file_path basename prefix 解析 (e.g. `GLW_10-K...` → GLW)
- ✅ 向後兼容：無 filters 時仍返 bare array；filters 存在時返 `{results, count, filters[, total_count]}`
- ✅ Prometheus counter `stocker_report_searches_total{has_results=true|false}` + `/api/metrics/summary` 加 `report_searches` block
- ✅ 24 unit tests (tests/test_report_search.py) — all passing (195/195 total)
- Commit: 40e37b5

**v3.4.4 (2026-08-25)**:
- ✅ Dashboard 投資組合卡片內嵌 Chart.js sparkline — 繪製近 30 日 `total_value` 走勢
- ✅ 漲綠/跌紅配色，配淺色 fill area，hover 顯示當日美元數值
- ✅ Meta 行顯示 "Nd · ±$X (±Y%)" 整段趨勢摘要
- ✅ < 2 個快照時自動隱藏 wrapper（單點無法畫 trend line）
- ✅ 重新渲染前先 `.destroy()` 舊 Chart.js instance，避免 langchange 切換時記憶體洩漏
- ✅ i18n：新增 `portfolio.sparkline_meta` + `portfolio.sparkline_title` (zh + en)
- ✅ Touch templates/index.html + static/css/components.css + static/js/i18n.js，無 backend 改動
- ✅ Smoke test：手動 capture 3 個 backdated snapshots (08-21, 08-23, 08-24)，curve 由 $8,430 → $15,409
- Commit: 4fc0299

**v3.4.5 (2026-08-25)**:
- ✅ `/api/portfolio/snapshots/export.csv` — 將每日 portfolio snapshots 下載成 CSV (default) 或 TSV (`?fmt=tsv`, Excel-friendly paste)
- ✅ Columns: snapshot_date, total_value, total_cost, total_pnl, pnl_pct, holdings_count, captured_at
- ✅ `?days=N` 控制 window (default 365, max 3650); 總是 200 — empty result 返 header-only CSV 而非 404
- ✅ Prometheus counter `stocker_portfolio_exports_total{format=csv|tsv}` + `record_portfolio_export()` helper
- ✅ `/api/metrics/summary` 加入 `portfolio_exports: {total, csv, tsv}` block
- ✅ 13 個 unit tests (tests/test_portfolio_csv.py) — all passing (208/208 total)
- ✅ Fix double-charset bug: Flask auto-appends `; charset=utf-8` to text/* mimetypes, 所以唔可以自己加

**v3.4.6 (2026-08-25)**:
- ✅ `/api/portfolio/breakdown` — 即時由 current prices 計算每個持倉嘅 (market_value, cost_value, unrealized_pl, unrealized_pl_pct, share_of_portfolio)，按市值降序
- ✅ Reuses `services.portfolio_snapshot.compute_totals()` (no new service code, only HTTP wrapper + enrichment)
- ✅ Skips tickers with shares=0 or no price (matches snapshot policy)
- ✅ Prometheus counter `stocker_portfolio_breakdown_requests_total{status=ok|empty|error}` + `record_portfolio_breakdown()` helper
- ✅ `/api/metrics/summary` 加入 `portfolio_breakdowns: {total, ok, empty, error}` block
- ✅ Smoke test: 3 個持倉 (TSLA 30股/MSFT 8股/NVDA 5股) 返 share_of_portfolio 67.94% / 25.3% / 6.76% — sum 100%
- ✅ 10 個 unit tests (tests/test_portfolio_breakdown.py) — all passing (218/218 total)

**v3.4.10 (2026-08-25)**:
- ✅ `/system` 系統狀態儀表板 — surface 之前 orphan 嘅 `/api/metrics/summary` + `/health` endpoint
- ✅ 4 個 stat cards：Health（status badge + uptime + DB/tsdb/disk checks）/ Tickers（active + reports + events + reports by category bar）/ Portfolio（snapshots + latest value + P&L + latest report）/ Features（alerts + banks + custom sources + watchlist groups + SSE）
- ✅ Top sectors + Top tickers by reports 排行 bar chart
- ✅ Prometheus counters panel（ticker_exports / portfolio_captures / portfolio_exports / portfolio_breakdowns / report_searches）
- ✅ 30 秒 auto-refresh + visibilitychange 暫停 + langchange 即時 re-render + 「原始格式」連結去 `/metrics`
- ✅ Nav icon (`monitoring`) 加喺 base.html 嘅 nav-right (search + system + alerts)
- ✅ 純前端 + 1 個 route，零 backend / DB / schema 改動 — 46 個 zh + 46 個 en i18n keys
- ✅ Touch: templates/system.html (新建), static/css/components.css, static/js/i18n.js, templates/base.html, app.py, README.md, SPEC.md

**v3.4.9 (2026-08-25)**:
- ✅ Dashboard 持股清單新增「📤 匯出持倉 CSV」按鈕，直接重用現有 `/api/tickers/export.csv` endpoint
- ✅ 前端先 fetch + `response.ok` check，再由 Blob 產生 download；HTTP 4xx/5xx 不會誤報下載成功，並從 Content-Disposition 讀取伺服器檔名
- ✅ Fix `text/csv` double-charset：Flask 會自動附加一次 `charset=utf-8`
- ✅ Prometheus 新增 `stocker_ticker_exports_total{scope=all|group}` counter + `/api/metrics/summary` 的 `ticker_exports` 區塊
- ✅ 支援繁中 / English i18n（`index.stocks_toolbar`, `index.export_holdings_*`）
- ✅ 全部修改：`templates/index.html`, `static/css/components.css`, `static/js/i18n.js`, `app.py`, `services/metrics.py`, `README.md`, `SPEC.md`
- ✅ Smoke test：`GET /api/tickers/export.csv` 200、`Content-Type: text/csv; charset=utf-8`（single charset）、metric all=1/group=0

**v3.4.8 (2026-08-25)**:
- ✅ Dashboard 投資組合卡片新增「📸 拍攝快照」「📥 匯出 CSV」兩個 quick-action buttons — 終於將之前 orphan 嘅 `POST /api/portfolio/capture` 同 `GET /api/portfolio/snapshots/export.csv` 拉到 UI surface
- ✅ Buttons 帶 44px 觸控目標、桌面並排 / 手機自動堆疊、loading state 帶 ⏳ spinner、成功 / 失敗 toast 4 秒自動消失
- ✅ `data-i18n` 全部 6 個新 keys (zh + en)：`portfolio.{capture_now,export_csv,capture_success,capture_failed,export_failed,actions_title}`
- ✅ Prometheus 新增 `stocker_portfolio_captures_total{trigger=manual|nightly}` counter — manual 同 nightly 兩條 trigger path 都 inc
- ✅ `/api/metrics/summary` 新增 `portfolio_captures: {total, manual, nightly}` block
- ✅ 7 個 unit tests (tests/test_portfolio_capture_metric.py) — all passing (225/225 total)
- ✅ 改動: services/metrics.py, app.py, nightly_tasks.py, templates/index.html, static/js/i18n.js, static/css/components.css
- ✅ Smoke test: POST capture 返 201 + snapshot row #10、GET export.csv 返 text/csv + 6 行 CSV + Content-Disposition 對 filename=/metrics shows manual counter=1

**v3.4.7 (2026-08-25)**:
- ✅ Dashboard 投資組合卡片內嵌 holdings breakdown 表格 — 列出每個持倉嘅代碼/股數/現價/市值/未實現損益/佔比
- ✅ 零持倉時自動隱藏整個 wrapper (避免顯示空表)；sort by MV desc (server 已經做)
- ✅ Mobile-first: <480px 自動隱藏現價欄避免水平捲動 (MV = shares × price 讀者可以心算)
- ✅ i18n: 9 個新 zh/en keys (holdings_title/symbol/shares/price/market_value/unrealized_pl/share/empty/count_total)
- ✅ P&L 欄綠色 (正) / 紅色 (負) 配色；share 欄灰色；hover 整行淺藍高亮
- ✅ 純前端改動 — `templates/index.html` + `static/css/components.css` + `static/js/i18n.js`，零 backend / DB / route 改動
- ✅ Reuses `/api/portfolio/breakdown` (v3.4.6 endpoint)
- ✅ Smoke test: 3 holdings (TSLA 30股/MSFT 8股/NVDA 5股) 顯示正確 MV/P&L/share
- ✅ i18n langchange handler 自動重渲染 holdings table

**v3.4.2 (2026-08-25)**:
- ✅ Daily portfolio snapshots — services/portfolio_snapshot.py walks active tickers,
  multiplies (price × shares), persists to portfolio_snapshots table keyed by date
- ✅ 3 新 API: GET /api/portfolio/snapshots, GET /api/portfolio/summary (含 30 日 delta),
  POST /api/portfolio/capture (manual capture)
- ✅ nightly_tasks.py Task 6: 每日 20:00 自動拍攝 + prune >365d 嘅 snapshots
- ✅ Prometheus gauges: stocker_portfolio_snapshots_total + _value_dollars_latest + _pnl_dollars_latest
- ✅ /api/metrics/summary 加入 `portfolio: {snapshots_count, latest_value, latest_pnl}` 區塊
- ✅ Dashboard widget (templates/index.html) 顯示總市值/未實現損益/30 日變化/持倉數
- ✅ 13 個 zh/en i18n keys (static/js/i18n.js)
- ✅ 27 unit tests (tests/test_portfolio_snapshot.py) — all passing (171/171 total)
- Commit: 25cd9ef (cron tick salvage of ~2hr uncommitted WIP)

## 接力做事項（v3.3 規劃）

按以下優先級，每小時做 1-2 項，commit + push + restart server:

### P0 - 立即做
 [x] 將 `fetch_chart_data` 改用 multi_source.fetch_with_fallback()（commit a8d9115）
 [x] 將 `fetch_stock_info` 改用 multi_source.get_current_price() + yfinance 補完 PE/EPS/market_cap（commit f4e2251）
 [x] 將 `refresh_ticker_data` 入面嘅 `fetch_historical_prices` 改用 multi_source（commit a8d9115）
 [x] 加 staging area git commit workflow 改進 (scripts/stage_commit.py, commit c78d5ee)

### P1 - 重要
- [x] Add SSE client in index.html (用 EventSource 取代 setInterval 輪詢) (commit 56776e8)
- [x] Add `data-source-badge` 顯示每個 ticker 嘅數據源 (yfinance / yahoo_direct / stooq / coingecko / custom) (commit 3a802c4)
- [x] Add `data-freshness` 顯示最後更新時間 (relative: 3s ago / 5m ago) (commit 98ed308)
- [x] Add `nightly_refresher` 自動刷新 5 年歷史價 + 預熱 cache (commit a16585a)
- [x] Add `watchlist_groups` (用戶分組管理追蹤股票) (commit pending)
- [x] Add `events_calendar` 月曆視圖顯示 earnings/dividend/events
- [x] Add `banks/投行` feature — scraper + PDF + text renderer (commit 288aa7d)

### P2 - 改進
- [x] 將 mobile.css 結構化 (variables + components + utilities 分檔) (commit 16264cc)
- [x] 將 stock_detail.html chart 改用線上 plugin zoom + crosshair plugin (而非 chartjs-plugin-zoom) (commit 895af1c)
- [x] Add `candlestick` toggle (陰陽燭 vs 折線) (commit 19e2f12)
- [x] Add `compare` mode (兩股疊加圖) (commit f2a302b)
- [x] Add i18n 補完 (en 翻譯) (commit f0e4b2a)
- [x] 加 unit tests (pytest) for multi_source.py (commit pending)

### P3 - 優化
- [ ] 將 in-memory `_cache` 改 Redis (可選)
- [x] 加 Prometheus metrics endpoint (commit cdf61bd)
- [x] 增強 Prometheus 業務指標 + /health + /api/metrics/summary (commit ded10a5)
- [x] CSV export 投資組合 (active tickers + holdings + P&L) (commit 21b5bd1)
- [x] Price Alerts v3.4 (用戶自訂價格閾值，事件自動觸發) (commit a673b22)
- [x] alert_checker unit tests (26 tests covering threshold eval + side-effects + sweep + model validation) (commit eda159d)
- [x] Daily Portfolio Snapshots v3.4.2 (services/portfolio_snapshot.py + dashboard widget) (commit 25cd9ef)
- [x] Report Search v3.4.3 (/api/reports?q=&category=&source=&ticker=&limit=) (commit 40e37b5)
- [x] Report Search unit tests (24 tests covering all 4 filter dimensions) (commit 40e37b5)
- [x] Portfolio Sparkline v3.4.4 (Chart.js trendline on dashboard widget, < 2 snapshots hidden) (commit 4fc0299)
- [ ] 加 user accounts (multi-user)

## 流程

每次 cron 觸發:
1. `cd ~/repos/Stocker && git pull origin main` (拉最新)
2. 檢查 server 狀態 (`curl http://localhost:5000/api/refresh-interval`)
3. 如果 server 死咗: 重啟 (`pkill -f "python.*app.py" && cd ~/repos/Stocker && nohup .venv/bin/python app.py > /tmp/stocker.log 2>&1 &`)
4. 從 P0 開始做下一個未完成嘅項目
5. **完成一項就 commit push + restart server**（按陳仔0號指示: "每次全部commit push and restart web server"）
6. 用 Telegram 報告: 完成咗咩、改咗咩 files、下次做咩

## Git 規範

- Commit message 用 P0/P1/P2 tag: `[P0] feat: use multi_source in fetch_chart_data`
- 唔好掂未 commit 嘅現有 modified files (surgical changes 原則)
- Push 完驗證 server 200 OK 先算完成

## Telegram 報告格式（陳仔0號偏好簡潔）

```
✅ [v3.3 P0] fetch_chart_data 改用多源
   + 改咗 stock_data.py, app.py
   + commit xxxxx, push ok
   + server 重啟, 200 OK
   下次: 將 refresh_ticker_data 入面嘅 fetch_historical_prices 改用 multi_source
```

## 重要約束

- 唔好用 `git reset --hard` (可能丟失 uncommitted 嘢)
- 唔好 force push
- 唔好掂 `data/stocker.db`（runtime data, .gitignore 排除）
- 唔好掂 .gitignore
- 唔好將 secret / API key commit
- 遇到 import error 立即 `cd ~/repos/Stocker && source .venv/bin/activate` 再 retry
- 每次改完 service/stock_data.py 等 hot file，要驗證 server 200 + 至少一個新 endpoint 回 200

## Skill references

- `stocker-project`: 項目主指南
- `git-safe-push-cron`: 處理 push 衝突
- `github-pr-workflow`: 嚴格 commit 規範
- `web-search`: 研究新數據源
- `flask-api-integration-pitfalls`: Flask + 異步服務陷阱
