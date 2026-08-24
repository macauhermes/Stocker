/**
 * TextRenderer - 結構化文字渲染器
 * 將 TXT/JSON 內容渲染為手機友好的列表格式
 */
class TextRenderer {
    constructor(options = {}) {
        this.options = {
            maxItems: 50,
            showIndex: true,
            compact: false,
            ...options
        };
    }

    /**
     * 主渲染方法 - 自動偵測格式並渲染
     */
    render(content) {
        if (!content) return this.renderEmpty();

        // 嘗試解析為 JSON
        try {
            const json = JSON.parse(content);
            return this.renderJSON(json);
        } catch (e) {
            // 不是 JSON，繼續
        }

        // 偵測表格格式
        if (this.isTableFormat(content)) {
            return this.renderTable(content);
        }

        // 偵測列表格式
        if (this.isListFormat(content)) {
            return this.renderList(content);
        }

        // 預設：純文字
        return this.renderPlainText(content);
    }

    /**
     * JSON 渲染
     */
    renderJSON(data) {
        if (Array.isArray(data)) {
            return this.renderArray(data);
        }
        if (typeof data === 'object') {
            return this.renderObject(data);
        }
        return this.renderValue(data);
    }

    /**
     * JSON 陣列 → 列表
     */
    renderArray(arr) {
        if (arr.length === 0) return this.renderEmpty('空列表');

        const items = arr.slice(0, this.options.maxItems);
        const html = items.map((item, i) => {
            if (typeof item === 'object' && item !== null) {
                return this.renderListItem(i, this.renderObjectContent(item));
            }
            return this.renderListItem(i, this.renderValue(item));
        }).join('');

        const more = arr.length > this.options.maxItems 
            ? `<div class="text-renderer-more">還有 ${arr.length - this.options.maxItems} 項...</div>` 
            : '';

        return `<div class="text-renderer-list">${html}${more}</div>`;
    }

    /**
     * JSON 物件 → 鍵值列表
     */
    renderObject(obj) {
        const entries = Object.entries(obj);
        if (entries.length === 0) return this.renderEmpty('空物件');

        const html = entries.map(([key, value]) => {
            return `
                <div class="text-renderer-item">
                    <div class="text-renderer-key">${this.escapeHtml(key)}</div>
                    <div class="text-renderer-value">${this.renderValue(value)}</div>
                </div>
            `;
        }).join('');

        return `<div class="text-renderer-list">${html}</div>`;
    }

    /**
     * 渲染物件內容（用於陣列中的物件）
     */
    renderObjectContent(obj) {
        const entries = Object.entries(obj);
        return entries.map(([key, value]) => {
            return `
                <div class="text-renderer-field">
                    <span class="text-renderer-label">${this.escapeHtml(key)}:</span>
                    <span class="text-renderer-data">${this.renderValue(value)}</span>
                </div>
            `;
        }).join('');
    }

