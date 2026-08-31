/**
 * Stocker i18n — 繁體中文 / English
 * Usage: t('key') returns translated string
 *        setLang('en') / setLang('zh') switches language
 *        HTML elements with data-i18n="key" are auto-translated
 */
const I18N = {
  zh: {
    // Nav
    'nav.dashboard': '主頁',
    'nav.industry': '行業',
    'nav.files': '檔案',
    'nav.login': '登入',
    'nav.banks': '投行',
    'nav.sources': '數據源',
    'nav.watchlists': '分組',
    'nav.calendar': '日曆',
    'nav.search_placeholder': '搜尋股票代碼...',

    // Common
    'common.app_name': 'Stocker',
    'common.loading': '載入中...',
    'common.error': '載入失敗，請稍後重試',
    'common.retry': '重試',
    'common.save': '保存',
    'common.cancel': '取消',
    'common.confirm': '確認',
    'common.close': '關閉',
    'common.back': '返回',
    'common.all': '全部',
    'common.none': '無',
    'common.date': '日期',
    'common.action': '操作',
    'common.name': '名稱',
    'common.category': '分類',
    'common.size': '大小',
    'common.source': '來源',
    'source.yfinance': 'Yahoo Finance',
    'source.yahoo_direct': 'Yahoo 直連',
    'source.stooq': 'Stooq',
    'source.coingecko': 'CoinGecko',
    'source.custom': '自訂來源',
    'source.unknown': '未知',
    'common.untitled': '無標題',
    'common.enabled': '啟用',
    'common.disabled': '停用',
    'common.edit': '編輯',
    'common.delete': '刪除',
    'common.add': '新增',
    'common.save': '保存',
    'common.saving': '保存中...',
    'common.saved': '已儲存',
    'common.deleted': '已刪除',
    'common.updated': '已更新',
    'common.required_field': '必填',
    'common.delete_confirm': '確定刪除？',
    'common.load_error': '載入失敗',

    // Index page
    'index.title': '主頁',
    'index.last_updated_at': '最後更新：',
    'index.last_updated_unknown': '未更新',
    'index.tab.stocks': '股票',
    'index.tab.reports': '報告',
    'index.tab.archived': '歸檔',
    'index.tab.groups': '分組',
    'index.add': '+ 新增',
    'index.add_ticker': '新增追蹤',
    'index.symbol_placeholder': '輸入股票代碼 (如 TSLA)',
    'index.confirm_add': '確認新增',
    'index.event_dismiss': '已知悉',
    'index.empty_stocks': '尚無追蹤股票，點擊「+ 新增」開始',
    'index.enter_symbol': '請輸入股票代碼',
    'index.adding': '新增中...',
    'index.added': '已新增',
    'index.add_title': '新增追蹤股票',
    'index.watchlist': '追蹤分組',
    'index.groups_empty': '尚未建立追蹤分組',
    'index.groups_create': '建立分組',
    'index.groups_empty_group': '空',
    'index.groups_manage': '管理分組',

    // v3.4.33 — Pattern 5d: hardcoded CJK in JS toast/badge strings
    'index.refresh_reason_us_market_open': '盤中',
    'index.refresh_reason_us_extended_hours': '盤後',
    'index.refresh_reason_us_off_hours': '收盤',
    'index.refresh_reason_weekend': '週末',
    'index.preview_loading': '載入中…',

    // Stock table
    'stock.ticker': '代碼',
    'stock.name': '名稱',
    'stock.price': '現價',
    'stock.change': '漲跌%',
    'stock.prev_close': '昨收',
    'stock.mini_chart': '走勢圖',
    'stock.shares': '持倉',
    'stock.pnl': '損益',
    'stock.pnl_pct': '損益%',
    'stock.archive': '歸檔',
    'stock.restore': '恢復',
    'stock.archived_date': '歸檔日期',
    'stock.sector': '行業',
    'stock.symbol': '代碼',
    'stock.action': '操作',
    'stock.archived': '已歸檔',
    'stock.restored': '已恢復',
    'stock.compare': '比較',
    'stock.select_compare': '選擇比較股票',
    'stock.clear_compare': '清除比較',
    'stock.chart_line': '折線圖',
    'stock.chart_candlestick': '陰陽燭',
    'stock.candle_open': '開',
    'stock.candle_high': '高',
    'stock.candle_low': '低',
    'stock.candle_close': '收',

    // Archive
    'archive.confirm': '確定要歸檔 {symbol} 嗎？已下載的報告將保留。',
    'archive.empty': '暫無歸檔的股票',

    // Reports list
    'reports.empty': '尚無報告',
    'reports.tab.all': '全部',
    'reports.tab.earnings': '財報',
    'reports.tab.news': '新聞',
    'reports.tab.analyst': '券商分析',
    'reports.tab.bank': '投行',
    'reports.search_placeholder': '搜尋報告標題或摘要...',  // v3.4.20
    'reports.source_filter': '全部來源',                    // v3.4.20
    'reports.source_all': '全部來源',                       // v3.4.20
    'reports.filter_count': '{shown}/{total} 份',           // v3.4.20
    'reports.empty_filtered': '沒有符合篩選條件的報告',     // v3.4.20

    // Stock detail
    'detail.back': '返回',
    'detail.chart_loading': '載入圖表中...',
    'detail.indicators': '指標',
    'detail.info': '基本面',
    'detail.market_cap': '市值',
    'detail.pe_ratio': 'PE 比率',
    'detail.eps': '每股盈利',
    'detail.high_52w': '52周最高',
    'detail.low_52w': '52周最低',
    'detail.next_earnings': '下次財報',
    'detail.news': '最近新聞',
    'detail.no_news': '暫無新聞',
    'detail.holdings': '持倉管理',
    'detail.shares_label': '持倉數量',
    'detail.cost_label': '成本價',
    'detail.save_holdings': '保存',
    'detail.event_dismiss': '已知悉',
    'detail.no_data': '暫無數據',
    'detail.load_stock_error': '載入股票資料失敗',
    'detail.load_chart_error': '載入圖表失敗',
    'detail.holdings_updated': '持倉已更新',
    'detail.holdings_update_error': '保存失敗',
    'detail.refreshing': '更新中...',
    'detail.refresh_error': '更新失敗',
    'detail.refreshed': '已更新',
    'detail.event_dismissed': '已標記已知悉',
    'detail.event_dismiss_error': '操作失敗',

    // News filter row (v3.4.25)
    'detail.news_sort_label': '排序',
    'detail.news_sort_newest': '最新優先',
    'detail.news_sort_oldest': '最早優先',
    'detail.news_publisher_all': '全部來源',
    'detail.news_count': '{shown}/{total} 條',
    'detail.news_no_match': '冇符合篩選嘅新聞',
    'detail.news_try_other': '試下揀「全部來源」或另一個來源',
    'detail.news_untitled': '無標題',

    // Events list (v3.4.27)
    'detail.events_title': '事件時間表',
    'detail.events_empty': '暫無事件',
    'detail.events_count': '{n} 個事件',
    'detail.events_upcoming_tag': '即將',
    'detail.events_dismissed_tag': '已知悉',
    'detail.reports_title': '相關報告',
    'detail.reports_count': '{n} 份',
    'detail.reports_empty_title': '暫無報告',
    'detail.reports_empty_hint': '之後有 10-K、10-Q 或分析師報告就會喺度顯示',

    // Reports
    'report.title': '報告',
    'report.summary': '摘要',
    'report.added_at': '加入系統：{date}',
    'report.analysis': 'AI 分析',
    'report.original': '原文',
    'report.no_analysis': 'AI 分析尚未生成',
    'report.collect': '收集報告',
    'report.collecting': '收集中...',
    'report.collect_done': '收集完成',
    'report.view_source': '查看來源',
    'report.source_external': '原文儲存於外部連結',
    'report.no_source': '暫無原文內容',
    'report.load_error': '載入報告失敗',
    'report.rating_summary': '評級摘要',
    'report.analysts': '位分析師',
    'report.rating.strongBuy': '強力買入',
    'report.rating.buy': '買入',
    'report.rating.hold': '持有',
    'report.rating.sell': '賣出',
    'report.rating.strongSell': '強力賣出',
    'report.rating.period': '期間',
    'report.rating.current': '當前',
    'report.rating.1m': '1個月前',
    'report.rating.2m': '2個月前',
    'report.rating.3m': '3個月前',
    'report.rating.4m': '4個月前',
    'report.rating.5m': '5個月前',
    'report.ticker_badge': '查看 {symbol} 詳細資料',            // v3.4.57 — Pattern 9b orphan field (ticker_symbol)

    // Industry
    'industry.title': '行業新聞與報告',
    'industry.collect': '收集行業新聞',
    'industry.collecting': '收集中...',
    // v3.4.33 — Pattern 5d: hardcoded CJK in collectNews() toast strings
    'industry.collect_done': '收集完成！',
    'industry.collect_failed': '收集失敗',
    'industry.network_error': '網絡錯誤',
    'industry.select': '選擇行業查看報告',
    'industry.reports': '報告',
    'industry.tickers': '追蹤標的',
    'industry.no_sectors': '暫無行業分類，請先新增追蹤股票',
    'industry.no_reports': '該行業暫無報告',
    'industry.load_error': '載入行業失敗',
    'industry.report_error': '載入報告失敗',
    'industry.close': '關閉',
    'industry.nav': '行業',
    // Industry News panel (v3.4.16)
    'industry.news': '行業新聞',
    'industry.no_news': '該行業暫無新聞',
    'industry.news_error': '載入行業新聞失敗',
    'industry.news_count': '{n} 篇',

    // Sector reports filter row (v3.4.22)
    'industry.filter_all': '全部',
    'industry.filter_earnings': '財報',
    'industry.filter_analyst': '分析師',
    'industry.filter_sec': '招股書',
    'industry.filter_industry': '新聞',
    'industry.sort_newest': '最新優先',
    'industry.sort_oldest': '最早優先',
    'industry.count_filtered': '顯示 {shown} / {total} 份',
    'industry.count_total': '共 {total} 份',
    'industry.no_filter_match': '冇符合篩選嘅報告',
    'industry.try_other_filter': '試下揀另一個類別',

    // Files
    'files.title': '檔案管理',
    'files.filename': '檔案名稱',
    'files.download': '下載',
    'files.view_report': '查看報告',
    'files.load_error': '載入檔案列表失敗',
    'files.empty': '暫無檔案',

    // File categories
    'files.cat.all': '全部',
    'files.cat.earnings': '財報',
    'files.cat.analyst_report': '分析師報告',
    'files.cat.news': '新聞',
    'files.cat.sec_filing': 'SEC 文件',
    'files.cat.industry': '行業報告',
    'files.cat.investment_bank_report': '投行報告',

    // Files page filter row (v3.4.23)
    'files.search_placeholder': '搜尋檔名...',
    'files.sort_newest': '最新優先',
    'files.sort_oldest': '最早優先',
    'files.sort_name': '檔名排序',
    'files.sort_size_desc': '檔案最大',
    'files.count_filtered': '顯示 {shown} / {total} 份',
    'files.count_total': '共 {total} 份',
    'files.no_filter_match': '冇符合篩選嘅檔案',
    'files.try_other_filter': '試下揀另一個檔案',

    // Events Calendar
    'events.title': '事件日曆',
    'events.sync': '同步',
    'events.syncing': '同步中...',
    'events.sync_done': '已同步 {n} 個事件',
    'events.sync_error': '同步失敗',
    'events.upcoming': '即將到來',
    'events.empty': '暫無即將到來嘅事件',
    'events.empty_hint': '點擊「同步」從 Yahoo Finance 獲取',
    'events.type.all': '全部',
    'events.type.earnings': '盈報',
    'events.type.dividend': '派息',
    'events.type.sec_filing': 'SEC',
    'events.filter_count': '{shown}/{total} 個',
    'events.filtered_empty': '冇呢類型嘅事件',
    'events.hide_dismissed': '隱藏已 dismiss',
    'events.show_dismissed': '顯示已 dismiss',
    'events.dismissed_tag': '已 dismiss',
    'events.dismiss_tooltip': '標記為已知悉',
    'events.dismissed': '已標記為已知悉',
    'events.dismiss_error': 'dismiss 失敗',
    'events.only_dismissed': '所有事件都已被 dismiss',
    'events.only_dismissed_hint': '撳「顯示已 dismiss」睇返',
    'events.days': ['日', '一', '二', '三', '四', '五', '六'],
    'events.year_month': '{year} 年 {month} 月',

    // Custom Sources
    'sources.title': '自訂數據源',
    'sources.desc': '為任何基金 / 債券 / 理財產品接入歷史價（JSONPath + URL）。',
    'sources.desc2': '自訂源喺歷史價解析鏈中優先於 Yahoo。',
    'sources.add_title': '新增自訂數據源',
    'sources.edit_title': '編輯自訂數據源',
    'sources.name': '名稱',
    'sources.name_placeholder': '例：My Pension Fund',
    'sources.symbol_replaced': '{symbol} 會被替換',
    'sources.optional_fields': '可選欄位（Open / High / Low / Volume / 過濾）',
    'sources.filter_label': 'Symbol 過濾路徑（只取對應 symbol）',
    'sources.notes': '備註',
    'sources.notes_placeholder': '例：每日 23:00 更新',
    'sources.empty_title': '未設定任何自訂源',
    'sources.enabled': '● 啟用',
    'sources.disabled': '○ 停用',
    'sources.required_error': 'name, url, date_path, price_path 全部必填',
    'sources.save_error': '儲存失敗',
    'sources.delete_confirm': '確定刪除此自訂源？',
    'sources.delete_error': '刪除失敗',

    // Banks
    'banks.title': '投行觀察名單',
    'banks.check_all': '全部檢查',
    'banks.tab.list': '投行列表',
    'banks.tab.reports': '最新報告',
    'banks.add_title': '新增投行',
    'banks.edit_title': '編輯投行',
    'banks.name': '投行名稱',
    'banks.name_placeholder': '例如: Goldman Sachs',
    'banks.short_name': '簡稱',
    'banks.short_name_placeholder': '例如: GS',
    'banks.website': '網站 URL',
    'banks.report_url': '報告頁面 URL',
    'banks.report_url_hint': '填寫投行的研究報告或 Insights 頁面 URL',
    'banks.empty_title': '尚未新增任何投行',
    'banks.empty_hint': '點擊「新增」按鈕開始追蹤投行報告',
    'banks.last_check': '上次檢查: ',
    'banks.never_checked': '尚未檢查',
    'banks.action.check': '檢查新報告',
    'banks.action.edit': '編輯',
    'banks.reports_empty_title': '暫無報告',
    'banks.reports_empty_hint': '新增投行後點擊「檢查新報告」獲取最新報告',
    'banks.action.view': '查看',
    'banks.action.download': '下載',
    'banks.downloaded': '已下載',
    'banks.name_required': '請輸入投行名稱',
    'banks.url_required': '請輸入報告頁面 URL',
    'banks.save_error': '保存失敗',
    'banks.action_error': '操作失敗',
    'banks.checking': '檢查中...',
    'banks.check_done': '檢查完成: {n} 份新報告',
    'banks.checking_all': '正在檢查所有投行...',
    'banks.check_all_done': '檢查完成: 共 {n} 份新報告',
    'banks.downloading': '下載中...',
    'banks.download_done': '下載完成',
    'banks.filter_all': '全部',
    'banks.filter_enabled': '已啟用',
    'banks.filter_undownloaded': '未下載',
    'banks.count_filtered': '{shown}/{total} 個',
    'banks.empty_filtered_title': '過濾後無結果',
    'banks.empty_filtered_hint': '切換到「全部」看完整列表',

    // Watchlists
    'watchlists.title': '追蹤分組',
    'watchlists.add_group': '新增分組',
    'watchlists.desc': '將追蹤嘅股票分組管理（例如：科技股、金融股、我嘅持倉）。',
    'watchlists.add_title': '新增分組',
    'watchlists.edit_title': '編輯分組',
    'watchlists.group_name': '分組名稱',
    'watchlists.group_name_placeholder': '例：科技股',
    'watchlists.description': '說明',
    'watchlists.description_placeholder': '（選填）',
    'watchlists.color': '顏色',
    'watchlists.add_ticker': '加入股票',
    'watchlists.ticker_symbol': '股票代碼',
    'watchlists.empty_title': '尚未建立任何追蹤分組',
    'watchlists.empty_hint': '點擊「新增分組」開始',
    'watchlists.ticker_count': '{n} 股',
    'watchlists.name_required': '請輸入分組名稱',
    'watchlists.delete_confirm': '刪除「{name}」？股票唔會被刪除。',
    'watchlists.all_added': '所有股票都已經加入咗',
    'watchlists.symbol_required': '請輸入股票代碼',
    'watchlists.save_error': '儲存失敗：{msg}',
    'watchlists.network_error': '網絡錯誤',
    'watchlists.remove_error': '刪除失敗：{msg}',

    // Price Alerts (v3.4)
    'alerts.title': '價格提醒',
    'alerts.add': '新增提醒',
    'alerts.edit': '編輯提醒',
    'alerts.desc': '設定價格閾值，當股票價格到達指定範圍時自動產生提醒事件。每個提醒只會觸發一次，需重新啟用（rearm）才會再次觸發。',
    'alerts.threshold_high': '升至 ≥',
    'alerts.threshold_low': '跌至 ≤',
    'alerts.threshold_high_full': '升至 ≥ 目標價',
    'alerts.threshold_low_full': '跌至 ≤ 目標價',
    'alerts.target_price': '目標價 (USD)',
    'alerts.rearm': '重新武裝',
    'alerts.enabled': '啟用',
    'alerts.disabled': '已停用',
    'alerts.triggered_at': '已觸發：{time}',
    // v3.4.60 — Pattern 9b orphan field: alert cards now show when the alert was created
    'alerts.created_at': '建立於：{time}',
    'alerts.note': '備註',
    'alerts.note_placeholder': '（選填）例：突破阻力位',
    'alerts.symbol_placeholder': 'TSLA',
    'alerts.target_placeholder': '例：300.00',
    // Page actions
    'alerts.check_all': '立即檢查',
    'alerts.check_all_title': '立即檢查所有啟用中的提醒',
    // Filter chips
    'alerts.filter_all': '全部',
    'alerts.filter_enabled': '啟用中',
    'alerts.filter_disabled': '已停用',
    // Modal form labels
    'alerts.field_symbol': '股票代碼 *',
    'alerts.field_type': '觸發類型 *',
    'alerts.field_target': '目標價 (USD) *',
    'alerts.required_field': '必填',
    // Status / empty / errors
    'alerts.empty': '冇提醒。點擊「新增提醒」開始設定。',
    'alerts.empty_short': '冇提醒',
    'alerts.load_error': '載入失敗：{msg}',
    'alerts.save_error': '儲存失敗：{msg}',
    'alerts.rearm_error': '重新武裝失敗：{msg}',
    'alerts.delete_error': '刪除失敗：{msg}',
    'alerts.update_error': '更新失敗：{msg}',
    'alerts.symbol_required': '請輸入股票代碼',
    'alerts.price_required': '請輸入有效的目標價',
    'alerts.check_error': '檢查失敗：{msg}',
    'alerts.check_triggered': '已觸發 {n} 個提醒！',
    'alerts.check_none': '沒有提醒被觸發。',
    'alerts.check_line': '{symbol} {type} ${threshold} (now ${current})',
    // Confirm dialog
    'alerts.delete_confirm_title': '確認',
    'alerts.delete_confirm_msg': '確定要刪除 {symbol} 嘅提醒？此操作無法復原。',
    // Card actions (titles)
    'alerts.action_disable': '停用',
    'alerts.action_enable': '啟用',
    'alerts.action_rearm_title': '重新武裝 (rearm)',
    'alerts.action_edit_title': '編輯',
    'alerts.action_delete_title': '刪除',
    'alerts.note_prefix': '備註：',

    // Portfolio summary (v3.4.2)
    'portfolio.total_value': '總市值',
    'portfolio.total_cost': '總成本',
    'portfolio.total_pnl': '總損益',
    'portfolio.pnl_pct': '損益百分比',
    'portfolio.holdings_count': '持倉數',
    'portfolio.change_30d': '30日變化',
    'portfolio.history_title': '投資組合 30 日歷史',
    'portfolio.history_empty': '暫無歷史快照 — 每日 20:00 自動拍攝',
    'portfolio.snapshot_today': '今日快照：{date}',
    'portfolio.unrealized': '未實現損益',
    'portfolio.dashboard_no_history': '尚未有投資組合歷史快照',
    'portfolio.dashboard_value_only': '當前總市值',
    'portfolio.dashboard_change': '較 30 日前',
    'portfolio.sparkline_meta': '{n}日 · {sign}{delta} ({sign}{pct}%)',
    'portfolio.sparkline_title': '市值走勢 (近30日)',
    'portfolio.holdings_title': '持倉明細',
    'portfolio.holdings_symbol': '代碼',
    'portfolio.holdings_shares': '股數',
    'portfolio.holdings_cost_basis': '成本/股',
    'portfolio.holdings_cost_value': '成本合計',
    'portfolio.holdings_price': '現價',
    'portfolio.holdings_market_value': '市值',
    'portfolio.holdings_unrealized_pl': '未實現損益',
    'portfolio.holdings_share': '佔比',
    'portfolio.holdings_as_of': '資料時間：{time}',            // v3.4.58 — Pattern 9b orphan field (breakdown timestamp)
    'portfolio.holdings_empty': '暫無持倉',
    'portfolio.holdings_count_total': '{n} 個持倉 · 總市值 {total}',
    'portfolio.actions_title': '快捷操作',
    'portfolio.capture_now': '📸 拍攝快照',
    'portfolio.export_csv': '📥 匯出 CSV',
    'portfolio.capture_success': '✓ 已拍攝 {date} 快照 ({value})',
    'portfolio.capture_failed': '拍攝失敗：{error}',
    'portfolio.export_failed': '匯出失敗：{error}',

    // Portfolio v3.4.11 — daily snapshots log table on dashboard
    'portfolio.snapshots_log_title': '📋 快照日誌',
    'portfolio.snapshots_log_date': '日期',
    'portfolio.snapshots_log_captured': '拍攝時間',
    'portfolio.snapshots_log_value': '市值',
    'portfolio.snapshots_log_cost': '成本',
    'portfolio.snapshots_log_pnl': '損益',
    'portfolio.snapshots_log_pnl_pct': '損益%',
    'portfolio.snapshots_log_holdings': '持倉數',
    'portfolio.snapshots_log_empty': '尚無歷史快照 — 每日 20:00 自動拍攝',
    'portfolio.snapshots_log_count_total': '共 {n} 個快照',
    'portfolio.snapshots_log_backfilled': '補拍：此快照代表較早日期，於 {captured} 補入系統',

    // Index (v3.4.9) — stocks-tab toolbar with /api/tickers/export.csv button
    'index.stocks_toolbar': '持股清單',
    'index.export_holdings_csv': '📤 匯出持倉 CSV',
    'index.export_holdings_title': '匯出所有持倉到 CSV',
    'index.export_holdings_success': '已下載 CSV',
    'index.export_holdings_failed': '匯出失敗：{error}',

    // Index (v3.4.14) — stocks-tab filter row: sector pills + sort + holdings-only
    'index.stocks_sector_all': '全部行業',
    'index.stocks_sort_label': '排序',
    'index.sort_symbol': '代碼 A→Z',
    'index.sort_change_pct': '今日漲跌幅',
    'index.sort_price': '現價',
    'index.sort_market_cap': '市值',
    'index.sort_shares': '持倉股數',
    'index.stocks_holdings_only': '💼 只顯示持倉',
    'index.stocks_filter_count': '顯示 {shown} / {total}',
    'index.stocks_empty_filtered': '冇符合條件嘅股票',
    'index.week52_range': '52周範圍',
    'index.tracking_since': '追蹤自 {date}',

    // System page (/system)
    'nav.system': '系統',
    'nav.system_title': '系統狀態',
    'system.title': '系統狀態',
    'system.refresh': '重新整理',
    'system.desc': '即時顯示 Stocker 應用嘅健康狀態、業務指標同 Prometheus 計數器。數據來自 /api/metrics/summary + /health。',
    'system.health_title': '健康狀態',
    'system.uptime': '運行時間',
    'system.disk': '磁碟空間',
    'system.checked_at': '最後檢查',
    'system.health_ok': '健康',
    'system.health_degraded': '降級',
    'system.health_unhealthy': '異常',
    'system.health_unreachable': '無法取得',
    'system.tickers_title': '追蹤股票',
    'system.active_tickers': '啟用中股票',
    'system.total_reports': '報告總數',
    'system.events_active': '活躍事件',
    'system.events_upcoming': '未來 7 日事件',
    'system.reports_by_category': '報告分類',
    'system.cat_earnings': '業績',
    'system.cat_analyst': '分析師',
    'system.cat_industry': '行業',
    'system.cat_bank': '投行',
    'system.cat_sec': 'SEC 上市',
    'system.portfolio_title': '投資組合',
    'system.snapshots_count': '快照總數',
    'system.latest_value': '最新市值',
    'system.latest_pnl': '未實現損益',
    'system.latest_report': '最新報告',
    'system.features_title': '功能啟用',
    'system.alerts_enabled': '提醒（啟用）',
    'system.alerts_triggered': '提醒（已觸發）',
    'system.banks_enabled': '投行（啟用）',
    'system.custom_sources': '自訂數據源',
    'system.watchlist_groups': '追蹤分組',
    'system.sse_connections': 'SSE 連線',
    'system.top_sectors': '熱門行業',
    'system.top_tickers': '最多報告股票',
    'system.counters_title': 'Prometheus 計數器',
    'system.metrics_raw': '原始格式',
    'system.metrics_raw_title': '查看原始 Prometheus 格式',
    'system.cnt_exports': '持倉匯出',
    'system.cnt_captures': '快照拍攝',
    'system.cnt_portfolio_exports': '組合匯出',
    'system.cnt_breakdowns': '組合拆解',
    'system.cnt_searches': '報告搜索',
    'system.cnt_ticker_refresh': '股票刷新',
    'system.cnt_industry_news': '行業新聞請求',
    'system.empty_list': '暫無數據',
    'system.api_hint': '數據來自',
    'system.auto_refresh': '每 30 秒自動刷新',

    'system.actions_title': '管理操作',
    'system.actions_warning': '這些操作可能需要數分鐘，會佔用伺服器資源',
    'system.action_nightly_refresh': '刷新價格（5 年歷史）',
    'system.action_nightly_refresh_desc': '手動觸發 nightly_tasks，刷新所有追蹤股票的歷史價格',
    'system.action_check_banks': '檢查投行報告',
    'system.action_check_banks_desc': '掃描所有啟用投行的最新研究報告',
    'system.action_collect_reports': '收集行業報告',
    'system.action_collect_reports_desc': '從 SEC + 行業新聞源收集所有追蹤股票嘅報告',
    'system.action_running': '執行中...',
    'system.action_success': '操作完成',
    'system.action_failed': '操作失敗',
    'system.cnt_manual_triggers': '手動操作',
    'system.cnt_cache': '快取命中率',
    'system.cnt_data_sources': '數據源使用',
    'system.cnt_health_check': '健康檢查',


    // Time
    'time.just_now': '剛剛',
    'time.seconds_ago': '{n} 秒前',
    'time.minutes_ago': '{n} 分鐘前',
    'time.hours_ago': '{n} 小時前',
    'time.days_ago': '{n} 天前',
    'time.month_format': '{year} 年 {month} 月',

    // Language
    'lang.switch': '語言',
    'lang.zh': '中文',
    'lang.en': 'EN',
  },

  en: {
    // Nav
    'nav.dashboard': 'Dashboard',
    'nav.industry': 'Industry',
    'nav.files': 'Files',
    'nav.login': 'Login',
    'nav.banks': 'Banks',
    'nav.sources': 'Sources',
    'nav.watchlists': 'Groups',
    'nav.calendar': 'Calendar',
    'nav.search_placeholder': 'Search ticker...',

    // Common
    'common.app_name': 'Stocker',
    'common.loading': 'Loading...',
    'common.error': 'Failed to load. Please try again.',
    'common.retry': 'Retry',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.confirm': 'Confirm',
    'common.close': 'Close',
    'common.back': 'Back',
    'common.all': 'All',
    'common.none': 'None',
    'common.date': 'Date',
    'common.action': 'Action',
    'common.name': 'Name',
    'common.category': 'Category',
    'common.size': 'Size',
    'common.source': 'Source',
    'source.yfinance': 'Yahoo Finance',
    'source.yahoo_direct': 'Yahoo Direct',
    'source.stooq': 'Stooq',
    'source.coingecko': 'CoinGecko',
    'source.custom': 'Custom',
    'source.unknown': 'Unknown',
    'common.untitled': 'Untitled',
    'common.enabled': 'Active',
    'common.disabled': 'Disabled',
    'common.edit': 'Edit',
    'common.delete': 'Delete',
    'common.add': 'Add',
    'common.save': 'Save',
    'common.saving': 'Saving...',
    'common.saved': 'Saved',
    'common.deleted': 'Deleted',
    'common.updated': 'Updated',
    'common.required_field': 'Required',
    'common.delete_confirm': 'Are you sure?',
    'common.load_error': 'Failed to load',

    // Index page
    'index.title': 'Dashboard',
    'index.last_updated_at': 'Last updated: ',
    'index.last_updated_unknown': 'Not yet updated',
    'index.tab.stocks': 'Stocks',
    'index.tab.reports': 'Reports',
    'index.tab.archived': 'Archived',
    'index.tab.groups': 'Groups',
    'index.add': '+ Add',
    'index.add_ticker': 'Add Ticker',
    'index.symbol_placeholder': 'Enter symbol (e.g. TSLA)',
    'index.confirm_add': 'Add',
    'index.event_dismiss': 'Dismiss',
    'index.empty_stocks': 'No stocks tracked yet. Click "+ Add" to start.',
    'index.enter_symbol': 'Please enter a stock symbol',
    'index.adding': 'Adding...',
    'index.added': 'Added',
    'index.add_title': 'Add Ticker',
    'index.watchlist': 'Watchlists',
    'index.groups_empty': 'No watchlist groups yet',
    'index.groups_create': 'Create group',
    'index.groups_empty_group': 'Empty',
    'index.groups_manage': 'Manage groups',

    // v3.4.33 — Pattern 5d: hardcoded CJK in JS toast/badge strings
    'index.refresh_reason_us_market_open': 'Market open',
    'index.refresh_reason_us_extended_hours': 'Extended hours',
    'index.refresh_reason_us_off_hours': 'Off hours',
    'index.refresh_reason_weekend': 'Weekend',
    'index.preview_loading': 'Loading…',

    // Stock table
    'stock.ticker': 'Ticker',
    'stock.name': 'Name',
    'stock.price': 'Price',
    'stock.change': 'Change%',
    'stock.prev_close': 'Prev Close',
    'stock.mini_chart': 'Chart',
    'stock.shares': 'Shares',
    'stock.pnl': 'P&L',
    'stock.pnl_pct': 'P&L%',
    'stock.archive': 'Archive',
    'stock.restore': 'Restore',
    'stock.archived_date': 'Archived',
    'stock.sector': 'Sector',
    'stock.symbol': 'Symbol',
    'stock.action': 'Action',
    'stock.archived': 'Archived',
    'stock.restored': 'Restored',
    'stock.compare': 'Compare',
    'stock.select_compare': 'Select compare stock',
    'stock.clear_compare': 'Clear comparison',
    'stock.chart_line': 'Line',
    'stock.chart_candlestick': 'Candlestick',
    'stock.candle_open': 'Open',
    'stock.candle_high': 'High',
    'stock.candle_low': 'Low',
    'stock.candle_close': 'Close',

    // Archive
    'archive.confirm': 'Archive {symbol}? Downloaded reports will be kept.',
    'archive.empty': 'No archived stocks',

    // Reports list
    'reports.empty': 'No reports',
    'reports.tab.all': 'All',
    'reports.tab.earnings': 'Earnings',
    'reports.tab.news': 'News',
    'reports.tab.analyst': 'Broker Research',
    'reports.tab.bank': 'Bank Reports',
    'reports.search_placeholder': 'Search report titles or summaries...',  // v3.4.20
    'reports.source_filter': 'All sources',                              // v3.4.20
    'reports.source_all': 'All sources',                                 // v3.4.20
    'reports.filter_count': '{shown}/{total}',                           // v3.4.20
    'reports.empty_filtered': 'No reports match the current filters',    // v3.4.20

    // Stock detail
    'detail.back': 'Back',
    'detail.chart_loading': 'Loading chart...',
    'detail.indicators': 'Indicators',
    'detail.info': 'Fundamentals',
    'detail.market_cap': 'Market Cap',
    'detail.pe_ratio': 'P/E Ratio',
    'detail.eps': 'EPS',
    'detail.high_52w': '52W High',
    'detail.low_52w': '52W Low',
    'detail.next_earnings': 'Next Earnings',
    'detail.news': 'Recent News',
    'detail.no_news': 'No news available',
    'detail.holdings': 'Holdings',
    'detail.shares_label': 'Shares',
    'detail.cost_label': 'Cost Basis',
    'detail.save_holdings': 'Save',
    'detail.event_dismiss': 'Dismiss',
    'detail.no_data': 'No data available',
    'detail.load_stock_error': 'Failed to load stock data',
    'detail.load_chart_error': 'Failed to load chart',
    'detail.holdings_updated': 'Holdings updated',
    'detail.holdings_update_error': 'Save failed',
    'detail.refreshing': 'Updating...',
    'detail.refresh_error': 'Update failed',
    'detail.refreshed': 'Updated',
    'detail.event_dismissed': 'Dismissed',
    'detail.event_dismiss_error': 'Action failed',

    // News filter row (v3.4.25)
    'detail.news_sort_label': 'Sort',
    'detail.news_sort_newest': 'Newest first',
    'detail.news_sort_oldest': 'Oldest first',
    'detail.news_publisher_all': 'All sources',
    'detail.news_count': '{shown}/{total}',
    'detail.news_no_match': 'No news match the filter',
    'detail.news_try_other': 'Try "All sources" or pick another publisher',
    'detail.news_untitled': 'Untitled',

    // Events list (v3.4.27)
    'detail.events_title': 'Events Timeline',
    'detail.events_empty': 'No events yet',
    'detail.events_count': '{n} events',
    'detail.events_upcoming_tag': 'upcoming',
    'detail.events_dismissed_tag': 'dismissed',
    'detail.reports_title': 'Related Reports',
    'detail.reports_count': '{n}',
    'detail.reports_empty_title': 'No reports yet',
    'detail.reports_empty_hint': '10-K, 10-Q, and analyst reports will appear here once collected',

    // Reports
    'report.title': 'Reports',
    'report.summary': 'Summary',
    'report.added_at': 'Added to system: {date}',
    'report.analysis': 'AI Analysis',
    'report.original': 'Original',
    'report.no_analysis': 'AI analysis not yet generated',
    'report.collect': 'Collect Reports',
    'report.collecting': 'Collecting...',
    'report.collect_done': 'Collection complete',
    'report.view_source': 'View Source',
    'report.source_external': 'Original saved at external link',
    'report.no_source': 'No source content',
    'report.load_error': 'Failed to load report',
    'report.rating_summary': 'Rating Summary',
    'report.analysts': 'analysts',
    'report.rating.strongBuy': 'Strong Buy',
    'report.rating.buy': 'Buy',
    'report.rating.hold': 'Hold',
    'report.rating.sell': 'Sell',
    'report.rating.strongSell': 'Strong Sell',
    'report.rating.period': 'Period',
    'report.rating.current': 'Current',
    'report.rating.1m': '1 month ago',
    'report.rating.2m': '2 months ago',
    'report.rating.3m': '3 months ago',
    'report.rating.4m': '4 months ago',
    'report.rating.5m': '5 months ago',
    'report.ticker_badge': 'View {symbol} details',               // v3.4.57 — Pattern 9b orphan field (ticker_symbol)

    // Industry
    'industry.title': 'Industry News & Reports',
    'industry.collect': 'Collect Industry News',
    'industry.collecting': 'Collecting...',
    // v3.4.33 — Pattern 5d: hardcoded CJK in collectNews() toast strings
    'industry.collect_done': 'Collection complete!',
    'industry.collect_failed': 'Collection failed',
    'industry.network_error': 'Network error',
    'industry.select': 'Select a sector to view reports',
    'industry.reports': 'Reports',
    'industry.tickers': 'Tickers',
    'industry.no_sectors': 'No sectors found. Add some tickers first.',
    'industry.no_reports': 'No reports found for this sector yet.',
    'industry.load_error': 'Failed to load sectors.',
    'industry.report_error': 'Failed to load reports.',
    'industry.close': 'Close',
    'industry.nav': 'Industry',
    // Industry News panel (v3.4.16)
    'industry.news': 'Industry News',
    'industry.no_news': 'No news found for this sector.',
    'industry.news_error': 'Failed to load industry news.',
    'industry.news_count': '{n}',

    // Sector reports filter row (v3.4.22)
    'industry.filter_all': 'All',
    'industry.filter_earnings': 'Earnings',
    'industry.filter_analyst': 'Analyst',
    'industry.filter_sec': 'SEC',
    'industry.filter_industry': 'News',
    'industry.sort_newest': 'Newest first',
    'industry.sort_oldest': 'Oldest first',
    'industry.count_filtered': 'Showing {shown} / {total}',
    'industry.count_total': '{total} total',
    'industry.no_filter_match': 'No reports match the filter',
    'industry.try_other_filter': 'Try a different category',

    // Files
    'files.title': 'File Manager',
    'files.filename': 'Filename',
    'files.download': 'Download',
    'files.view_report': 'View Report',
    'files.load_error': 'Failed to load file list.',
    'files.empty': 'No files',

    // File categories
    'files.cat.all': 'All',
    'files.cat.earnings': 'Earnings',
    'files.cat.analyst_report': 'Analyst Report',
    'files.cat.news': 'News',
    'files.cat.sec_filing': 'SEC Filing',
    'files.cat.industry': 'Industry Report',
    'files.cat.investment_bank_report': 'Investment Bank Report',

    // Files page filter row (v3.4.23)
    'files.search_placeholder': 'Search filename...',
    'files.sort_newest': 'Newest first',
    'files.sort_oldest': 'Oldest first',
    'files.sort_name': 'Filename',
    'files.sort_size_desc': 'Largest size',
    'files.count_filtered': 'Showing {shown} / {total}',
    'files.count_total': '{total} total',
    'files.no_filter_match': 'No files match the filter',
    'files.try_other_filter': 'Try a different file',

    // Events Calendar
    'events.title': 'Events Calendar',
    'events.sync': 'Sync',
    'events.syncing': 'Syncing...',
    'events.sync_done': 'Synced {n} events',
    'events.sync_error': 'Sync failed',
    'events.upcoming': 'Upcoming',
    'events.empty': 'No upcoming events',
    'events.empty_hint': 'Click "Sync" to fetch from Yahoo Finance',
    'events.type.all': 'All',
    'events.type.earnings': 'Earnings',
    'events.type.dividend': 'Dividend',
    'events.type.sec_filing': 'SEC',
    'events.filter_count': '{shown}/{total}',
    'events.filtered_empty': 'No events of this type',
    'events.hide_dismissed': 'Hide dismissed',
    'events.show_dismissed': 'Show dismissed',
    'events.dismissed_tag': 'dismissed',
    'events.dismiss_tooltip': 'Mark as acknowledged',
    'events.dismissed': 'Marked as acknowledged',
    'events.dismiss_error': 'Dismiss failed',
    'events.only_dismissed': 'All events dismissed',
    'events.only_dismissed_hint': 'Click "Show dismissed" to view',
    'events.days': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    'events.year_month': '{month} {year}',

    // Custom Sources
    'sources.title': 'Custom Data Sources',
    'sources.desc': 'Connect historical prices for any fund / bond / product (JSONPath + URL).',
    'sources.desc2': 'Custom sources take priority over Yahoo in the price resolution chain.',
    'sources.add_title': 'Add Custom Source',
    'sources.edit_title': 'Edit Custom Source',
    'sources.name': 'Name',
    'sources.name_placeholder': 'e.g. My Pension Fund',
    'sources.symbol_replaced': '{symbol} will be replaced',
    'sources.optional_fields': 'Optional fields (Open / High / Low / Volume / Filter)',
    'sources.filter_label': 'Symbol filter path (match by symbol)',
    'sources.notes': 'Notes',
    'sources.notes_placeholder': 'e.g. Updates daily at 23:00',
    'sources.empty_title': 'No custom sources configured',
    'sources.enabled': '● Active',
    'sources.disabled': '○ Disabled',
    'sources.required_error': 'name, url, date_path, price_path are all required',
    'sources.save_error': 'Save failed',
    'sources.delete_confirm': 'Delete this custom source?',
    'sources.delete_error': 'Delete failed',

    // Banks
    'banks.title': 'Bank Watchlist',
    'banks.check_all': 'Check All',
    'banks.tab.list': 'Bank List',
    'banks.tab.reports': 'Latest Reports',
    'banks.add_title': 'Add Bank',
    'banks.edit_title': 'Edit Bank',
    'banks.name': 'Bank Name',
    'banks.name_placeholder': 'e.g. Goldman Sachs',
    'banks.short_name': 'Short Name',
    'banks.short_name_placeholder': 'e.g. GS',
    'banks.website': 'Website URL',
    'banks.report_url': 'Report Page URL',
    'banks.report_url_hint': 'Enter the bank\'s research or Insights page URL',
    'banks.empty_title': 'No banks added yet',
    'banks.empty_hint': 'Click "Add" to start tracking bank reports',
    'banks.last_check': 'Last check: ',
    'banks.never_checked': 'Not yet checked',
    'banks.action.check': 'Check new reports',
    'banks.action.edit': 'Edit',
    'banks.reports_empty_title': 'No reports',
    'banks.reports_empty_hint': 'Add a bank then click "Check" to fetch reports',
    'banks.action.view': 'View',
    'banks.action.download': 'Download',
    'banks.downloaded': 'Downloaded',
    'banks.name_required': 'Please enter bank name',
    'banks.url_required': 'Please enter report page URL',
    'banks.save_error': 'Save failed',
    'banks.action_error': 'Action failed',
    'banks.checking': 'Checking...',
    'banks.check_done': 'Done: {n} new reports',
    'banks.checking_all': 'Checking all banks...',
    'banks.check_all_done': 'Done: {n} new reports total',
    'banks.downloading': 'Downloading...',
    'banks.download_done': 'Download complete',
    'banks.filter_all': 'All',
    'banks.filter_enabled': 'Enabled only',
    'banks.filter_undownloaded': 'Undownloaded only',
    'banks.count_filtered': '{shown}/{total} shown',
    'banks.empty_filtered_title': 'No results match filter',
    'banks.empty_filtered_hint': 'Switch to "All" to see the complete list',

    // Watchlists
    'watchlists.title': 'Watchlist Groups',
    'watchlists.add_group': 'Add Group',
    'watchlists.desc': 'Organize tracked stocks into groups (e.g. Tech, Finance, My Portfolio).',
    'watchlists.add_title': 'Add Group',
    'watchlists.edit_title': 'Edit Group',
    'watchlists.group_name': 'Group Name',
    'watchlists.group_name_placeholder': 'e.g. Tech Stocks',
    'watchlists.description': 'Description',
    'watchlists.description_placeholder': '(optional)',
    'watchlists.color': 'Color',
    'watchlists.add_ticker': 'Add Stock',
    'watchlists.ticker_symbol': 'Symbol',
    'watchlists.empty_title': 'No watchlist groups yet',
    'watchlists.empty_hint': 'Click "Add Group" to start',
    'watchlists.ticker_count': '{n} stocks',
    'watchlists.name_required': 'Please enter group name',
    'watchlists.delete_confirm': 'Delete "{name}"? Stocks will not be removed.',
    'watchlists.all_added': 'All stocks already added',
    'watchlists.symbol_required': 'Please enter a stock symbol',
    'watchlists.save_error': 'Save failed: {msg}',
    'watchlists.network_error': 'Network error',
    'watchlists.remove_error': 'Remove failed: {msg}',

    // Price Alerts (v3.4)
    'alerts.title': 'Price Alerts',
    'alerts.add': 'New Alert',
    'alerts.edit': 'Edit Alert',
    'alerts.desc': 'Set price thresholds — events fire automatically when prices cross them. Each alert fires once; rearm to re-arm.',
    'alerts.threshold_high': 'Rises to ≥',
    'alerts.threshold_low': 'Falls to ≤',
    'alerts.threshold_high_full': 'Rises to ≥ target',
    'alerts.threshold_low_full': 'Falls to ≤ target',
    'alerts.target_price': 'Target Price (USD)',
    'alerts.rearm': 'Rearm',
    'alerts.enabled': 'Enabled',
    'alerts.disabled': 'Disabled',
    'alerts.triggered_at': 'Triggered: {time}',
    'alerts.created_at': 'Created at: {time}',
    'alerts.note': 'Notes',
    'alerts.note_placeholder': '(optional) e.g. breakout level',
    'alerts.symbol_placeholder': 'TSLA',
    'alerts.target_placeholder': 'e.g. 300.00',
    // Page actions
    'alerts.check_all': 'Check Now',
    'alerts.check_all_title': 'Check all enabled alerts now',
    // Filter chips
    'alerts.filter_all': 'All',
    'alerts.filter_enabled': 'Enabled',
    'alerts.filter_disabled': 'Disabled',
    // Modal form labels
    'alerts.field_symbol': 'Symbol *',
    'alerts.field_type': 'Trigger Type *',
    'alerts.field_target': 'Target Price (USD) *',
    'alerts.required_field': 'required',
    // Status / empty / errors
    'alerts.empty': 'No alerts yet. Click "New Alert" to set one up.',
    'alerts.empty_short': 'No alerts',
    'alerts.load_error': 'Load failed: {msg}',
    'alerts.save_error': 'Save failed: {msg}',
    'alerts.rearm_error': 'Rearm failed: {msg}',
    'alerts.delete_error': 'Delete failed: {msg}',
    'alerts.update_error': 'Update failed: {msg}',
    'alerts.symbol_required': 'Please enter a symbol',
    'alerts.price_required': 'Please enter a valid target price',
    'alerts.check_error': 'Check failed: {msg}',
    'alerts.check_triggered': '{n} alert(s) triggered!',
    'alerts.check_none': 'No alerts triggered.',
    'alerts.check_line': '{symbol} {type} ${threshold} (now ${current})',
    // Confirm dialog
    'alerts.delete_confirm_title': 'Confirm',
    'alerts.delete_confirm_msg': 'Delete the alert for {symbol}? This cannot be undone.',
    // Card actions (titles)
    'alerts.action_disable': 'Disable',
    'alerts.action_enable': 'Enable',
    'alerts.action_rearm_title': 'Rearm',
    'alerts.action_edit_title': 'Edit',
    'alerts.action_delete_title': 'Delete',
    'alerts.note_prefix': 'Notes:',

    // Portfolio summary (v3.4.2)
    'portfolio.total_value': 'Total Value',
    'portfolio.total_cost': 'Total Cost',
    'portfolio.total_pnl': 'Total P&L',
    'portfolio.pnl_pct': 'P&L %',
    'portfolio.holdings_count': 'Holdings',
    'portfolio.change_30d': '30-Day Change',
    'portfolio.history_title': 'Portfolio 30-Day History',
    'portfolio.history_empty': 'No history yet — captured nightly at 20:00',
    'portfolio.snapshot_today': 'Today snapshot: {date}',
    'portfolio.unrealized': 'Unrealized P&L',
    'portfolio.dashboard_no_history': 'No portfolio history yet',
    'portfolio.dashboard_value_only': 'Current total value',
    'portfolio.dashboard_change': 'vs 30 days ago',
    'portfolio.sparkline_meta': '{n}d · {sign}{delta} ({sign}{pct}%)',
    'portfolio.sparkline_title': 'Value trend (last 30 days)',
    'portfolio.holdings_title': 'Holdings Breakdown',
    'portfolio.holdings_symbol': 'Symbol',
    'portfolio.holdings_shares': 'Shares',
    'portfolio.holdings_cost_basis': 'Cost/Share',
    'portfolio.holdings_cost_value': 'Cost Total',
    'portfolio.holdings_price': 'Price',
    'portfolio.holdings_market_value': 'Market Value',
    'portfolio.holdings_unrealized_pl': 'Unrealized P&L',
    'portfolio.holdings_share': 'Share',
    'portfolio.holdings_as_of': 'As of: {time}',               // v3.4.58 — Pattern 9b orphan field (breakdown timestamp)
    'portfolio.holdings_empty': 'No holdings yet',
    'portfolio.holdings_count_total': '{n} holdings · total {total}',
    'portfolio.actions_title': 'Quick actions',
    'portfolio.capture_now': '📸 Capture snapshot',
    'portfolio.export_csv': '📥 Export CSV',
    'portfolio.capture_success': '✓ Captured {date} snapshot ({value})',
    'portfolio.capture_failed': 'Capture failed: {error}',
    'portfolio.export_failed': 'Export failed: {error}',

    // Portfolio v3.4.11 — daily snapshots log table on dashboard
    'portfolio.snapshots_log_title': '📋 Snapshot Log',
    'portfolio.snapshots_log_date': 'Date',
    'portfolio.snapshots_log_captured': 'Captured',
    'portfolio.snapshots_log_value': 'Value',
    'portfolio.snapshots_log_cost': 'Cost',
    'portfolio.snapshots_log_pnl': 'P&L',
    'portfolio.snapshots_log_pnl_pct': 'P&L %',
    'portfolio.snapshots_log_holdings': 'Holdings',
    'portfolio.snapshots_log_empty': 'No snapshots yet — captured nightly at 20:00',
    'portfolio.snapshots_log_count_total': '{n} snapshots total',
    'portfolio.snapshots_log_backfilled': 'Backfilled: this row was actually captured on {captured}, representing an earlier date',

    // Index (v3.4.9) — stocks-tab toolbar with /api/tickers/export.csv button
    'index.stocks_toolbar': 'Holdings',
    'index.export_holdings_csv': '📤 Export holdings CSV',
    'index.export_holdings_title': 'Export all holdings to CSV',
    'index.export_holdings_success': 'CSV downloaded',
    'index.export_holdings_failed': 'Export failed: {error}',

    // Index (v3.4.14) — stocks-tab filter row: sector pills + sort + holdings-only
    'index.stocks_sector_all': 'All sectors',
    'index.stocks_sort_label': 'Sort',
    'index.sort_symbol': 'Symbol A→Z',
    'index.sort_change_pct': "Today's % change",
    'index.sort_price': 'Current price',
    'index.sort_market_cap': 'Market cap',
    'index.sort_shares': 'Shares held',
    'index.stocks_holdings_only': '💼 Holdings only',
    'index.stocks_filter_count': 'Showing {shown} / {total}',
    'index.stocks_empty_filtered': 'No stocks match the current filters',
    'index.week52_range': '52W Range',
    'index.tracking_since': 'Tracking since {date}',

    // System page (/system)
    'nav.system': 'System',
    'nav.system_title': 'System status',
    'system.title': 'System status',
    'system.refresh': 'Refresh',
    'system.desc': 'Live health, business metrics, and Prometheus counters for the Stocker app. Backed by /api/metrics/summary + /health.',
    'system.health_title': 'Health',
    'system.uptime': 'Uptime',
    'system.disk': 'Disk space',
    'system.checked_at': 'Last checked',
    'system.health_ok': 'Healthy',
    'system.health_degraded': 'Degraded',
    'system.health_unhealthy': 'Unhealthy',
    'system.health_unreachable': 'Unreachable',
    'system.tickers_title': 'Tracked tickers',
    'system.active_tickers': 'Active tickers',
    'system.total_reports': 'Total reports',
    'system.events_active': 'Active events',
    'system.events_upcoming': 'Events next 7d',
    'system.reports_by_category': 'Reports by category',
    'system.cat_earnings': 'Earnings',
    'system.cat_analyst': 'Analyst',
    'system.cat_industry': 'Industry',
    'system.cat_bank': 'Bank',
    'system.cat_sec': 'SEC listing',
    'system.portfolio_title': 'Portfolio',
    'system.snapshots_count': 'Snapshots',
    'system.latest_value': 'Latest value',
    'system.latest_pnl': 'Unrealized P&L',
    'system.latest_report': 'Latest report',
    'system.features_title': 'Feature usage',
    'system.alerts_enabled': 'Alerts (enabled)',
    'system.alerts_triggered': 'Alerts (triggered)',
    'system.banks_enabled': 'Banks (enabled)',
    'system.custom_sources': 'Custom sources',
    'system.watchlist_groups': 'Watchlist groups',
    'system.sse_connections': 'SSE connections',
    'system.top_sectors': 'Top sectors',
    'system.top_tickers': 'Most-reported tickers',
    'system.counters_title': 'Prometheus counters',
    'system.metrics_raw': 'Raw format',
    'system.metrics_raw_title': 'View raw Prometheus format',
    'system.cnt_exports': 'Holdings exports',
    'system.cnt_captures': 'Snapshot captures',
    'system.cnt_portfolio_exports': 'Portfolio exports',
    'system.cnt_breakdowns': 'Portfolio breakdowns',
    'system.cnt_searches': 'Report searches',
    'system.cnt_ticker_refresh': 'Ticker refresh',
    'system.cnt_industry_news': 'Industry news requests',
    'system.empty_list': 'No data yet',
    'system.api_hint': 'Data from',
    'system.auto_refresh': 'Auto-refresh every 30s',

    'system.actions_title': 'Admin actions',
    'system.actions_warning': 'These actions may take several minutes and consume server resources',
    'system.action_nightly_refresh': 'Refresh prices (5y history)',
    'system.action_nightly_refresh_desc': 'Manually trigger nightly_tasks to refresh all tracked tickers\' historical prices',
    'system.action_check_banks': 'Check investment banks',
    'system.action_check_banks_desc': 'Scrape all enabled banks for new research reports',
    'system.action_collect_reports': 'Collect industry reports',
    'system.action_collect_reports_desc': 'Pull reports from SEC + industry news sources for all tracked tickers',
    'system.action_running': 'Running...',
    'system.action_success': 'Action completed',
    'system.action_failed': 'Action failed',
    'system.cnt_manual_triggers': 'Manual triggers',
    'system.cnt_cache': 'Cache hit rate',
    'system.cnt_data_sources': 'Data source usage',
    'system.cnt_health_check': 'Health checks',


    // Time
    'time.just_now': 'Just now',
    'time.seconds_ago': '{n}s ago',
    'time.minutes_ago': '{n}m ago',
    'time.hours_ago': '{n}h ago',
    'time.days_ago': '{n}d ago',

    // Language
    'lang.switch': 'Language',
    'lang.zh': '中文',
    'lang.en': 'EN',
  }
};

