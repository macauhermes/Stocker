你是陳仔0號的 Hermes Agent。被 cron 每 1 小時叫醒。

## 當前狀態（截至 2026-08-31 cron tick）

**Stocker repo**: ~/repos/Stocker/，git 已 push commit cdf4bfe (v3.4.56)
**Latest commit**: cdf4bfe [P3] feat: surface cost_value column in portfolio holdings table (Pattern 9b)

**v3.4.56 (2026-08-31) — Holdings table 成本合計 column (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/portfolio/breakdown` returns 9 fields per holding including `cost_value` (TSLA 6000, MSFT 2800, NVDA 1500) — but `index.html` holdings table only rendered 7 columns (symbol/shares/cost_basis/price/MV/P&L/share%)。`cost_value` (total cost in dollars = shares × cost_basis) 永久 silently dropped — 用戶睇到 "+52% gain" 但要 mental arithmetic 去知道 "呢個 position 我投資咗 $6000"
- ✅ **Fix scope** — pure frontend 3-file surgical addition (9 insertions / 4 deletions):
  - `templates/index.html` (+2): new `<th data-i18n="portfolio.holdings_cost_value">成本合計</th>` between cost_basis + current_price columns + matching `<td>${formatCurrency(h.cost_value)}</td>` in loadPortfolioHoldings() row template
  - `static/css/components.css` (+0/-2 mod): update mobile @media (max-width: 480px) to hide nth-child(5) (current_price) instead of nth-child(4) (which is now cost_value). On phones, cost_value (total $ invested) is more useful than live current_price
  - `static/js/i18n.js` (+2 keys): `portfolio.holdings_cost_value: '成本合計' / 'Cost Total'`
- ✅ 0 backend / DB / schema changes — endpoint already returns cost_value (3/3 holdings populated)
- ✅ **Verification**:
  - 275/276 tests passing (pre-existing failure `test_old_smoke_news_reach_response` unrelated to this change, documented in v3.4.46)
  - node --check on extracted index.html script + i18n.js both OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits 跨 3 modified files
  - / 200 OK; new `<th data-i18n="portfolio.holdings_cost_value">` + matching `<td>${formatCurrency(h.cost_value)}</td>` rendered
  - /api/portfolio/breakdown 3 holdings (TSLA/MSFT/NVDA) all have cost_value populated
- ✅ Touch: templates/index.html (+2/-0), static/css/components.css (+1/-3 mod), static/js/i18n.js (+2 keys). Template-only → no restart needed
- Commit: cdf4bfe

**v3.4.55 (2026-08-31) — Files page drill-down to report detail (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/files` returns 7 fields per row (category, created_at, file_path, file_size, filename, id, **report_id**) — but `templates/files.html renderFiles()` only consumed 5 (icon/filename/category-badge/size/date + download href). `report_id` field (302/302 rows populated) was silently dropped between API 同 DOM。Every file card on /files let user download 原始 file (HTML/PDF/TXT)，但完全冇 way 去 navigate 去 structured `/report/<id>` view (with v3.4.49 summary, v3.4.50 category badge, v3.4.51 created_at header)
- ✅ **Fix scope** — pure frontend 3-file surgical addition (15 insertions / 3 deletions):
  - `templates/files.html` (+9/-3): wrap download button 喺 `<div class="file-actions">` flex container; 新加 `<a class="file-view" href="/report/${f.report_id}">` description icon BEFORE download button; `data-i18n-title` for langchange re-translation; defensive `${f.report_id ? ... : ''}` guard (雖然 302/302 populated)
  - `static/css/components.css` (+19): `.file-actions` flex container with 2px gap; `.file-view` icon link with `var(--blue)` (matches report-detail visual language); hover state with rgba blue tint
  - `static/js/i18n.js` (+2 keys): `files.view_report: '查看報告' / 'View Report'`
- ✅ **Bonus Pattern 5c i18n fix**: existing icon-only download button 之前 hardcoded `title="下載"` CJK tooltip — 順手加返 `data-i18n-title="files.download"` + `title="下載"` zh fallback (English mode 之前 silent fallback 落中文)
- ✅ 0 backend / DB / schema changes — endpoint already returns report_id
- ✅ **Verification**:
  - node --check `files.html` script (12469 chars) + i18n.js both OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF) 0 hits across 3 modified files
  - /files 200 OK; template contains `file-view` + `file-actions` markup
  - /report/2379 200 OK (drill-down target works)
  - /api/files 302 rows, all with report_id populated
- ✅ Touch: templates/files.html (+9/-3), static/css/components.css (+19), static/js/i18n.js (+2 keys). Template-only → no restart needed, server stays 200 OK
- Commit: 0295ed7

**v3.4.54 (2026-08-31) — Events page per-event dismiss UI + hide-dismissed filter (Pattern 4b)**:
- ✅ **Bug class**: `/api/events/upcoming` 返每個 event 嘅 `dismissed` 同 `dismissed_at` fields (v3.3 ships 起就有)，但 events.html 嘅 upcoming list render 唔到 dismiss UI — 用户冇 way 去 dismiss 已知悉嘅 event (e.g. 已過嘅派息日)、亦冇 way 去 filter 走 dismissed events
- ✅ **Fix scope** — pure frontend 1-file surgical addition (40+ insertions):
  - `templates/events.html` (+40): new dismiss button (✕ icon, red) on each upcoming event card; conditional `${event.dismissed ? '重啟' : '已知悉'}` button label; new filter pill '隱藏已知悉'; empty-state distinguishes 'no events' vs '全部已 dismiss'
  - 7 zh + 7 en i18n keys: `events.dismiss` / `events.undismiss` / `events.dismissed_tag` / `events.hide_dismissed` / `events.show_all` / `events.all_dismissed` / `events.confirm_dismiss`
