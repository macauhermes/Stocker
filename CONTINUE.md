你是陳仔0號的 Hermes Agent。被 cron 每 1 小時叫醒。

## 當前狀態（截至最後一次手動執行 2026-08-26）

|**Stocker repo**: ~/repos/Stocker/，git 已 push commit 5344056 (v3.4.32)
|**Latest commit**: 5344056 [P3] fix: /industry sector reports — add 3 missing icon mappings (v3.4.32)
|**Server**: localhost:5000（python app.py 跑緊）
|**Branch**: main
|**Remote**: git@github.com:macauhermes/Stocker.git

**v3.4.33 (2026-08-27) — Hardcoded CJK in JS toast/badge strings (Pattern 5d)**:
- ✅ Sibling subagent WIP salvage — 3 files modified (i18n.js + index.html + industry.html), `git status` showed uncommitted changes when cron tick fired
- ✅ Salvage check #5 passed: 5 zh + 5 en i18n keys added (index.refresh_reason_us_market_open/extended_hours/off_hours/weekend, index.preview_loading, industry.collect_done/failed/network_error); .preview-loading CSS class exists in variables.css; node --check OK on both modified templates; gremlin check clean
- ✅ **Bug class**: Pattern 5d — hardcoded CJK strings inside JS `showToast()` / badge `textContent =` calls bypassed `applyI18n()` entirely (applyI18n only rewrites static HTML markup, not runtime JS string output)
- ✅ 5 hardcoded CJK strings wired:
  1. `templates/index.html:1475-78` — refresh-badge `reasonMap = {us_market_open:'盤中',...}` literal map → `t('index.refresh_reason_' + d.reason)`
  2. `templates/index.html:1614` — previewBox `<div class="preview-loading">載入中…</div>` → `t('index.preview_loading')`
  3. `templates/industry.html:435` — `showToast('收集完成！', 'success')` → `t('industry.collect_done')`
  4. `templates/industry.html:439` — `showToast(data.error || '收集失敗', ...)` → `t('industry.collect_failed')`
  5. `templates/industry.html:442` — `showToast('網絡錯誤', 'error')` → `t('industry.network_error')`
- ✅ Detection recipe: grep `templates/ static/js/ -rnE "(showToast\\(['\\\"]|textContent\\s*=\\s*['\\\"])" -B 1 | grep -E "[一-鿿]+"` — each match is a JS-side hardcoded CJK string that applyI18n() can never touch
- ✅ Touch: static/js/i18n.js (+22 lines), templates/index.html (+5/-4), templates/industry.html (+3/-3). Template-only → no restart needed
- ✅ Smoke test: / 200 + preview_loading wired; /industry 200 + 3 industry.collect_* wired; i18n.js node --check OK
- Commit: 3cb2328

**v3.4.32 (2026-08-27) — /industry sector reports icon mapping gap**:
- ✅ Pattern 8b bug class (same as v3.4.20 but for industry.html): `/industry` page sector reports panel 嘅 `renderReports()` 只覆蓋 2 個 category (`earnings`, `industry|news`) — `analyst_report` / `investment_bank_report` / `sec_filing` 全部 fall back 落 generic 藍色 `description` 圖示
- ✅ Technology sector reports 22 份 `analyst_report` 全部顯示默認藍色 description 圖示（應該係 analytics/blue 跟 index.html 一致）
- ✅ 3 個新 `else if` branches added，parity 100% 跟 index.html renderReports() (analytics/blue + account_balance/blue + gavel/orange)
- ✅ Pure frontend — Touch: templates/industry.html (+20 lines, +0/-0)，0 backend / DB / i18n changes
- ✅ Smoke test: /industry 200, JS node --check OK, mojibake clean, 3 v3.4.32 markers 喺 served HTML
- ✅ Template-only → no restart needed
- Commit: 5344056

**v3.4.31 (2026-08-27) — Hardcoded CJK in 3 templates → i18n wiring fix**:
- ✅ Pattern 5 audit fix: 5 個 hardcoded CJK strings 喺 3 個 templates — 之前英文 mode 全部 fall back 喺中文
  1. `templates/index.html:236` — Groups tab 嘅 "管理分組" link 冇 data-i18n 包住
  2. `templates/stock_detail.html:43` — compare button 嘅 `title="比較"` 冇 data-i18n-title
  3. `templates/stock_detail.html:56` — line chart button 嘅 `title="折線圖"` 冇 data-i18n-title
  4. `templates/stock_detail.html:59` — candlestick button 嘅 `title="陰陽燭"` 冇 data-i18n-title
  5. `templates/system.html:150` — info icon `title="這些操作..."` — 已有 data-i18n-title 但 i18n key 之前已存在 (system.actions_warning)