// Current language
let _lang = localStorage.getItem('stocker_lang') || 'zh';

/**
 * Get translation for a key. Supports {placeholder} interpolation.
 */
function t(key, params) {
  const dict = I18N[_lang] || I18N.zh;
  let text = dict[key] || I18N.zh[key] || key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, v);
    }
  }
  return text;
}

/**
 * Get current language code.
 */
function getLang() {
  return _lang;
}

/**
 * Locale-aware date formatting (v3.4.34 Pattern 5e).
 * Returns a date string formatted for the current language —
 * 'zh-TW' for Chinese mode (default), 'en-US' for English mode.
 * Accepts ISO strings, Date objects, or null/undefined (returns '—').
 */
function formatDate(date, opts) {
  if (!date) return '—';
  const d = (date instanceof Date) ? date : new Date(date);
  if (isNaN(d.getTime())) return '—';
  const locale = _lang === 'en' ? 'en-US' : 'zh-TW';
  return d.toLocaleDateString(locale, opts);
}

/**
 * Locale-aware datetime formatting (v3.4.34).
 * Same as formatDate but includes time.
 */
function formatDateTime(date, opts) {
  if (!date) return '—';
  const d = (date instanceof Date) ? date : new Date(date);
  if (isNaN(d.getTime())) return '—';
  const locale = _lang === 'en' ? 'en-US' : 'zh-TW';
  return d.toLocaleString(locale, opts);
}