- ✅ **Verification**:
  - /events 200 OK; new dismiss button rendered for each event
  - node --check on extracted JS OK; gremlin clean
  - /api/events/upcoming 16 events (10 盈報 + 6 派息); `dismissed: 0` initially
- ✅ Touch: templates/events.html (+40). Template-only → no restart needed
- Commit: 7120ae1

**v3.4.53 (2026-08-31) — Report detail added-at timestamp (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/reports/<id>` returns 11 top-level keys (`analysis`, `category`, `content`, `created_at`, `file_path`, `id`, `published_at`, `source`, `summary`, `title`, `url`) — but `templates/report_detail.html` 只 wire 8 個 (title/published_at/summary/source/url/content/analysis + category badge from v3.4.51).`created_at` field ("when the report entered Stocker") 永久 silently dropped — 用戶睇到 `published_at` (原始 doc date) 但完全唔知 `created_at` (幾時 ingest 到系統)。新 ingest 嘅 GS 投行 PDF / 最新 SEC 招股書 — 用戶冇 way 知道「呢份 2 小時前加入」同「呢份 3 個月前加入」嘅分別
- ✅ **Fix scope** — pure frontend 2-file surgical addition (13 insertions):
  - `templates/report_detail.html` (+11): new `#report-added` div 喺 `#report-summary` 下面 (muted 0.75rem); JS handler reads `data.created_at`, parses ISO timestamp + 'YYYY-MM-DD HH:MM:SS' format (SQLite default), 透過 v3.4.34 嘅 `formatDateTime()` helper 渲染 (locale-aware — en mode 顯示 "Aug 27, 2026, 12:30 AM" 而唔係 zh "2026/8/27 上午12:30")
  - `static/js/i18n.js` (+2 keys): `'report.added_at': '加入系統：{date}' / 'Added to system: {date}'` — `{date}` placeholder 由 v3.4.34 嘅 `formatDateTime()` 填充
- ✅ 0 backend / DB / schema changes — endpoint already 返 created_at (1175/1175 rows populated, 100%)
- ✅ **Verification**:
  - 275/276 tests passing — 1 pre-existing failure (`test_old_smoke_news_reach_response`, 已 fail 喺 v3.4.47 之後因為 industry news 191→713 破壞咗 smoke-prefix 排序假設, 唔關今次 change 事)
  - node --check i18n.js + extracted report_detail.html script both OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits 跨 2 modified files
  - /report/1 200 OK; new `#report-added` element + JS handler 喺 served HTML
- Commit: 4e22758

**v3.4.52 (2026-08-31) — Holdings table 成本/股 column (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/portfolio/breakdown` returns 9 fields per holding (`cost_basis`, `cost_value`, `current_price`, `market_value`, `share_of_portfolio`, `shares`, `symbol`, `unrealized_pl`, `unrealized_pl_pct`) — but `index.html` holdings table only render 6 columns (symbol/shares/price/MV/P&L/share%)。`cost_basis` (per-share cost, e.g. TSLA 200, MSFT 350, NVDA 300) 永久 silently dropped — 用戶睇到 "+74% gain" 但唔知 "bought at $200, now $348.75" at a glance
- ✅ **Fix scope** — pure frontend 3-file surgical addition (8 insertions / 2 deletions):
  - `templates/index.html` (+2): new `<th data-i18n="portfolio.holdings_cost_basis">成本/股</th>` between shares + price columns + matching `<td>${formatCurrency(h.cost_basis)}</td>` in loadPortfolioHoldings() row template
  - `static/js/i18n.js` (+2 keys): `'portfolio.holdings_cost_basis': '成本/股' / 'Cost/Share'` (mirrors holdings_* namespace)
  - `static/css/components.css` (mobile @media): update nth-child(3) → nth-child(4) so cost_basis stays visible on <480px and current_price hides (cost_basis + MV + P&L% together convey "bought vs now" — more useful on small screens)
- ✅ 0 backend / DB / schema changes — endpoint already returns cost_basis
- ✅ **Verification**:
  - 276/276 tests passing (no regressions)
  - node --check on extracted index.html script + i18n.js both OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits 跨 3 modified files
  - / 200 OK; new `<th data-i18n="portfolio.holdings_cost_basis">` + matching `<td>${formatCurrency(h.cost_basis)}</td>` rendered
  - /api/portfolio/breakdown 3 holdings (TSLA/MSFT/NVDA) all have cost_basis populated
- Commit: 8512b95

**v3.4.51 (2026-08-31) — Report detail category badge (Pattern 9b orphan field)**:

**v3.4.50 (2026-08-31) — Stocks-list 52-week range line (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/tickers` returns 19 top-level keys 包括 `week52_high` 同 `week52_low` (10/10 active tickers 全部 populated)，但 `index.html` 嘅 `renderStocks()` 只 consume 17 個 — 52-week range silently dropped between API 同 DOM。每張 stock card 顯示 symbol/sector/price/change 但冇 52W 範圍 context (而 `/stock/<sym>` detail page 已經有 high_52w/low_52w tile)
- ✅ **Fix scope** — pure frontend 4-file addition:
  - `templates/index.html` (+5): 第 3 行喺 `stock-name` 下面，顯示 `"$66.14 – $271.78"` 範圍，title 用 `t('index.week52_range')` tooltip
  - `static/js/i18n.js` (+2 keys): `'index.week52_range': '52周範圍' / '52W Range'`
  - `static/css/components.css` (+13): `.stock-week52` muted monospace 0.65rem with ellipsis (matches existing `.stock-name` pattern)
- ✅ 0 backend / DB / schema changes — endpoint already 返 data
- ✅ **Verification**:
  - 276/276 tests passing (no regressions)
  - node --check 喺 `index.html` script + `i18n.js` both OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits 跨 3 個 modified files
  - / 200 OK; `stock-week52` class 喺 source 出現 10 次 (每 ticker 一次)
- Commit: 2e7ceaa

**v3.4.49 (2026-08-31) — Report detail summary preview header (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/reports/<id>` 返 11 個 top-level keys (`analysis`, `category`, `content`, `created_at`, `file_path`, `id`, `published_at`, `source`, `summary`, `title`, `url`) — but `templates/report_detail.html` 只 wire 6 個 (title/published_at/source/url/content/analysis)。`summary` 字段 (e.g. "GLW 10-Q 年度/季度財報，提交日期 2026-05-01") 完全冇 surface — 用戶開 `/report/<id>` 只睇到 title + date + source badge，要 scroll 落原文內容先知報告講咩。99% reports 都有 populated summary (v3.4 ai_analyzer.generate_summary 已寫入)
- ✅ **Fix scope** — pure frontend 10-line addition:
  - `templates/report_detail.html` (+10): 新加 `<div id="report-summary" style="display:none; ...">` 喺 `<div id="report-date">` 下面；JS handler 讀 `data.summary`，存在就 display block，null/empty 就 keep hidden。textContent (而非 innerHTML) 防 XSS
  - 0 i18n keys 新增 (key 已存在: `report.summary: '摘要' / 'Summary'`，但呢個 page 用唔到 — summary 係 API field 名，不是 UI label)
- ✅ **Companion orphans** (not fixed in this tick — 同 endpoint 仲有 4 個 unreferenced fields，可做 future pattern 9b 應用): `category` / `created_at` / `file_path` / `id`
- ✅ **Verification**:
  - /report/1 200 OK; `report-summary` div + JS handler 喺 served HTML
  - node --check on extracted 15514-char script OK
  - gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits
  - git diff = templates/report_detail.html (+10/-0). Template-only → no restart needed
- Commit: 9e411cc

**v3.4.48 (2026-08-31) — Stock detail Next Earnings stat tile (Pattern 1 orphan field)**:
- ✅ **Bug class**: `/api/stock/<sym>/detail` returns `next_earnings: {date, title}` for 9/10 active tickers (only MRVU has none) — but `templates/stock_detail.html` stats grid only rendered 5 financial tiles (market_cap / pe_ratio / eps / high_52w / low_52w). The `next_earnings` field was silently dropped — every stock_detail page rendered `—` for what is actually a populated API field
- ✅ **Fix scope** — pure frontend 10-line addition (6th stat-item tile + JS handler + 2 i18n keys):
  - `templates/stock_detail.html` (+8): 6th `<div class="stat-item">` after low_52w tile + 4-line JS handler reading `data.next_earnings.date` via `formatDate()` (locale-aware, v3.4.34 helper)
  - `static/js/i18n.js` (+2 keys): `detail.next_earnings: '下次財報' / 'Next Earnings'`
- ✅ **Verification**:
  - 276/276 tests passing (no regressions)
  - node --check on extracted JS OK; gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF): 0 hits both files
  - `/stock/TSLA` 200 OK, `val-next-earnings` div + `data-i18n="detail.next_earnings"` rendered
  - 9/10 tickers have next_earnings date (TSLA 10/22, NVDA 11/18, IBM 10/22, MSFT 10/29, GS 10/13, MS 10/14, GLW 10/27, TE 11/12, SPCX 11/04; MRVU: none)
- ✅ Touch: templates/stock_detail.html (+8), static/js/i18n.js (+2 keys). Template-only → no restart needed but defensive restart done
- Commit: 4df93b8

**v3.4.47 (2026-08-31) — Sector endpoint cap bump (Pattern 8c companion to v3.4.46)**:
- ✅ **Bug class**: Pattern 8c — silent pagination truncation. Two sector endpoints had hardcoded caps that hid hundreds of rows from the live DB:
  - `/api/industry/<sector>/news` — Python `if len(result) >= 50: break` (SQL had LIMIT 500)
    - Technology: 50/191 visible (26% — 141 hidden)
    - Industrials: 50/171 visible (29% — 121 hidden)
    - Consumer Cyclical: 50/155 visible (32% — 105 hidden)
    - Financial Services: 50/150 visible (33% — 100 hidden)
  - `/api/sectors/<sector>/reports` — SQL `LIMIT 50` (worst offender)
    - Industrials: 50/316 visible (16% — 266 hidden)
    - Financial Services: 50/267 visible (19% — 217 hidden)
    - Technology: 50/184 visible (27% — 134 hidden)
    - Consumer Cyclical: 49/49 visible (only 1 ticker TSLA, just under cap)
- ✅ **Fix**: SQL LIMIT bumped to 2000, Python break bumped to 200 (in `/api/industry/<sector>/news`). DB has 1095 total reports — 2000 has ample headroom for growth. Worst-case JSON payload ~700KB which is fine for one-shot /industry page load
- ✅ **Smoke test**: Technology news 50 → 191, Industrials news 50 → 171, Industrials reports 50 → 316, FS reports 50 → 267. /industry page 200 OK
- ✅ **6 new regression tests** (tests/test_sector_truncation.py): test_news_returns_more_than_50, test_old_smoke_news_reach_response (inserts 50 industry news with old timestamps, asserts they reach response), test_cap_at_least_200; test_reports_returns_more_than_50, test_old_smoke_reports_reach_response, test_sql_limit_at_least_2000. 276/276 tests passing (was 270, now +6)
- ✅ **Touch**: app.py (+12/-2), tests/test_sector_truncation.py (+192, new file). Backend → restart server → 200 OK
- Commit: d04125e

**v3.4.46 (2026-08-31) — /api/reports silent truncation fix (Pattern 8c)**:
- ✅ **Bug class**: Pattern 8c — silent pagination truncation. `/api/reports?limit=500` returned only 500/1095 reports (46% coverage). All 23 `investment_bank_report` (16) + `sec_filing` (7) rows were outside the top-500 most-recent (`created_at` cutoff 2026-06-13 12:00:54; bank reports 2026-06-07 + SPCX S-1 2026-06-13 06:54:17). Dashboard reports tab's bank filter was permanently empty even though DB had data
- ✅ **Root cause**: `app.py:api_get_reports` hardcoded `min(request.args.get('limit', 50, type=int), 500)`. v3.4.20 bumped client `limit=50 → 500` (a partial fix for coverage 7% → 46%) but didn't anticipate that `ORDER BY created_at DESC` would push older-but-valuable bank reports off the end
- ✅ **Fix scope** — 2 surgical line edits:
  - `app.py:api_get_reports` cap raised 500 → 2000 (covers all 1095 + headroom; bare JSON ~660KB which is fine for one-shot dashboard load)
  - `templates/index.html:loadReports` `limit=500 → limit=2000` to match new server cap
- ✅ **Verification** — `/api/reports` returns 1095/1095 (100% coverage); all 5 tabs now non-empty (earnings:259, news/industry:667, analyst:146, **bank:23**); sum invariant holds (259+667+146+23=1095); dashboard 200 OK; `_insert_reports(50)` with old timestamps all reach the response (regression test)
- ✅ **3 new regression tests** (tests/test_report_search.py::TestReportsCap): test_limit_param_honors_request, test_old_rows_not_silently_dropped (inserts 50 rows with `created_at='2000-01-01'`, asserts all 50 reach the response), test_cap_at_least_2000 (static check on app.py source). 270/270 tests passing (was 267/267)
- ✅ **Touch**: app.py (+7/-1), templates/index.html (+4/-2), tests/test_report_search.py (+112/-1). Backend → restart server → 200 OK
- ✅ **Companion finding** (fixed in v3.4.47): `/api/industry/<sector>/news` hardcoded `LIMIT 50` (DB has 191 Technology industry news, 141 hidden) + `/api/sectors/<sector>/reports` hardcoded `LIMIT 50`. Same Pattern 8c class but sector-specific
- Commit: 534f216

**v3.4.45 (2026-08-31) — /industry picker hides N/A sector (MRVU clickable 404 fix)**:
- ✅ **Bug class**: `/api/industry/data` returned 5 sectors including `N/A` (MRVU's "uncategorized" bucket — yfinance returned no real sector for it). `/industry` rendered `N/A` as clickable card with `1 ticker · 20 reports`. Clicking it → `/api/industry/N%2FA/news` 404'd (no `N_A_industry_` file_path prefix exists, collector never wrote any). Dead-end UX
- ✅ **Fix scope** — filter at API boundary, NOT in `models.get_sectors()`:
  - `app.py:api_industry_data()` now `sectors = [s for s in models.get_sectors() if s != 'N/A']` before building per-sector response
  - `/api/sectors` (consumed by dashboard stocks-list sector pills) UNCHANGED — `index.html:822` uses `'N/A'` as `tk.sector || 'N/A'` fallback for MRVU, so dashboard's N/A pill still appears and correctly buckets MRVU
- ✅ **Smoke test** (post-restart, PID 667816): `/api/industry/data` sectors: [Consumer Cyclical, Financial Services, Industrials, Technology] (N/A gone ✓); `/api/sectors` sectors: [Consumer Cyclical, Financial Services, Industrials, N/A, Technology] (N/A preserved for dashboard ✓); /industry 200 OK 4 cards; app.py gremlin 0 hits; py_compile OK
- ✅ Touch: app.py (+12/-2). Backend → restart server → 200 OK
- Commit: 23e1f28

**v3.4.44 (2026-08-31) — Locale-aware number/currency formatting (Pattern 5e number variant)**:
- ✅ Pattern 5e number variant: 6 hardcoded `toLocaleString('en-US', ...)` call sites — even in en mode, zh fallback showed "$1,234" without locale formatting, and currency display used different number conventions
- ✅ Fix: added `formatNumber()` + `formatCurrency()` helpers in static/js/i18n.js (mirrors v3.4.34 `formatDate()` pattern) — locale picker uses `_lang` ('en' → 'en-US', else 'zh-TW')
- ✅ Wired 6 sites: `templates/index.html` (portfolio sparkline Chart.js tick callback + holdings breakdown table shares/price/MV/PnL) + `templates/system.html` (stat-portfolio-value + stat-portfolio-pnl with `+` sign prefix for PnL)
- ✅ Removed local `formatNumber()` / `formatCurrency()` definitions from both templates (now global in i18n.js)
- Commit: b470403

**v3.4.43 (2026-08-31) — Sibling subagent WIP salvage: dynamic page title translation**:
- ✅ **Bug class**: 各 template 嘅 `<title>Stocker — Dashboard</title>` 之前係 hardcoded CJK 字串, 即使用戶中途撳 `中/EN` switcher, browser tab title 永遠 stay 喺中文 — 因為 `applyTranslations()` 雖然有 title 更新邏輯, 但舊 code 只 query `[data-i18n-title]` selector, 而 `<title>` 元素從未被加過呢個 attribute
- ✅ **Fix 方案**: 新加 `<title data-page-title="X.Y">` attribute pattern — 每個 template 喺 `{% block title %}` 旁邊加新 `{% block page_title_key %}` block (e.g. `{% block page_title_key %}index.title{% endblock %}`)
- ✅ **base.html**: `<title>` 改用 `data-page-title="..."` attribute, default value `common.app_name`
- ✅ **i18n.js:1225-1248**: rewrite `applyTranslations()` 嘅 title block — `document.querySelector('title[data-page-title]')` 攞 titleEl, read attribute, `t()` resolve, 失敗時 fall back 去現有 `textContent` (no-JS graceful degradation 唔受影響)
- ✅ **1 個新 i18n key**: `common.app_name: 'Stocker'` (zh + en 同值 — app name 本身就係 "Stocker")。其餘 10 個 page-title keys (`index.title` / `alerts.title` / `banks.title` / `events.title` / `files.title` / `industry.title` / `report.title` / `sources.title` / `system.title` / `watchlists.title`) 全部早已喺 i18n.js 存在, 但從未被 reference
- ✅ **Touch**: static/js/i18n.js (+9/-2), templates/base.html (+1/-1), 10 templates (+1/-1 each)
- ✅ **Verification**: 9 個 page route 全部 200 (/, /alerts, /banks, /events, /files, /industry, /sources, /system, /watchlists); served HTML 全部有 `<title data-page-title="...">` markup; setLang('en') flow 驗證過 — t('index.title') → 'Dashboard' → document.title = 'Dashboard — Stocker'; gremlin check 0 hits 喺 11 個 modified files; node --check i18n.js + 所有 template script block OK
- ✅ Template-only → no restart needed, server 仲係 200 OK
- Commit: ab7aa8e

**v3.4.42 (2026-08-27) — index.html timeAgo() Pattern 5d fix**:
- ✅ **Bug class**: `templates/index.html:999-1008` 嘅 `timeAgo()` function 用 hardcoded English strings ('just now', 'Ns ago', 'Nm ago', 'Nh ago', 'Nd ago') — 即使其他 locale 設定已經切換, freshness badge 永遠 stay 喺英文
- ✅ Freshness badge 嘅 `title="Last updated: ..."` 亦都用 hardcoded "Last updated: " + "unknown" 字符串 (line 936)
- ✅ Sibling subagent WIP salvage: 2 files modified (i18n.js + index.html), salvage check #5 全 pass — 7 個 t() calls 全部有 matching i18n keys (4 existing + 3 new), JS node --check OK, gremlin clean (2 files), langchange listener line 1645 經 loadStocks() → timeAgo() → t() 自動 re-render
- ✅ 3 個新 zh + 3 個新 en i18n keys:
  - `time.seconds_ago: '{n} 秒前' / '{n}s ago'`
  - `index.last_updated_at: '最後更新：' / 'Last updated: '`
  - `index.last_updated_unknown: '未更新' / 'Not yet updated'`
- ✅ Touch: templates/index.html (+7/-6), static/js/i18n.js (+6 keys)。Template-only → no restart needed
- ✅ Smoke test: / 200; 7 expected t() call sites all wired; i18n.js node --check OK; freshness badge 喺 served HTML 仲 render
- Commit: 9cbdf35
**v3.4.46 (2026-08-31) — /api/reports silent truncation fix (Pattern 8c)**:
- ✅ **Bug class**: Pattern 8c — silent pagination truncation. `/api/reports?limit=500` returned only 500/1095 reports (46% coverage). All 23 `investment_bank_report` (16) + `sec_filing` (7) rows were outside the top-500 most-recent (`created_at` cutoff 2026-06-13 12:00:54; bank reports 2026-06-07 + SPCX S-1 2026-06-13 06:54:17). Dashboard reports tab's bank filter was permanently empty even though DB had data
- ✅ **Root cause**: `app.py:api_get_reports` hardcoded `min(request.args.get('limit', 50, type=int), 500)`. v3.4.20 bumped client `limit=50 → 500` (a partial fix for coverage 7% → 46%) but didn't anticipate that `ORDER BY created_at DESC` would push older-but-valuable bank reports off the end
- ✅ **Fix scope** — 2 surgical line edits:
  - `app.py:api_get_reports` cap raised 500 → 2000 (covers all 1095 + headroom; bare JSON ~660KB which is fine for one-shot dashboard load)
  - `templates/index.html:loadReports` `limit=500 → limit=2000` to match new server cap
- ✅ **Verification** — `/api/reports` returns 1095/1095 (100% coverage); all 5 tabs now non-empty (earnings:259, news/industry:667, analyst:146, **bank:23**); sum invariant holds (259+667+146+23=1095); dashboard 200 OK; `_insert_reports(50)` with old timestamps all reach the response (regression test)
- ✅ **3 new regression tests** (tests/test_report_search.py::TestReportsCap): test_limit_param_honors_request, test_old_rows_not_silently_dropped (inserts 50 rows with `created_at='2000-01-01'`, asserts all 50 reach the response), test_cap_at_least_2000 (static check on app.py source). 270/270 tests passing (was 267/267)
- ✅ **Touch**: app.py (+7/-1), templates/index.html (+4/-2), tests/test_report_search.py (+112/-1). Backend → restart server → 200 OK
- ✅ **Companion finding** (not fixed in this tick): `/api/industry/<sector>/news` hardcoded `LIMIT 50` (DB has 191 Technology industry news, 141 hidden) + `/api/sectors/<sector>/reports` hardcoded `LIMIT 50`. Same Pattern 8c class but sector-specific — log as next-tick item
- Commit: 534f216

**Server**: localhost:5000（python app.py 跑緊，restart 完成 200 OK）
**Branch**: main
**Remote**: git@github.com:macauhermes/Stocker.git

**v3.4.41 (2026-08-27) — Sibling subagent WIP salvage (2 commits, 8 files)**:
- ✅ **Cron tick WIP salvage**: `git status` 顯示 8 個 modified files 嚟自兩個 sibling subagent runs (~12h + ~6h old) — salvage check #5 全 pass: CACHE_HITS/CACHE_MISSES defined + wired, 6 個 i18n keys 各 zh+en 出現 2 次, 22 t() keys 全部 hit, JS node --check OK (6 templates), gremlin clean (8 files)
- ✅ **Commit 1 — e5aca93 [P3] metrics**: surface 3 個 Prometheus counters 到 /system admin page — cache{hits,misses,hit_rate%}, data_source_requests{by_source{yfinance/yahoo_direct/stooq/coingecko}}, health_check{by_status{healthy/degraded/unhealthy}}。Pre-create expected labels (Pitfall 15) 所以 /metrics 第一行就見 0 而唔係空白。renderCounters() generalize 攞 flat dict + nested dict (by_source / by_status 都解開做 "label: count · ..." segments)。6 zh + 6 en i18n keys (system.cnt_cache / .cnt_data_sources / .cnt_health_check)
- ✅ **Commit 2 — 560de92 [P3] i18n**: Pattern 5d 升級 — 22 個 static `data-i18n="..."` attributes 喺 JS template literals (`el.innerHTML = \`...\${t('...')}...\``) 換做 `${t('...')}` direct calls。之前 applyI18n() 喺 DOMContentLoaded 跑嗰陣呢啲 empty-state DOM 仲未存在 (loadGroups/loadSources/etc 嘅 fetch 先 inject)，所以 English mode 永遠見到硬編碼 CJK 字串。22 個 t() key 全部喺 i18n.js 已有 (0 missing)。Touch 5 templates: index.html (groups dashboard), report_detail.html (rating + empty state), sources.html (custom sources empty), stock_detail.html (news empty/filter-empty + save button), watchlists.html (groups empty)
- ✅ **Smoke test**: services/metrics.py 重啟後 → /api/metrics/summary 返 cache={hits:1,misses:11,hit_rate:8.3} + data_source_requests{...} + health_check{healthy:1,...} 全 block surface; 6 pages 200 (/, /system, /watchlists, /sources, /stock/TSLA, /api/metrics/summary); /health 觸發後 HEALTH_CHECK counter inc 1 = wire-up 確認
- ✅ **Touch**: services/metrics.py (+39), templates/system.html (+19), static/js/i18n.js (+6 keys), 5 templates (+14/-14 lines total)。Commit 1 backend 改 → restart server; Commit 2 template-only → no restart needed

**v3.4.40 — covered by e5aca93 above (3 個 Prometheus counter blocks)**

**v3.4.39 (2026-08-27) — Pattern 11 second sweep: bare native alert() in watchlists.html**:
- ✅ **Bug class**: v3.4.37 sweep 用 `grep -rn "alert(t("` 只 catch i18n-wrapped alert calls，漏咗 bare-string calls。`templates/watchlists.html` 有 6 個 native `alert()` (2× `alert(data.error || 'Error')` + 4× `alert('Network error')`) — v3.4.37 convert `alert(t(...))` 但漏咗呢啲，consistency 仍然 broken
- ✅ 改用 broadened regex `grep -rnE '\b(alert|confirm|prompt)\(' templates/` — 9 hits total (6 alert in watchlists + 3 confirm 喺 index.html/archive + watchlists/deleteGroup + sources.html — 3 個 confirm 留低因為 destructive action confirmation 係 conventional UX)
- ✅ 6 個 alert 全部換做 showToast，mirror alerts.html pattern：server error → `showToast(t('watchlists.save_error', { msg: data.error || res.status }), 'error')`，network exception → `showToast(t('watchlists.network_error'), 'error')`
- ✅ `removeTicker()` 順手加 `resp.ok` check + JSON error parse — 之前 silent swallow 全部失敗 (冇 user feedback)，而家失敗會出 toast。Scope-justified 因為呢個 change 將 silent-failure UX 變做 proper error reporting
- ✅ 3 zh + 3 en i18n keys: `watchlists.save_error` ('儲存失敗：{msg}'/'Save failed: {msg}'), `watchlists.network_error` ('網絡錯誤'/'Network error'), `watchlists.remove_error` ('刪除失敗：{msg}'/'Remove failed: {msg}')
- ✅ Touch: templates/watchlists.html (+12/-7), static/js/i18n.js (+6 keys). Template-only → no restart needed
- ✅ Smoke test: /watchlists 200; showToast total 52 → 59; served HTML 0 alert( 留低; node --check 兩 file OK; gremlin clean; 3 i18n key 喺 i18n.js 各 2 次 (zh + en)
- Commit: e64a9c5

|**v3.4.38 (2026-08-27) — Events calendar langchange re-render fix (Pattern 5d)**:
|- ✅ Pattern 5d bug class: `templates/events.html:168` 用 `const DAYS = t('events.days') || ['日',...];` — `const` 喺 script load 時 evaluate 一次，之後永遠唔變。即使用戶中途撳 `中/EN` switcher，calendar header 嘅「日/一/二/...」永遠 stay 喺中文（除非 reload page）
|- ✅ 同時發現 events.html 完全冇 `window.addEventListener('langchange', ...)` — index.html / files.html / alerts.html / industry.html / stock_detail.html / system.html 全部有，淨係 events.html 漏咗
|- ✅ 兩重 fix:
|  1. `const DAYS = ...` 改成 `function getDays()` — 每次 `loadCalendar()` call 都重新 fetch 當前 locale 嘅 day names
|  2. 新增 `window.addEventListener('langchange', () => { loadCalendar(); renderUpcoming(); })` — 切 language 即時 re-render calendar header + month title + upcoming list
|- ✅ Detection recipe (refined Pattern 5d): `grep -rnE "^\s*(let|const|var)\s+[A-Z_]+\s*=\s*t\(" templates/` — 每個 hit 都係 cached-at-load-time 嘅 i18n value，必須改做 function call 或者喺 langchange handler 重新 fetch
|- ✅ Touch: templates/events.html (+16/-2). Template-only → no restart needed
|- ✅ Smoke test: /events 200; 3 events in Aug 2026 (IBM/MSFT dividends + NVDA earnings 8/27); node --check OK; gremlin clean
|- Commit: 4b1e3a6

**v3.4.37 (2026-08-27) — UX consistency: native alert() → showToast() in alerts + watchlists**:
- ✅ **Bug class**: `templates/alerts.html` 同 `templates/watchlists.html` 用 native `alert()` (window.alert, blocking modal) — 其他 7 templates 全部用 `base.html:144` 嘅 `showToast()` (auto-dismiss 3s, non-blocking)。兩 files 用 `alert(t(...))` 13 次, 全部係 form validation / save error / 確認回饋嘅 moment
- ✅ Alerts.html 仲有一個 local shim `function alert(msg) { window.alert(msg); }` (line 336) — author 為咗避免 shadowing 自己定義嘅 local `alert()` 變數 (used for re-render check) 而特登寫嘅 — 即係話連 form 填錯都係 popup 嚇 user
- ✅ 13 個 `alert(t(...))` 全部換做 `showToast(t(...), type)`:
  - Form validation: `warning` toast (橘色) — symbol/price required, group name required, ticker symbol required
  - Save/load/update/rearm/delete errors: `error` toast (紅色)
  - checkAllAlerts success: 拆 2 個 toast (count 用 success 綠色, per-line details 用 warning 橘色, joined with ` · ` 因為 toast 唔 render newlines)
  - checkAllAlerts no-trigger: `info` toast (藍色)
- ✅ 移除 `function alert(msg) { window.alert(msg); }` local shim — 而家直接用 base.html global `showToast()`
- ✅ Detection recipe: `grep -rn "alert(t(" templates/` — 0 hits 證明 clean (search-time 2 files affected, both 0 after fix)
- ✅ Consistency check: 38 prior `showToast(` + 14 新加 = 52 個 `showToast(` total 喺所有 templates — 0 個 native blocking `alert()` left in form flows
- ✅ Pure UX — Touch: templates/alerts.html (+12/-15), templates/watchlists.html (+2/-2). Zero backend / DB / i18n changes (toast component already exists in base.html:144)
- ✅ Smoke test: /alerts 200 (11 showToast in served HTML, 0 alert), /watchlists 200 (2 showToast, 0 alert), POST /api/alerts/check 200 ({count: 0, triggered: []})
- ✅ JS node --check 11740 chars OK, gremlin clean (U+FFFD/U+00AD/U+200B/U+FEFF 0 hits)
- ✅ Template-only → no restart needed
- Commit: cb427f4

**v3.4.36 (2026-08-27) — Watchlist group ticker count i18n fix (Pattern 5d)**:
- ✅ Pattern 5d bug class: `templates/index.html:1418` 內 JS template literal `<span>${g.ticker_count} 股</span>` 用 hardcoded CJK 「股」字 — applyI18n() 只 rewrites static HTML markup, 完全唔 touch runtime-injected DOM
- ✅ 結果: 即使切到 English mode, 每個 watchlist group 嘅 "{n} 股" count 都永遠 stay 喺中文
- ✅ i18n key `watchlists.ticker_count: '{n} 股'` (zh) / `'{n} stocks'` (en) 已經喺 i18n.js 存在 (v3.3 已加), 但係從未被 reference
- ✅ 改成 `t('watchlists.ticker_count', {n: g.ticker_count})` — `{n}` placeholder substitution 由 i18n.js:1135 replace() helper 處理
- ✅ Companion fix: `loadGroupsDashboard()` 之前 missing 喺 langchange handler — 即使用戶切 language, groups dashboard 都唔會 re-render。V3.4.36 加返 `loadGroupsDashboard()` 落 `window.addEventListener('langchange', ...)` 嘅 callback 列表
- ✅ Detection recipe (refined): `for tpl in templates/ static/js/; do grep -nE '[一-鿿]' $tpl/*.html $tpl/*.js; done | grep -v 'data-i18n' | grep -v 'static/js/i18n.js'` — 任何命中都係 hardcoded CJK string in JS context 需要 fix
- ✅ Touch: templates/index.html (+3/-1). Template-only → no restart needed, / 200 OK
- Commit: 975f827

**v3.4.35 (2026-08-27) — Pattern 5e follow-up: banks.html last_check locale**:
|- ✅ Pattern 5e audit caught 1 remaining site that v3.4.34 grep missed: `templates/banks.html:172` — `new Date(bank.last_check).toLocaleDateString()` had NO locale argument, silently fell back to browser default 喺英文 mode 都出中文/瀏覽器默認格式
|- ✅ 改成 `formatDate(bank.last_check)` (i18n.js:1150 helper) — 但 v3.4.34 grep 用 `toLocaleDateString\('zh-TW'\)` 嘅 regex **根本 miss 咗冇 arg 嘅 call**，所以呢個 bug survive 咗 1 個 tick
|- ✅ Detection recipe 修正: `grep -rnE 'new Date\([^)]*\)\.toLocale(?:Date|Time)?String\(\)' templates/ static/js/` (空 arg 都 catch) — 0 hits 證明 clean
|- ✅ Touch: templates/banks.html (+1/-1). formatDate helper battle-tested already (handle null/invalid → '—')
|- ✅ Template-only → no restart needed, /banks 200 OK
|- Commit: 0260bca
|
|**v3.4.34 (2026-08-27) — Locale-aware date formatting (Pattern 5e)**:
- ✅ Pattern 5e bug class: 11 hardcoded `toLocaleDateString('zh-TW')` calls across 7 templates — 喺 English mode dates 仍然 render 中文格式 ("2026/8/27") 而唔係用戶期望嘅英文格式 ("Aug 27, 2026")
- ✅ Root cause 同 Pattern 5d 一樣: applyI18n() 只 rewrites static markup 經 `data-i18n`, 唔能夠攔截 dynamic JS Date formatting — 兩者都係 "hardcoded i18n assumption in JS" 嘅 sub-class
- ✅ Fix: 加 `formatDate(date, opts)` + `formatDateTime(date, opts)` 喺 `static/js/i18n.js` — 用 `_lang` 揀 locale (Chinese mode → 'zh-TW', English mode → 'en-US')，null/invalid → '—'
- ✅ 11 個 hardcoded call sites 全部 replace: index.html (3: event banner / reports / archived) + files.html (1) + report_detail.html (1) + stock_detail.html (4: event banner / news / reports / events) + industry.html (1) + banks.html (1)
- ✅ Detection recipe: `grep -rnE "toLocaleDateString\\('zh-TW'\\)|toLocaleString\\('zh-TW'\\)" templates/ static/js/` — 任何命中都係 locale-bug（除非係刻意嘅 zh-only page)
- ✅ Verification: node --check OK (i18n.js + 6 template scripts), gremlin clean (7 files), 6 pages 200 (/, /industry, /banks, /files, /stock/TSLA, /report/1), served HTML 有 formatDate(...) call sites, served i18n.js 有 function definition
- ✅ Pure frontend — Touch: static/js/i18n.js (+26), 6 templates (+11/-11)。Template-only → no restart needed
- Commit: a490cd3

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

**v3.4.51 (2026-08-31) — Report detail category badge (Pattern 9b orphan field)**:
- ✅ **Bug class**: `/api/reports/<id>` returns 11 keys but `templates/report_detail.html` 只 wire 7 個 (title/published_at/summary/source/url/content/analysis) — `category` field 永久 silently dropped。每個 /report/<id> page 顯示 title/date/summary/source 但完全冇 indication 屬於咩類型報告 (earnings / industry / analyst_report / investment_bank_report / sec_filing)。用戶開 S-1 招股書 vs GLW 10-Q vs GS 投行報告 vs 行業新聞 → 標題以外冇任何 visual cue
- ✅ **Fix scope** — pure frontend 26-line addition:
  - `templates/report_detail.html` (+24): new `#report-category-badge` div 喺 header (next to source badge), JS block render 5 個 category-specific icon + color (matches index.html renderReports() mapping)：earnings=assessment/綠, industry|news=article/橘, analyst_report=analytics/紫, investment_bank_report=account_balance/藍, sec_filing=gavel/橘。Unknown value 落回 default 藍色 description icon
  - `static/js/i18n.js` (+2 keys): `files.cat.investment_bank_report: '投行報告' / 'Investment Bank Report'` — 其餘 4 個 category i18n keys 已經喺 i18n.js 存在 (earnings/analyst_report/industry/sec_filing)
- ✅ **Smoke test**: 5 個不同 category page 全部測試過 (id=1 earnings, 16 industry, 57 analyst_report, 209 investment_bank_report, 570 sec_filing) — 全部 200 OK + 全部 5 個 category 喺 JS mapping 覆蓋 + category-badge div 喺 served HTML 存在
- ✅ node --check (extracted report_detail.html JS + i18n.js) OK, gremlin check (U+FFFD/U+00AD/U+200B/U+FEFF) 0 hits 兩個 files
- ✅ 276/276 tests passing (no regressions)
- ✅ / 200 OK, /report/1 200 OK
- Touch: templates/report_detail.html (+24), static/js/i18n.js (+2 keys). Template-only → no restart needed, server 仲係 200 OK
- Commit: d2525a4

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

## 流程

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