- ✅ applyI18n() 喺 i18n.js:1152 只 query `[data-i18n-title]` selector set title attribute — 冇 attribute 嘅 element 永遠唔會被翻譯
- ✅ 加 2 個 i18n keys (`index.groups_manage` zh + en)，其餘 4 個 keys (`stock.compare` / `stock.chart_line` / `stock.chart_candlestick` / `system.actions_warning`) 已經喺 i18n.js 存在但從未被任何 markup reference
- ✅ Touch: templates/index.html (+1/-1), templates/stock_detail.html (+3/-3), static/js/i18n.js (+2 keys). Template-only → no restart needed
- ✅ Smoke test: / 200 + data-i18n="index.groups_manage" markup 喺度; /stock/TSLA 200 + 3 個 chart button tooltips 全部有 data-i18n-title; /system 200 + data-i18n-title="system.actions_warning" markup 喺度; node --check i18n.js OK; gremlin check OK
- ✅ 順手 cleanup: NOPE_NOT_REAL smoke-test ticker 由 2026-08-26 13:11 已經 archived (無 orphan reports/files, data-only, 唔需要 commit)
- Commit: 6047abe

**v3.4.30 (2026-08-26) — /system industry_news counter surfacing**:
- ✅ Pattern 1 應用: `/api/metrics/summary` 由 v3.4.16 起一直有 `industry_news` counter block (services/metrics.py:806) — but `renderCounters()` in templates/system.html:357 嘅 `groups` array 漏咗呢個 key, 結果 /system admin page 嘅 Prometheus counters panel 永遠唔顯示行業新聞請求 stats
- ✅ 加 `industry_news` group 到 renderCounters(), 順序排在 ticker_refresh 後面 (邏輯 grouping: ticker refresh → 行業新聞 → manual triggers)
- ✅ 2 個新 zh + 2 個新 en i18n keys (`system.cnt_industry_news`: '行業新聞請求' / 'Industry news requests')
- ✅ Smoke test: `/api/metrics/summary` 返 `industry_news: {total: 0, ok: 0, empty: 0}` (新加嗰陣 zero, 證明 labels pre-created) — 而家 8 個 counter groups 全部 surface (之前只有 7)
- ✅ Touch: templates/system.html (+1 line), static/js/i18n.js (+2 keys). Template-only → no restart needed
- Commit: <next>

**v3.4.25 (2026-08-26) — Stock detail 新聞 filter row**:
- ✅ Pattern 4b 第五個應用: stock_detail.html 新聞 panel 加 filter row — publisher pills (動態由 7 個 source 構造, count desc 排序) + sort dropdown (newest/oldest) + count badge `{shown}/{total} 條`
- ✅ JS: 將 `renderNews()` 拆做 `allNews` module-scope cache + `applyNewsFilters()` + `renderNewsFilterRow()`; langchange 時 `loadDetail()` re-render 自動 reload filter state
- ✅ 8 zh + 8 en i18n keys (`detail.news_*` namespace): sort_label / sort_newest / sort_oldest / publisher_all / count / no_match / try_other / untitled
- ✅ Empty-state 區分: 冇 news (article icon) vs filter 排除晒 (filter_alt_off icon + 「試下揀「全部來源」或另一個來源」提示)
- ✅ escHtml helper 防 XSS — publisher name + title + link 全 escape
- ✅ CSS: 新增 .pill-count 計數 chip inside .sector-pill; active 時變白色半透明 background
- ✅ Reuses .events-filter-row / .sector-pills / .stocks-control-select / .stocks-filter-count (zero new wrapper classes)
- ✅ Smoke test: TSLA 10 news / 7 publishers (Benzinga/Motley Fool/Stocktwits/Yahoo Finance/GuruFocus.com/24/7 Wall St./Trefis); NVDA + MSFT pages 都 200 + 全部新 markup ID 喺度; JS node --check OK; mojibake clean
- ✅ Pure frontend — 改動: templates/stock_detail.html (+165/-11), static/js/i18n.js (16 keys), static/css/components.css (+19)
| ✅ Template-only change → no restart needed, server 200 OK
| Commit: af7bb87
|**v3.4.26 (2026-08-26) — /api/nightly-refresh 500 Bug Fix**:
|- ✅ Pattern 6 latent-bug detection: `POST /api/nightly-refresh` 由 v3.3 ships 起就壞咗, 每次撳 `/system` admin `nightly_refresh` button 500 AttributeError
|- ✅ `sqlite3.Row has no attribute 'symbol'` — `services/nightly_refresher.py:70` 用咗 `t.symbol` 屬性訪問, 但 sqlite3.Row 只支援 bracket access (Pitfall 12/14)
|- ✅ 改成 `td = dict(t); symbol = td["symbol"]` — 一次性 dict() wrap, 之後兩個 column 都用 bracket access, 唔再 attribute access
|- ✅ Companion metric fix: app.py `/api/nightly-refresh` success path 加 `metrics.record_manual_trigger('nightly_refresh')` — v3.4.24 ships `manual_triggers` Counter 但漏咗 wire `nightly_refresh` action, 只 wire `check_banks` + `collect_reports`. 而家 3 個 action 全部 counter 都會跟住 button press inc
|- ✅ Smoke test: `POST /api/nightly-refresh {"period":"1mo"}` 200 + 10 tickers refreshed, 22 rows each; metrics show `stocker_nightly_refresh_total{status="success"}=1` + `stocker_manual_triggers_total{action="nightly_refresh"}=1`
|- ✅ Grep 全 codebase for 同款 `t.symbol else t.X` pattern — 0 other occurrences
|- Touch: services/nightly_refresher.py (+5/-2), app.py (+2 lines)
| Commit: 7fa504d