/**
 * Locale-aware number formatting (v3.4.45 Pattern 5e number variant).
 * Returns a number string formatted for the current language —
 * 'en-US' for English mode, 'zh-TW' for Chinese mode.
 * Accepts numbers, numeric strings, or null/undefined (returns '—').
 */
function formatNumber(n, opts) {
  if (n == null || isNaN(Number(n))) return '—';
  const locale = _lang === 'en' ? 'en-US' : 'zh-TW';
  return Number(n).toLocaleString(locale, opts);
}

/**
 * Locale-aware currency formatting (v3.4.45).
 * Same as formatNumber but prefixes with the dollar sign.
 * Defaults to 2 decimal places — overrides via opts.
 */
function formatCurrency(n, opts) {
  const fmtOpts = Object.assign({ minimumFractionDigits: 2, maximumFractionDigits: 2 }, opts || {});
  return '$' + formatNumber(n, fmtOpts);
}

/**
 * Switch language and refresh all data-i18n elements.
 */
function setLang(lang) {
  _lang = lang;
  localStorage.setItem('stocker_lang', lang);
  applyTranslations();
  // Update lang switcher buttons
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  // Fire custom event for pages to re-render dynamic content
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
}

/**
 * Apply translations to all elements with data-i18n attribute.
 */
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const text = t(key);
    if (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'submit') {
      el.placeholder = text;
    } else {
      el.textContent = text;
    }
  });
  // Translate aria-label and title attributes
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
  });
  // Translate placeholder attribute on inputs
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
  });
  // Update page title — read data-page-title from <title> element, fall back to zh textContent
  const titleEl = document.querySelector('title[data-page-title]');
  if (titleEl) {
    const titleKey = titleEl.getAttribute('data-page-title');
    const translated = t(titleKey);
    // translated is the key string itself if missing — fall back to existing textContent
    document.title = (translated && translated !== titleKey)
      ? translated + ' — Stocker'
      : titleEl.textContent;
  }
}

/**
 * Create language switcher HTML (call once in base.html).
 */
function createLangSwitcher() {
  return `
    <div class="lang-switcher">
      <button class="lang-btn ${_lang === 'zh' ? 'active' : ''}" data-lang="zh" onclick="setLang('zh')">中</button>
      <button class="lang-btn ${_lang === 'en' ? 'active' : ''}" data-lang="en" onclick="setLang('en')">EN</button>
    </div>
  `;
}

// Auto-apply on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