    /**
     * 渲染值（帶類型判斷）
     */
    renderValue(value) {
        if (value === null || value === undefined) {
            return '<span class="text-renderer-null">—</span>';
        }
        if (typeof value === 'boolean') {
            return `<span class="text-renderer-bool">${value ? '✓' : '✗'}</span>`;
        }
        if (typeof value === 'number') {
            return `<span class="text-renderer-number">${this.formatNumber(value)}</span>`;
        }
        if (typeof value === 'string') {
            // 偵測 URL
            if (value.match(/^https?:\/\//)) {
                return `<a href="${this.escapeHtml(value)}" target="_blank" class="text-renderer-link">${this.escapeHtml(value)}</a>`;
            }
            // 偵測日期
            if (value.match(/^\d{4}-\d{2}-\d{2}/)) {
                return `<span class="text-renderer-date">${this.escapeHtml(value)}</span>`;
            }
            return `<span class="text-renderer-text">${this.escapeHtml(value)}</span>`;
        }
        if (Array.isArray(value)) {
            return value.map(v => this.renderValue(v)).join(', ');
        }
        return `<span class="text-renderer-text">${this.escapeHtml(JSON.stringify(value))}</span>`;
    }

    /**
     * 表格格式偵測
     */
    isTableFormat(content) {
        const lines = content.split('\n').filter(l => l.trim());
        if (lines.length < 2) return false;
        
        // 檢查是否有分隔符
        const hasPipe = content.includes(' | ');
        const hasTab = content.includes('\t');
        const hasHeader = lines[0].match(/[a-zA-Z]/) && lines[1].match(/^[\s\d-]+$/);
        
        return hasPipe || hasTab || hasHeader;
    }

    /**
     * 表格渲染
     */
    renderTable(content) {
        const lines = content.split('\n').filter(l => l.trim());
        let headers = [];
        let rows = [];

        for (const line of lines) {
            const trimmed = line.trim();
            
            // 跳過分隔線
            if (trimmed.match(/^[-|+]+$/)) continue;
            
            // 解析分隔值
            let parts;
            if (trimmed.includes(' | ')) {
                parts = trimmed.split(' | ').map(p => p.trim());
            } else if (trimmed.includes('\t')) {
                parts = trimmed.split('\t').map(p => p.trim());
            } else {
                parts = trimmed.split(/\s{2,}/).map(p => p.trim());
            }

            if (parts.length > 1) {
                if (headers.length === 0) {
                    headers = parts;
                } else {
                    rows.push(parts);
                }
            }
        }

        if (headers.length === 0 || rows.length === 0) {
            return this.renderPlainText(content);
        }

        // 渲染為卡片列表（手機友好）
        const html = rows.slice(0, this.options.maxItems).map((row, i) => {
            const fields = headers.map((h, j) => {
                const value = j < row.length ? row[j] : '—';
                return `
                    <div class="text-renderer-field">
                        <span class="text-renderer-label">${this.escapeHtml(h)}</span>
                        <span class="text-renderer-data">${this.escapeHtml(value)}</span>
                    </div>
                `;
            }).join('');

            return `
                <div class="text-renderer-card">
                    <div class="text-renderer-card-header">
                        <span class="text-renderer-card-index">#${i + 1}</span>
                        <span class="text-renderer-card-title">${this.escapeHtml(row[0] || '')}</span>
                    </div>
                    <div class="text-renderer-card-body">${fields}</div>
                </div>
            `;
        }).join('');

        const more = rows.length > this.options.maxItems 
            ? `<div class="text-renderer-more">還有 ${rows.length - this.options.maxItems} 項...</div>` 
            : '';

        return `<div class="text-renderer-list">${html}${more}</div>`;
    }

    /**
     * 列表格式偵測
     */
    isListFormat(content) {
        const lines = content.split('\n');
        const listLines = lines.filter(l => l.match(/^[-•*]\s+/) || l.match(/^\d+\.\s+/));
        return listLines.length >= 2;
    }

    /**
     * 列表渲染
     */
    renderList(content) {
        const lines = content.split('\n');
        let html = '';
        let items = [];

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            // 項目符號
            const bulletMatch = trimmed.match(/^[-•*]\s+(.+)$/);
            if (bulletMatch) {
                items.push(bulletMatch[1]);
                continue;
            }

            // 編號列表
            const numberMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
            if (numberMatch) {
                items.push({ index: numberMatch[1], text: numberMatch[2] });
                continue;
            }

            // 標題
            if (trimmed.match(/^===.+===$/)) {
                if (items.length > 0) {
                    html += this.renderListItems(items);
                    items = [];
                }
                html += `<div class="text-renderer-heading">${this.escapeHtml(trimmed.replace(/===/g, '').trim())}</div>`;
                continue;
            }

            // 其他文字
            if (items.length > 0) {
                html += this.renderListItems(items);
                items = [];
            }
            html += `<div class="text-renderer-paragraph">${this.escapeHtml(trimmed)}</div>`;
        }

        if (items.length > 0) {
            html += this.renderListItems(items);
        }

        return `<div class="text-renderer-content">${html}</div>`;
    }

    /**
     * 渲染列表項目
     */
    renderListItems(items) {
        const html = items.slice(0, this.options.maxItems).map((item, i) => {
            if (typeof item === 'object') {
                return `
                    <div class="text-renderer-list-item">
                        <span class="text-renderer-list-index">${item.index}</span>
                        <span class="text-renderer-list-text">${this.escapeHtml(item.text)}</span>
                    </div>
                `;
            }
            return `
                <div class="text-renderer-list-item">
                    <span class="text-renderer-list-bullet">•</span>
                    <span class="text-renderer-list-text">${this.escapeHtml(item)}</span>
                </div>
            `;
        }).join('');

        return `<div class="text-renderer-list-group">${html}</div>`;
    }

    /**
     * 純文字渲染
     */
    renderPlainText(content) {
        let html = this.escapeHtml(content);
        
        // 轉換標題
        html = html.replace(/^=== (.+) ===$/gm, '<div class="text-renderer-heading">$1</div>');
        
        // 轉換項目符號
        html = html.replace(/^[-•*]\s+(.+)$/gm, '<div class="text-renderer-list-item"><span class="text-renderer-list-bullet">•</span><span class="text-renderer-list-text">$1</span></div>');
        
        // 轉換編號列表
        html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<div class="text-renderer-list-item"><span class="text-renderer-list-index">$1</span><span class="text-renderer-list-text">$2</span></div>');
        
        // 換行
        html = html.replace(/\n/g, '<br>');
        
        // 清理多餘 <br>
        html = html.replace(/(<br>){3,}/g, '<br><br>');
        
        return `<div class="text-renderer-content">${html}</div>`;
    }

    /**
     * 空狀態
     */
    renderEmpty(message = '暫無內容') {
        return `
            <div class="text-renderer-empty">
                <span class="material-icons-outlined">description</span>
                <div>${message}</div>
            </div>
        `;
    }

    /**
     * 列表項目
     */
    renderListItem(index, content) {
        return `
            <div class="text-renderer-card">
                <div class="text-renderer-card-header">
                    <span class="text-renderer-card-index">#${index + 1}</span>
                </div>
                <div class="text-renderer-card-body">${content}</div>
            </div>
        `;
    }

    /**
     * 格式化數字
     */
    formatNumber(num) {
        if (Number.isInteger(num)) {
            return num.toLocaleString();
        }
        return num.toFixed(2);
    }

    /**
     * HTML 轉義
     */
    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}

// 全域實例
window.textRenderer = new TextRenderer();

/**
 * 快速渲染函數
 */
function renderTextContent(content, container) {
    if (typeof container === 'string') {
        container = document.getElementById(container);
    }
    if (container) {
        container.innerHTML = window.textRenderer.render(content);
    }
}