**v3.4.28 (2026-08-26) — stock_detail Related Reports section**:
- ✅ Pattern 1 應用: stock_detail.html 加 Related Reports card (å Events 上面), 消費 `/api/reports?ticker=X&limit=5` endpoint (v3.4.3 ships, 之前從來冇 UI surface)
- ✅ 每隻追蹤中嘅 ticker 喺 DB 都有 6-30 份 10-K/10-Q/分析師/招股書報告, stock detail page 之前要 scroll 去 /report/<id> 先見到
- ✅ Parallel fetch via loadRelatedReports() — 唔 block 其他 sections render
- ✅ renderRelatedReports() 用 5 個 category-specific icon mapping (mirrors index.html renderReports() v3.4.20 fix): earnings=assessment/green, industry|news=article/orange, analyst_report=analytics/purple, investment_bank_report=account_balance/blue, sec_filing=gavel/orange
- ✅ 每張 card 連結去 /report/<id>, hover highlight border + lift
- ✅ Empty state: folder_open icon + 「暫無報告」title + hint 講之後會有
- ✅ Load error state: error icon + common.load_error message
- ✅ 4 zh + 4 en i18n keys (detail.reports_title / reports_count / reports_empty_title / reports_empty_hint)
- ✅ CSS: .related-reports-list flex column + .report-card hover effect
- ✅ Salvaged sibling subagent WIP — verified 5/5 i18n keys + 2/2 CSS classes 喺 i18n.js/components.css 已存在; JS node --check OK; mojibake clean
- ✅ Pure frontend — Touch: templates/stock_detail.html (+134), static/js/i18n.js (+8), static/css/components.css (+16 lines). Template-only → no restart needed, server 200 OK
- ✅ Smoke test: /stock/TSLA 200 + 7 expected markup markers; /api/reports?ticker=TSLA&limit=5 返 5 reports (1 analyst + 4 earnings); MRVU/SPCX/NVDA 全 200 + 6+ markup IDs
- Commit: 9cbbd90

**v3.4.29 (2026-08-26) — refresh_ticker_data() sqlite3.Row AttributeError fix + observability**:
- ✅ Pattern 6 latent-bug detection: services/stock_data.py:refresh_ticker_data() 由 v3.3 ships 起每次 call 都 silently 失敗 — `ticker_row.id` / `ev.event_type` / `ev.event_date` 用 sqlite3.Row 嘅 attribute access (Row 只支援 bracket access, Pitfall 12b)
- ✅ Sibling subagent WIP detection: 2 files modified 已經喺 git status, 檢查 #5 (i18n/CSS 唔適用因為係 backend) + import test 通過; 唯一需要補嘅係 stock_data.py 缺少 `_record_refresh_metric` import (sibling 漏咗 wire)
- ✅ 加 `try: from services.metrics import record_ticker_refresh as _record_refresh_metric except ImportError: def _record_refresh_metric(_s): return None` — 容錯 test setup 同時 wire metric 落 refresh success/error 兩條 path
- ✅ Prometheus 新增 `stocker_ticker_refresh_total{status=success|error}` Counter + `/api/metrics/summary` 加 `ticker_refresh: {total, success, error}` block (Pitfall 15 pattern — labelled Counter 用 `_metrics.values()` sum children)
- ✅ Companion Pattern 1 修復: /system admin page 嘅 Prometheus counters panel 加入 `ticker_refresh` + 之前 orphan 嘅 `manual_triggers` 兩個 group (manual_triggers i18n key 已經存在由 v3.4.24 起但從未 wire 入 renderCounters())
- ✅ 2 zh + 2 en i18n keys (`system.cnt_ticker_refresh` 新加, `system.cnt_manual_triggers` 已存在重用)
- ✅ Smoke test: TSLA POST /api/stock/TSLA/refresh 200 + `stocker_ticker_refresh_total{status="success"}=1.0` + summary `ticker_refresh: {success:1, error:0, total:1.0}`; /system page 兩個新 counter card 都 render
- ✅ Touch: services/metrics.py (+37 lines), services/stock_data.py (+13/-5), templates/system.html (+2), static/js/i18n.js (+2 keys). Backend 改動 → restart server, 200 OK
- Commit: 4972929


