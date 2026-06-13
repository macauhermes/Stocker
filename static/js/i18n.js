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

    // Common
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

    // Index page
    'index.title': '主頁',
    'index.tab.stocks': '股票',
    'index.tab.reports': '報告',
    'index.tab.archived': '歸檔',
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

    // Archive
    'archive.confirm': '確定要歸檔 {symbol} 嗎？已下載的報告將保留。',
    'archive.empty': '暫無歸檔的股票',

    // Reports list
    'reports.empty': '尚無報告',

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
    'detail.news': '最近新聞',
    'detail.no_news': '暫無新聞',
    'detail.holdings': '持倉管理',
    'detail.shares_label': '持倉數量',
    'detail.cost_label': '成本價',
    'detail.save_holdings': '保存',
    'detail.event_dismiss': '已知悉',
    'detail.no_data': '暫無數據',

    // Reports
    'report.title': '報告',
    'report.summary': '摘要',
    'report.analysis': 'AI 分析',
    'report.original': '原文',
    'report.no_analysis': 'AI 分析尚未生成',
    'report.collect': '收集報告',
    'report.collecting': '收集中...',
    'report.collect_done': '收集完成',

    // Industry
    'industry.title': '行業新聞與報告',
    'industry.collect': '收集行業新聞',
    'industry.collecting': '收集中...',
    'industry.select': '選擇行業查看報告',
    'industry.reports': '報告',
    'industry.tickers': '追蹤標的',
    'industry.no_sectors': '暫無行業分類，請先新增追蹤股票',
    'industry.no_reports': '該行業暫無報告',
    'industry.load_error': '載入行業失敗',
    'industry.report_error': '載入報告失敗',
    'industry.close': '關閉',

    // Files
    'files.title': '檔案管理',
    'files.filename': '檔案名稱',
    'files.download': '下載',
    'files.load_error': '載入檔案列表失敗',
    'files.empty': '暫無檔案',

    // File categories
    'files.cat.all': '全部',
    'files.cat.earnings': '財報',
    'files.cat.analyst_report': '分析師報告',
    'files.cat.news': '新聞',
    'files.cat.sec_filing': 'SEC 文件',
    'files.cat.industry': '行業報告',

    // Time
    'time.just_now': '剛剛',
    'time.minutes_ago': '{n} 分鐘前',
    'time.hours_ago': '{n} 小時前',
    'time.days_ago': '{n} 天前',

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

    // Common
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

    // Index page
    'index.title': 'Dashboard',
    'index.tab.stocks': 'Stocks',
    'index.tab.reports': 'Reports',
    'index.tab.archived': 'Archived',
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

    // Archive
    'archive.confirm': 'Archive {symbol}? Downloaded reports will be kept.',
    'archive.empty': 'No archived stocks',

    // Reports list
    'reports.empty': 'No reports',

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
    'detail.news': 'Recent News',
    'detail.no_news': 'No news available',
    'detail.holdings': 'Holdings',
    'detail.shares_label': 'Shares',
    'detail.cost_label': 'Cost Basis',
    'detail.save_holdings': 'Save',
    'detail.event_dismiss': 'Dismiss',
    'detail.no_data': 'No data available',

    // Reports
    'report.title': 'Reports',
    'report.summary': 'Summary',
    'report.analysis': 'AI Analysis',
    'report.original': 'Original',
    'report.no_analysis': 'AI analysis not yet generated',
    'report.collect': 'Collect Reports',
    'report.collecting': 'Collecting...',
    'report.collect_done': 'Collection complete',

    // Industry
    'industry.title': 'Industry News & Reports',
    'industry.collect': 'Collect Industry News',
    'industry.collecting': 'Collecting...',
    'industry.select': 'Select a sector to view reports',
    'industry.reports': 'Reports',
    'industry.tickers': 'Tickers',
    'industry.no_sectors': 'No sectors found. Add some tickers first.',
    'industry.no_reports': 'No reports found for this sector yet.',
    'industry.load_error': 'Failed to load sectors.',
    'industry.report_error': 'Failed to load reports.',
    'industry.close': 'Close',

    // Files
    'files.title': 'File Manager',
    'files.filename': 'Filename',
    'files.download': 'Download',
    'files.load_error': 'Failed to load file list.',
    'files.empty': 'No files',

    // File categories
    'files.cat.all': 'All',
    'files.cat.earnings': 'Earnings',
    'files.cat.analyst_report': 'Analyst Report',
    'files.cat.news': 'News',
    'files.cat.sec_filing': 'SEC Filing',
    'files.cat.industry': 'Industry Report',

    // Time
    'time.just_now': 'Just now',
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
  // Update page title
  const titleEl = document.querySelector('[data-i18n-title]');
  if (titleEl) {
    document.title = t(titleEl.getAttribute('data-i18n-title'));
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