**v3.4.27 (2026-08-26) — stock_detail Events Timeline section**:
- ✅ 新加 stock_detail.html 嘅 Events Timeline card (喺 Holdings Section 上面) — render `/api/stock/<sym>/detail` 嘅 events array 為 full list (type icon + date + type label + title)
- ✅ Past 同 dismissed events 自動 dim (opacity 0.45)；type-specific icon color (earnings 黃 / dividend 綠 / sec_filing 橘 / other 紫)
- ✅ Upcoming event 加藍色 "即將" tag；dismissed event 加灰色 "已知悉" tag
- ✅ Empty state: event_busy icon + "暫無事件" message
- ✅ 同步 fix event banner bug — banner 之前用 `data.events[0]`，可能係 past dividend；改成搵下一個 future non-dismissed event 先 display banner
- ✅ 5 個 zh + 5 個 en i18n keys (detail.events_title / events_empty / events_count / events_upcoming_tag / events_dismissed_tag)
- ✅ 新加 CSS classes (stock-events-list, event-row, event-row-dim, event-row-icon-{type}, event-row-date/type/title, event-row-tag, event-row-tag-dismissed) — 含 ≤480px mobile responsive
- ✅ Pure frontend — 改 templates/stock_detail.html (+81/-6), static/css/components.css (+111), static/js/i18n.js (+14)。Template-only → no restart needed
- ✅ Smoke test: /stock/TSLA 200 + 10 markup markers; /stock/NVDA 2 events (6/4 past dividend dim + 8/27 earnings "即將" tag); JS node --check OK; gremlin clean

**v3.4.22 (2026-08-26) — 行業報告 filter row**:
- ✅ `/industry` sector 報告 panel 加 filter row：category pills (全部/財報/分析師/招股書/新聞) + sort dropdown (最新/最早優先) + count badge
- ✅ Pills 動態由 data 構造 (count desc 排序)；10 個 zh + 10 個 en i18n keys (industry.filter_* / industry.sort_* / industry.count_* / industry.no_filter_match / industry.try_other_filter)
- ✅ Distinguish empty states: 冇 reports vs filter 排除晒 (用 filter_alt_off icon + 提示「試下揀另一個類別」)
- ✅ Pure frontend — 改動: templates/industry.html (filter row markup + 2 functions), static/js/i18n.js (20 keys), static/css/components.css (4 type-specific active colors), README.md (1 行)
- ✅ Smoke test: Technology sector 50 reports (39 earnings + 11 analyst), filter 'earnings' → 39 reports, 'analyst_report' → 11, 'sec_filing' → 0 (empty-filtered state), sort desc/asc 都正確
- Commit: <next>

**v3.4.23 (2026-08-26) — Files page filter row**:
- ✅ Pattern 4b 第四個應用: /files 頁面加 filter row — 9 個 ticker pills (all + TSLA/TE/IBM/GLW/NVDA/MSFT/MS/GS/SPCX) 動態由 /api/files 數據構造 (count desc 排序) + search input (200ms debounce) + sort dropdown (newest/oldest/name/size_desc) + count badge
- ✅ 10 個 zh + 10 個 en i18n keys (files.search_placeholder / files.sort_* / files.count_* / files.no_filter_match / files.try_other_filter)
- ✅ CSS reuses .events-filter-row / .sector-pills / .stocks-control-select；加 .files-ticker-pills .active cyan (#29b6f6) 區分上面 category tabs + .files-search-input 240px (≤480px 160px)
- ✅ escHtml helper + langchange re-render + empty-state distinguishes "no data" (folder_open) vs "filter excluded all" (filter_alt_off + hint)
- ✅ Salvaged sibling subagent WIP — 5/5 i18n keys + 2/2 CSS classes 全部喺 i18n.js/components.css 已存在；JS node --check 10620 chars OK；mojibake clean
- ✅ Pure frontend — 改動: templates/files.html (+212/-21 lines), static/js/i18n.js (20 keys), static/css/components.css (39 lines)
- ✅ Smoke test: /api/files 200 (177 files), /files 200 (11/11 expected filter row IDs/classes/i18n keys 喺 HTML), template-only change → no restart needed
- Commit: 4af10ad

**已完成嘅改進 (v3.2)**:
1. ✅ 多源數據備援鏈 (multi_source.py) — yfinance → Yahoo → Stooq → CoinGecko → 自訂 JSONPath
2. ✅ 智能更新頻率 (3s/15s/60s/300s) + SSE endpoint
3. ✅ 觸控走勢圖 (chartjs-plugin-zoom + hammerjs + 十字線)
4. ✅ 股票搜索 + 預覽 (200ms debounce autocomplete)
5. ✅ 手機 UI (320px + 44px + FAB + bottom-nav 5 tab)
6. ✅ 自訂 JSONPath 數據源管理頁 /sources
| 7. ✅ SPCX 7 份 SEC 招股書 (data/files/sec_filing/)

**v3.4.17 (2026-08-26) — 報告類型 Tab 補完 + i18n + 類別覆蓋修復**:
- ✅ **Bug fix**: `filterByType('analyst')` 之前只 query `category='analyst_report'`，完全漏咗 `investment_bank_report` (16 份) 同 `sec_filing` (7 份 SpaceX 招股書) — 呢 23 份報告喺 Dashboard 報告 tab 從未出現過 (用戶要逐個 scroll 全部 report 列表先見到)
- ✅ 新增 2 個 type tab：「券商分析」(`analyst_report`) + 「投行」(`investment_bank_report` + `sec_filing`)，將 5 個 report category 全部 surface
- ✅ 將原本 hardcoded CJK 嘅 4 個 tab button 文字 (全部/財報/新聞/分析) 改用 `data-i18n="reports.tab.X"` 屬性 + 10 個 i18n keys (zh + en)
- ✅ Tab 按鈕結構改用 `<span data-i18n>` 包住 label，保留 material-icons-outlined glyph
- ✅ Smoke test：bank tab → 10 份報告 (3 investment_bank_report + 7 sec_filing) 全部可見；之前呢類全部無 UI surface
- ✅ Pure frontend — 改動: templates/index.html (tabs markup + filterByType), static/js/i18n.js (10 keys), README.md (1 行)
- Commit: 53ded9e

**v3.4.18 (2026-08-26) — Files page Pattern 8 fix (孖生 v3.4.17 bug class)**:
- ✅ **Bug fix**: `/files` 頁面嘅 category tabs 之前係 (all/earnings/analyst_report/news)，但 DB `files` table 只有 3 個 category (earnings: 113, analyst_report: 57, sec_filing: 7) —— 從來冇 `news`！7 份 SpaceX 招股書 (SPCX_S-1 × 4 個 + SPCX_EU-Prospectus × 3 個) 永久隱形，只可以喺「全部」tab 見到，用戶唔知道揀咩
- ✅ 同一個 bug class 係 v3.4.17 嘅孖生兄弟：UI filter 同 DB category 不對齊 (overlap，但唔同 page)
- ✅ 將 dead `news` tab 換成 `sec_filing` tab (matches actual DB content)
- ✅ `formatCategory()` i18n key `files.cat.sec_filing` 已經喺 i18n.js 存在 (zh + en)，直接重用無需新 key
- ✅ 新增 sec_filing icon mapping: `gavel` Material icon + 橘色 `rgba(255,145,0,.15)` background
- ✅ 1 file 改動 (templates/files.html, +7/-7 lines)，零 backend / DB / CSS / i18n 改動
- ✅ Smoke test: /files 200, /api/files 返 177 files (analyst_report: 57, earnings: 113, sec_filing: 7)，sec_filing tab 可見 SPCX_S-1 + SPCX_EU-Prospectus 招股書
- ✅ JS validated: node --check 4374 chars OK，mojibake clean (U+FFFD/U+00AD 0 hits)
- Commit: ddd9caf
- Commit: <next>

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
