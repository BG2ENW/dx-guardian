/**
 * DX Guardian - 前端主逻辑 v1.3（波段筛选 + 地图展示）
 */
let map = null;
let markers = [];
let socket = null;
let totalSpots = 0;
let bandCounts = {
    '160m': 0, '80m': 0, '60m': 0, '40m': 0, '30m': 0,
    '20m': 0, '17m': 0, '15m': 0, '12m': 0, '10m': 0, '6m': 0,
    '2m': 0, '70cm': 0, '23cm': 0
};

const MODE_COLORS = {
    'CW': '#FF5733',
    'SSB': '#2196F3',
    'FT8': '#4CAF50',
    'FT4': '#8BC34A',
    'RTTY': '#FF9800',
    'PSK31': '#9C27B0',
    'AM': '#795548',
    'FM': '#607D8B',
    'UNKNOWN': '#999999'
};

const BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m'];

// 本地台站配置（启动时从后端 API加载）
const MY_STATION = {
    callsign: 'BG2ENW',
    grid: 'PN35HS',
    lat: 45.8,
    lon: 126.5,
    location: '哈尔滨',
    power: 100,
    antenna: ''
};

let myStationMarker = null;
let heatLayer = null;
let showHeatmap = false;
let gridOverlayLayer = null;
let showGridOverlay = false;

// === 台站配置管理 ===
async function loadStationConfig() {
    try {
        const resp = await fetch('/api/user/station');
        if (resp.ok) {
            const config = await resp.json();
            MY_STATION.callsign = config.callsign || MY_STATION.callsign;
            MY_STATION.grid = config.grid || MY_STATION.grid;
            MY_STATION.lat = config.lat || MY_STATION.lat;
            MY_STATION.lon = config.lon || MY_STATION.lon;
            MY_STATION.power = config.power || 100;
            MY_STATION.antenna = config.antenna || '';
            
            // 更新显示
            document.getElementById('st-call').textContent = MY_STATION.callsign;
            document.getElementById('st-grid').textContent = MY_STATION.grid || '--';
            document.getElementById('st-power').textContent = MY_STATION.power ? MY_STATION.power + 'W' : '--';
            document.getElementById('st-antenna').textContent = MY_STATION.antenna || '--';
        }
    } catch (e) {
        console.error('加载台站配置失败:', e);
    }
}

function openStationEdit() {
    const modal = document.getElementById('station-modal');
    if (!modal) return;
    document.getElementById('edit-callsign').value = MY_STATION.callsign || '';
    document.getElementById('edit-grid').value = MY_STATION.grid || '';
    document.getElementById('edit-power').value = MY_STATION.power || '';
    document.getElementById('edit-antenna').value = MY_STATION.antenna || '';
    document.getElementById('station-save-status').textContent = '';
    modal.style.display = 'flex';
}

function closeStationModal() {
    const modal = document.getElementById('station-modal');
    if (modal) modal.style.display = 'none';
}

function editStation() {
    openStationEdit();
}

async function saveStationConfig() {
    const callsign = document.getElementById('edit-callsign').value.trim().toUpperCase();
    const grid = document.getElementById('edit-grid').value.trim().toUpperCase();
    const power = parseInt(document.getElementById('edit-power').value) || 100;
    const antenna = document.getElementById('edit-antenna').value.trim();
    
    // 简单验证
    if (!callsign || callsign.length < 3) {
        alert('请输入有效的呼号');
        return;
    }
    
    try {
        // Grid 转 lat/lon（简单处理，如果 Grid 有效的话）
        let lat = MY_STATION.lat;
        let lon = MY_STATION.lon;
        
        const resp = await fetch('/api/user/station', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({callsign, grid, lat, lon, power, antenna})
        });
        
        const result = await resp.json();
        if (result.success) {
            await loadStationConfig();
            closeStationModal();
            
            // 更新地图上的我的台站标记
            if (myStationMarker) {
                map.removeLayer(myStationMarker);
            }
            addMyStationMarker();
            
            document.getElementById('station-save-status').textContent = '✅ 保存成功';
            setTimeout(() => {
                document.getElementById('station-save-status').textContent = '';
            }, 2000);
        } else {
            document.getElementById('station-save-status').textContent = '❌ ' + (result.error || '保存失败');
        }
    } catch (e) {
        console.error('保存失败:', e);
        document.getElementById('station-save-status').textContent = '❌ 保存失败';
    }
}

let wavelogLoaded = false;

// === 关注列表管理 ===
let watchlistItems = [];
const WATCHLIST_TYPES = [
    {value: 'callsign', label: '呼号'},
    {value: 'dxcc', label: 'DXCC实体'},
    {value: 'prefix', label: '呼号前缀'},
    {value: 'band', label: '波段'},
    {value: 'mode', label: '模式'}
];

async function loadWatchlist() {
    try {
        const resp = await fetch('/api/user/watchlist');
        if (resp.ok) {
            const data = await resp.json();
            watchlistItems = data.items || [];
            renderWatchlist();
        }
    } catch (e) {
        console.error('加载关注列表失败:', e);
    }
}

function renderWatchlist() {
    const container = document.getElementById('watchlist-container');
    if (!container) return;

    if (watchlistItems.length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:12px;">暂无关注项，点击右上角添加</div>';
        return;
    }

    container.innerHTML = watchlistItems.map(item => {
        const typeLabel = WATCHLIST_TYPES.find(t => t.value === item.target_type)?.label || item.target_type;
        const colorMap = {callsign: '#4CAF50', dxcc: '#2196F3', prefix: '#FF9800', band: '#e94560', mode: '#9C27B0'};
        const color = colorMap[item.target_type] || '#888';
        const enabledStyle = item.enabled ? '' : 'opacity:0.4;';
        const bandTag = item.band_preference ? `<span class="watchlist-tag">${item.band_preference}</span>` : '';
        const modeTag = item.mode_preference ? `<span class="watchlist-tag">${item.mode_preference}</span>` : '';

        return `<div class="watchlist-item" style="${enabledStyle}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span class="watchlist-type" style="color:${color};margin-right:4px;">${typeLabel}</span>
                    <span class="watchlist-call">${item.target_value}</span>${bandTag}${modeTag}
                </div>
                <div style="display:flex;gap:4px;">
                    <button class="wl-btn wl-status" onclick="toggleWatchlistItem('${item.id}', ${!item.enabled})">${item.enabled ? '🟢' : '⚪'}</button>
                    <button class="wl-btn wl-delete" onclick="removeWatchlistItem('${item.id}')">✕</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

function openWatchlistModal() {
    const modal = document.getElementById('watchlist-modal');
    if (!modal) return;
    document.getElementById('wl-type').value = 'callsign';
    document.getElementById('wl-value').value = '';
    document.getElementById('wl-band').value = '';
    document.getElementById('wl-mode').value = '';
    document.getElementById('wl-status').textContent = '';
    modal.style.display = 'flex';
}

function closeWatchlistModal() {
    const modal = document.getElementById('watchlist-modal');
    if (modal) modal.style.display = 'none';
}

async function addWatchlistItem() {
    const target_type = document.getElementById('wl-type').value;
    const target_value = document.getElementById('wl-value').value.trim();
    const band_preference = document.getElementById('wl-band').value.trim();
    const mode_preference = document.getElementById('wl-mode').value.trim();

    if (!target_value) {
        document.getElementById('wl-status').textContent = '❌ 请输入目标值';
        return;
    }

    try {
        const resp = await fetch('/api/user/watchlist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({target_type, target_value, band_preference, mode_preference})
        });
        const result = await resp.json();
        if (result.success) {
            watchlistItems.push(result.item);
            renderWatchlist();
            closeWatchlistModal();
        } else {
            document.getElementById('wl-status').textContent = '❌ ' + (result.error || '添加失败');
        }
    } catch (e) {
        document.getElementById('wl-status').textContent = '❌ 网络错误';
    }
}

async function removeWatchlistItem(id) {
    try {
        const resp = await fetch(`/api/user/watchlist/${id}`, {method: 'DELETE'});
        if (resp.ok) {
            watchlistItems = watchlistItems.filter(i => i.id !== id);
            renderWatchlist();
        }
    } catch (e) {
        console.error('删除失败:', e);
    }
}

async function toggleWatchlistItem(id, enabled) {
    try {
        const resp = await fetch(`/api/user/watchlist/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled})
        });
        if (resp.ok) {
            const item = watchlistItems.find(i => i.id === id);
            if (item) item.enabled = enabled;
            renderWatchlist();
        }
    } catch (e) {
        console.error('更新失败:', e);
    }
}

// === 时间筛选 ===
let timeFilter = 30; // 默认 30 分钟
const TIME_OPTIONS = [
    {label: '15 分钟', value: 15},
    {label: '30 分钟', value: 30},
    {label: '1 小时', value: 60},
    {label: '2 小时', value: 120},
    {label: '4 小时', value: 240},
    {label: '全部', value: 0}
];

// === 模式筛选 ===
let modeFilter = 'FT8'; // 默认只显示 FT8
const MODE_FILTER_OPTIONS = [
    {value: 'ALL', label: '所有模式'},
    {value: 'FT8', label: 'FT8'},
    {value: 'FT4', label: 'FT4'},
    {value: 'CW', label: 'CW'},
    {value: 'SSB', label: 'SSB'},
    {value: 'RTTY', label: 'RTTY'},
];

// === 波段筛选 ===
let activeBandFilter = null; // 当前筛选的波段

// 所有 Spot 历史（带时间戳和标记）
const spotHistory = []; // {spot, marker, receivedAt}
const MAX_HISTORY = 500; // 限制最多 500 条，避免页面卡顿

const startTime = Date.now();

// ========== 主题配色管理 ==========
function initTheme() {
    const saved = localStorage.getItem('dx-theme');
    if (saved) {
        applyTheme(saved);
    }
}

function toggleThemeDropdown() {
    const dropdown = document.getElementById('theme-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

function setTheme(themeName) {
    applyTheme(themeName);
    localStorage.setItem('dx-theme', themeName);
    const dropdown = document.getElementById('theme-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    updateThemeUI(themeName);
}

function applyTheme(themeName) {
    if (themeName === 'default') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', themeName);
    }
    updateThemeUI(themeName);
}

function updateThemeUI(themeName) {
    document.querySelectorAll('.theme-option').forEach(opt => {
        opt.classList.toggle('active', opt.dataset.theme === themeName);
    });
}

function closeThemeDropdown() {
    const dropdown = document.getElementById('theme-dropdown');
    if (dropdown) dropdown.classList.remove('show');
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.theme-selector')) {
        closeThemeDropdown();
    }
});

function initMapHeightResize() {
    const handle = document.getElementById('map-height-resize-handle');
    const column = document.getElementById('column-map');
    if (!handle || !column) return;
    
    handle.addEventListener('mousedown', function(e) {
        mapHeightResizing = true;
        document.body.style.cursor = 'ns-resize';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!mapHeightResizing) return;
        
        // 计算新高度（从视口顶部到鼠标位置）
        const viewportHeight = window.innerHeight;
        const newHeight = (e.clientY / viewportHeight) * 100;
        
        if (newHeight > 30 && newHeight < 90) {
            column.style.height = newHeight + 'vh';
            mapHeightPercent = newHeight;
            if (map) {
                map.invalidateSize();
            }
        }
    });
    
    document.addEventListener('mouseup', function() {
        if (mapHeightResizing) {
            mapHeightResizing = false;
            document.body.style.cursor = '';
            if (map) {
                map.invalidateSize();
            }
        }
    });
}

// ========== QSO 统计更新 ==========
function updateQsoStats() {
    if (!spotHistory || spotHistory.length === 0) return;
    
    qsoCallingMe = [];
    qsoHeardMe = [];
    
    // 从最近的 spot 中筛选
    const recentSpots = spotHistory.slice(-100); // 看最近 100 条
    
    recentSpots.forEach(entry => {
        const spot = entry.spot;
        const comments = (spot.comments || '').toUpperCase();
        const myCall = MY_STATION.callsign.toUpperCase();
        
        // 检查是否包含我的呼号
        if (comments.includes(myCall)) {
            // 判断是呼叫我还是听到我
            if (comments.includes('CQ') && !comments.includes('CQ ' + myCall)) {
                // 其他台呼叫 CQ 时提到我
                if (!qsoCallingMe.find(q => q.call === spot.de_call)) {
                    qsoCallingMe.push({
                        call: spot.de_call,
                        country: spot.country || guessCountry(spot.de_call),
                        freq: spot.freq || spot.de_freq || '',
                        mode: spot.mode || '',
                        signal: spot.signal || extractSignal(comments),
                        time: spot.time,
                        band: spot.band || freqToBand(spot.de_freq)
                    });
                }
            }
            if (comments.includes('HEARD') || comments.includes('抄收') || comments.includes('R ' + myCall) || comments.includes('RST')) {
                // 其他台表示听到我
                if (!qsoHeardMe.find(q => q.call === spot.de_call)) {
                    // 从 comments 提取信号报告
                    const rst = extractRST(comments);
                    qsoHeardMe.push({
                        call: spot.de_call,
                        country: spot.country || guessCountry(spot.de_call),
                        freq: spot.freq || spot.de_freq || '',
                        mode: spot.mode || '',
                        signal: rst || extractSignal(comments),
                        time: spot.time,
                        band: spot.band || freqToBand(spot.de_freq)
                    });
                }
            }
        }
    });
    
    // 按时间排序，最新的在前
    qsoCallingMe.sort((a, b) => new Date(b.time) - new Date(a.time));
    qsoHeardMe.sort((a, b) => new Date(b.time) - new Date(a.time));
    
    // 更新显示
    renderQsoStats();
}

function renderQsoStats() {
    // 更新数量
    document.getElementById('qso-calling-me-count').textContent = qsoCallingMe.length;
    document.getElementById('qso-heard-me-count').textContent = qsoHeardMe.length;
    
    // 更新呼叫我列表 - 显示 10 个最新的
    const callingList = document.getElementById('qso-calling-me-list');
    if (qsoCallingMe.length === 0) {
        callingList.innerHTML = '<div style="color:#888;">暂无数据</div>';
    } else {
        callingList.innerHTML = qsoCallingMe.slice(0, 10).map(q => `
            <div class="qso-item">
                <div class="qso-info">
                    <span class="qso-callsign">${q.call}</span>
                    <span class="qso-country">${q.country || ''}</span>
                </div>
                <div class="qso-meta">
                    <span class="qso-band">${q.band || '--'}</span>
                    <span class="qso-mode">${q.mode || '--'}</span>
                    <span class="qso-signal">${q.signal ? q.signal + 'dB' : ''}</span>
                </div>
                <span class="qso-time">${formatQsoTime(q.time)}</span>
            </div>
        `).join('');
    }
    
    // 更新听到我列表 - 显示 10 个最新的
    const heardList = document.getElementById('qso-heard-me-list');
    if (qsoHeardMe.length === 0) {
        heardList.innerHTML = '<div style="color:#888;">暂无数据</div>';
    } else {
        heardList.innerHTML = qsoHeardMe.slice(0, 10).map(q => `
            <div class="qso-item">
                <div class="qso-info">
                    <span class="qso-callsign">${q.call}</span>
                    <span class="qso-country">${q.country || ''}</span>
                </div>
                <div class="qso-meta">
                    <span class="qso-band">${q.band || '--'}</span>
                    <span class="qso-mode">${q.mode || '--'}</span>
                    <span class="qso-signal">${q.signal ? ((q.signal>0)?'+':'') + q.signal : ''}</span>
                </div>
                <span class="qso-time">${formatQsoTime(q.time)}</span>
            </div>
        `).join('');
    }
}

function guessCountry(callsign) {
    // 简单的前缀判断国家
    const prefix = callsign.substring(0, 2).toUpperCase();
    const countryMap = {
        'BG': '中国', 'BI': '中国', 'BD': '中国', 'BV': '中国', 'BA': '中国',
        'JA': '日本', 'JE': '日本', 'JH': '日本', 'JI': '日本', 'JK': '日本',
        'HL': '韩国', 'DS': '韩国', 'DT': '韩国', 'DF': '韩国',
        'W': '美国', 'K': '美国', 'N': '美国', 'AA': '美国',
        'G': '英国', 'M': '英国', '2': '英国',
        'F': '法国', 'PA': '荷兰', 'DH': '德国', 'DK': '德国', 'DL': '德国',
        'I': '意大利', 'EA': '西班牙', 'EB': '西班牙', 'EC': '西班牙',
        'UA': '俄罗斯', 'UB': '俄罗斯', 'UC': '俄罗斯', 'R': '俄罗斯',
        'VK': '澳大利亚', 'AX': '澳大利亚', 'VE': '加拿大', 'VA': '加拿大'
    };
    return countryMap[prefix] || countryMap[callsign.substring(0, 1)] || '';
}

function extractSignal(comments) {
    // 从 comments 提取信号强度 (如 -18 dB, 59 等)
    const match = comments.match(/(-?\d+)\s?DB/);
    if (match) return parseInt(match[1]);
    const rstMatch = comments.match(/\b(\d)(\d)(\d)\b/);
    if (rstMatch) return parseInt(rstMatch[3]);
    return null;
}

function extractRST(comments) {
    // 提取 RST 信号报告的第 3 位（信号强度）
    const match = comments.match(/\b(\d)(\d)(\d)\b/);
    if (match) return parseInt(match[3]);
    return null;
}

function formatQsoTime(isoTime) {
    if (!isoTime) return '--';
    try {
        const date = new Date(isoTime);
        const now = new Date();
        const diff = Math.floor((now - date) / 60000); // 分钟
        
        if (diff < 1) return '刚刚';
        if (diff < 60) return diff + ' 分前';
        if (diff < 1440) return Math.floor(diff / 60) + ' 小时前';
        return date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'});
    } catch {
        return '--';
    }
}

function freqToBand(freqKhz) {
    if (!freqKhz) return '';
    const freqMhz = parseFloat(freqKhz) / 1000;
    if (freqMhz < 2) return '160m';
    if (freqMhz < 4) return '80m';
    if (freqMhz < 5.5) return '60m';
    if (freqMhz < 8) return '40m';
    if (freqMhz < 11) return '30m';
    if (freqMhz < 15) return '20m';
    if (freqMhz < 19) return '17m';
    if (freqMhz < 22) return '15m';
    if (freqMhz < 25) return '12m';
    if (freqMhz < 30) return '10m';
    if (freqMhz < 60) return '6m';
    if (freqMhz < 150) return '2m';
    if (freqMhz < 500) return '70cm';
    return '';
}

async function loadSolarData() {
    try {
        const resp = await fetch('/api/stats/solar');
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.success && data.solar) {
            const s = data.solar;
            const el1 = document.getElementById('solar-sfi'); if (el1) el1.textContent = s.sfi || '--';
            const el2 = document.getElementById('solar-ssn'); if (el2) el2.textContent = s.ssn || '--';
            const el3 = document.getElementById('solar-k'); if (el3) el3.textContent = s.k_index || '--';
            const el4 = document.getElementById('solar-a'); if (el4) el4.textContent = s.a_index || '--';
        }
    } catch(e) { console.error('加载太阳数据失败:', e); }
}

function updateSystemStatus(data) {
    const el1 = document.getElementById('cluster-status');
    if (el1) el1.textContent = data.cluster_connected ? '已连接' : '未连接';
    const el2 = document.getElementById('psk-status');
    if (el2) el2.textContent = data.psk_connected ? '已连接' : '等待中';
    const el3 = document.getElementById('cache-count');
    if (el3) el3.textContent = spotHistory.length;
}

function initDragAndDrop() {
    if (typeof Sortable === 'undefined') return;
    ['col-left', 'col-right'].forEach(colId => {
        const el = document.getElementById(colId);
        if (!el) return;
        Sortable.create(el, {
            group: 'cards', animation: 150, handle: '.card-header',
            ghostClass: 'sortable-ghost', chosenClass: 'sortable-chosen',
            store: {
                get: function(s) {
                    const order = localStorage.getItem('dx-card-order-' + s.el.id);
                    return order ? order.split('|') : [];
                },
                set: function(s) {
                    localStorage.setItem('dx-card-order-' + s.el.id, s.toArray().join('|'));
                }
            }
        });
    });
    restoreCardOrder();
}

function restoreCardOrder() {
    ['col-left', 'col-right'].forEach(colId => {
        const order = localStorage.getItem('dx-card-order-' + colId);
        if (!order) return;
        const col = document.getElementById(colId);
        if (!col) return;
        order.split('|').filter(id => document.getElementById(id)).forEach(id => {
            const el = document.getElementById(id);
            if (el && el.parentElement === col) col.appendChild(el);
        });
    });
}

function toggleCard(id) {
    const card = document.getElementById(id);
    if (card) card.classList.toggle('collapsed');
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadStationConfig();
    loadWatchlist();
    loadSolarData();
    setInterval(loadSolarData, 300000);
    initMap();
    initMapResize();
    initMapHeightResize();
    initSocket();
    renderBandBar();
    loadHistory();
    initDragAndDrop();
    updateUptime();
    setInterval(updateUptime, 60000);
    setInterval(() => {
        const el = document.getElementById('cache-count');
        if (el) el.textContent = spotHistory.length;
        updateQsoStats(); // 更新 QSO 统计
    }, 5000);
    setInterval(() => { if (showHeatmap) updateHeatmap(); }, 30000);
    loadPropagation();
    setInterval(loadPropagation, 300000);
    loadTrends();
    setInterval(loadTrends, 60000);
    loadVOACAP();
    setInterval(loadVOACAP, 300000);
    loadBandOpening();
    setInterval(loadBandOpening, 300000);
    // 点击模态框外部关闭
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.style.display = 'none';
        });
    });
});

// ========== 传播预测面板 ==========
function initMap() {
    map = L.map('dx-map').setView([MY_STATION.lat, MY_STATION.lon], 3);
    
    // 设置控件容器 z-index，确保按钮始终可见
    setTimeout(() => {
        const zoomControl = document.querySelector('.leaflet-control-zoom');
        const attribution = document.querySelector('.leaflet-control-container .leaflet-control-attribution');
        if (zoomControl) zoomControl.style.zIndex = '999';
        if (attribution) attribution.style.zIndex = '999';
        
        // 确保自定义控件始终在最上层
        const topControls = document.querySelector('.map-controls-top');
        const bottomControls = document.querySelector('.map-controls-bottom');
        if (topControls) topControls.style.zIndex = '1001';
        if (bottomControls) bottomControls.style.zIndex = '1001';
    }, 100);
    
    L.tileLayer('https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
        attribution: '&copy; 高德地图',
        maxZoom: 19,
        minZoom: 2
    }).addTo(map);

    // 添加本地台站标记
    addMyStationMarker();

    // 初始化热点图层（默认隐藏）
    heatLayer = L.heatLayer([], {
        radius: 25,
        blur: 15,
        maxZoom: 8,
        max: 1.0,
        gradient: {
            0.0: '#1a1a2e',
            0.2: '#16213e',
            0.4: '#0f3460',
            0.6: '#e94560',
            0.8: '#FF5733',
            1.0: '#FFD700'
        }
    });
    
    // 初始化网格图层（默认隐藏）
    gridOverlayLayer = L.layerGroup();
    
    // 监听地图移动和缩放，动态更新网格
    map.on('moveend', updateGridOnMove);
    map.on('zoomend', updateGridOnMove);
}

// 添加本地台站标记
function addMyStationMarker() {
    const myIcon = L.divIcon({
        className: 'my-station-marker',
        html: '<div style="background:#FFD700;border:3px solid #fff;border-radius:50%;width:18px;height:18px;box-shadow:0 0 12px #FFD700, 0 0 4px #FFD700;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });

    myStationMarker = L.marker([MY_STATION.lat, MY_STATION.lon], {icon: myIcon}).addTo(map);

    myStationMarker.bindPopup(
        '<div style="min-width:160px;">' +
        '<div style="font-weight:bold;font-size:14px;color:#FFD700;margin-bottom:6px;">🏠 ' + MY_STATION.callsign + ' (我的台站)</div>' +
        '<div style="font-size:12px;color:#888">' +
        '📍 Grid: ' + MY_STATION.grid + '<br/>' +
        '🌍 位置: ' + MY_STATION.location + '<br/>' +
        '📡 ' + MY_STATION.lat.toFixed(2) + ', ' + MY_STATION.lon.toFixed(2) +
        '</div></div>'
    ).openPopup();
}

// 热点图功能
function toggleHeatmap() {
    if (!map) return;
    showHeatmap = !showHeatmap;
    const btn = document.getElementById('btn-heat');
    if (showHeatmap) {
        updateHeatmap();
        heatLayer.addTo(map);
        if (btn) btn.classList.add('active');
    } else {
        map.removeLayer(heatLayer);
        if (btn) btn.classList.remove('active');
    }
}

function updateHeatmap() {
    if (!heatLayer || !map) return;
    
    // 从 spotHistory 提取坐标数据 [lat, lon, intensity]
    const heatData = spotHistory
        .filter(entry => entry.marker && entry.spot.lat && entry.spot.lon)
        .map(entry => {
            const spot = entry.spot;
            return [spot.lat, spot.lon, 1.0];
        });
    
    if (heatData.length > 0) {
        heatLayer.setLatLngs(heatData);
    }
}

// 地图缩放控制
function zoomMap(delta) {
    if (!map) return;
    const zoom = map.getZoom();
    map.setZoom(zoom + delta);
}

function resetMapZoom() {
    if (!map) return;
    map.setView([20, 0], 2);
}

// ========== 地图显示控制 ==========
let mapResizing = false;
let mapWidth = 65; // 默认宽度百分比
let mapClosed = false; // 地图是否已关闭
let mapHeightResizing = false; // 地图高度调整中
let mapHeightPercent = 80; // 默认高度百分比（相对于视口）
let qsoCallingMe = []; // 呼叫我电台的列表
let qsoHeardMe = []; // 收到我电台的列表

function closeMap() {
    const column = document.getElementById('column-map');
    const toggleBtn = document.getElementById('map-toggle-btn');
    
    if (column) {
        column.style.display = 'none';
        column.classList.add('collapsed');
    }
    if (toggleBtn) {
        toggleBtn.classList.remove('hidden');
        toggleBtn.style.right = '240px'; // 初始位置
    }
    mapClosed = true;
    
    if (map) {
        setTimeout(() => map.invalidateSize(), 300);
    }
}

function toggleMap() {
    const column = document.getElementById('column-map');
    const toggleBtn = document.getElementById('map-toggle-btn');
    if (!column) return;
    
    if (mapClosed) {
        column.style.display = 'block';
        column.style.width = mapWidth + '%';
        column.classList.remove('collapsed');
        if (toggleBtn) toggleBtn.classList.add('hidden');
        mapClosed = false;
        setTimeout(() => {
            if (map) {
                map.invalidateSize();
                // 重新添加图层
                if (showHeatmap && heatLayer) heatLayer.addTo(map);
                if (showGrayline && graylineLayer) graylineLayer.addTo(map);
                if (showGridOverlay && gridOverlayLayer) gridOverlayLayer.addTo(map);
            }
        }, 300);
    } else {
        closeMap();
    }
}

function initMapResize() {
    const handle = document.getElementById('map-resize-handle');
    const column = document.getElementById('column-map');
    const moduleContainer = document.querySelector('.map-module-container');
    if (!handle || !column) return;
    
    handle.addEventListener('mousedown', function(e) {
        mapResizing = true;
        document.body.style.cursor = 'col-resize';
        if (moduleContainer) moduleContainer.classList.add('resizing');
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!mapResizing) return;
        
        // 计算新宽度：从左侧列右侧 (240px) 到鼠标位置
        const containerWidth = window.innerWidth;
        const newWidth = ((e.clientX - 240) / containerWidth) * 100;
        
        if (newWidth > 30 && newWidth < 70) {
            column.style.width = newWidth + '%';
            mapWidth = newWidth;
            if (map) {
                map.invalidateSize();
            }
        }
    });
    
    document.addEventListener('mouseup', function() {
        if (mapResizing) {
            mapResizing = false;
            document.body.style.cursor = '';
            if (moduleContainer) moduleContainer.classList.remove('resizing');
            if (map) {
                map.invalidateSize();
            }
        }
    });
}

function initMapHeightResize() {
    const handle = document.getElementById('map-height-resize-handle');
    const column = document.getElementById('column-map');
    const moduleContainer = document.querySelector('.map-module-container');
    if (!handle || !column) return;
    
    handle.addEventListener('mousedown', function(e) {
        mapHeightResizing = true;
        document.body.style.cursor = 'ns-resize';
        if (moduleContainer) moduleContainer.classList.add('resizing');
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!mapHeightResizing) return;
        
        // 计算新高度（从视口顶部到鼠标位置）
        const viewportHeight = window.innerHeight;
        const newHeight = (e.clientY / viewportHeight) * 100;
        
        if (newHeight > 30 && newHeight < 90) {
            column.style.height = newHeight + 'vh';
            mapHeightPercent = newHeight;
            if (map) {
                map.invalidateSize();
            }
        }
    });
    
    document.addEventListener('mouseup', function() {
        if (mapHeightResizing) {
            mapHeightResizing = false;
            document.body.style.cursor = '';
            if (moduleContainer) moduleContainer.classList.remove('resizing');
            if (map) {
                map.invalidateSize();
            }
        }
    });
}

// ========== 灰线覆盖层 ==========
let showGrayline = false;
let graylineLayer = null;
let graylineUpdateTimer = null;

// ========== Maidenhead Grid 网格显示 ==========
function toggleGridOverlay() {
    if (!map) return;
    showGridOverlay = !showGridOverlay;
    const btn = document.getElementById('btn-grid');
    
    if (showGridOverlay) {
        if (btn) btn.classList.add('active');
        renderGridOverlay();
    } else {
        if (btn) btn.classList.remove('active');
        if (gridOverlayLayer) {
            map.removeLayer(gridOverlayLayer);
            gridOverlayLayer.clearLayers();
        }
    }
}

function renderGridOverlay() {
    if (!gridOverlayLayer) return;
    
    gridOverlayLayer.clearLayers();
    
    const bounds = map.getBounds();
    const latBounds = [bounds.getSouth(), bounds.getNorth()];
    const lonBounds = [bounds.getWest(), bounds.getEast()];
    
    // 根据缩放级别决定网格大小
    const zoom = map.getZoom();
    let fieldSize = 20; // Field 大小（度数）
    let subfieldSize = 2; // Square 大小（度数）
    let showSubfields = zoom >= 6;
    let showEnhanced = zoom >= 10;
    
    if (zoom >= 8) {
        fieldSize = 10;
        subfieldSize = 1;
    }
    if (zoom >= 10) {
        fieldSize = 5;
        subfieldSize = 0.5;
    }
    
    const lines = [];
    
    // 绘制 Field 网格（10 度间隔）
    for (let lon = Math.floor(lonBounds[0] / fieldSize) * fieldSize; 
         lon <= lonBounds[1]; 
         lon += fieldSize) {
        lines.push(L.polyline([[latBounds[0], lon], [latBounds[1], lon]], {
            color: 'rgba(255, 255, 255, 0.3)',
            weight: 1,
            dashArray: '5, 10'
        }));
    }
    
    for (let lat = Math.floor(latBounds[0] / fieldSize) * fieldSize; 
         lat <= latBounds[1]; 
         lat += fieldSize) {
        lines.push(L.polyline([[lat, lonBounds[0]], [lat, lonBounds[1]]], {
            color: 'rgba(255, 255, 255, 0.3)',
            weight: 1,
            dashArray: '5, 10'
        }));
    }
    
    // 绘制 Square 网格（2 度间隔，Zoom 6+ 显示）
    if (showSubfields) {
        for (let lon = Math.floor(lonBounds[0] / subfieldSize) * subfieldSize; 
             lon <= lonBounds[1]; 
             lon += subfieldSize) {
            lines.push(L.polyline([[latBounds[0], lon], [latBounds[1], lon]], {
                color: 'rgba(255, 255, 255, 0.15)',
                weight: 0.5,
                dashArray: '3, 5'
            }));
        }
        
        for (let lat = Math.floor(latBounds[0] / subfieldSize) * subfieldSize; 
             lat <= latBounds[1]; 
             lat += subfieldSize) {
            lines.push(L.polyline([[lat, lonBounds[0]], [lat, lonBounds[1]]], {
                color: 'rgba(255, 255, 255, 0.15)',
                weight: 0.5,
                dashArray: '3, 5'
            }));
        }
    }
    
    // 在地图中心显示当前 Grid 信息
    const center = map.getCenter();
    const gridLabel = calculateMaidenheadGrid(center.lat, center.lng);
    const centerMarker = L.marker([center.lat, center.lng], {
        icon: L.divIcon({
            className: 'grid-label',
            html: `<div style="background:rgba(0,0,0,0.7);color:#0f0;padding:4px 8px;border-radius:4px;font-size:12px;font-family:monospace;border:1px solid #0f0;">${gridLabel}</div>`,
            iconSize: [80, 24],
            iconAnchor: [40, 12]
        })
    });
    
    lines.forEach(line => gridOverlayLayer.addLayer(line));
    gridOverlayLayer.addLayer(centerMarker);
    gridOverlayLayer.addTo(map);
}

function calculateMaidenheadGrid(lat, lon) {
    // 计算 Maidenhead Grid _locator（6 位）
    const fieldLon = Math.floor((lon + 180) / 20);
    const fieldLat = Math.floor((lat + 90) / 10);
    
    const squareLon = Math.floor(((lon + 180) % 20) / 2);
    const squareLat = Math.floor(((lat + 90) % 10) / 1);
    
    const subLon = Math.floor((((lon + 180) % 20) % 2) / 0.08333);
    const subLat = Math.floor((((lat + 90) % 10) % 1) / 0.04166);
    
    const fieldChars = 'ABCDEFGHIJKLMNOPQRSTUVWX';
    const squareDigits = '0123456789';
    const subChars = 'abcdefghijklmnopqrstuvwx';
    
    return fieldChars[fieldLon] + 
           fieldChars[fieldLat] + 
           squareDigits[squareLon] + 
           squareDigits[squareLat] +
           subChars[subLon].toUpperCase() +
           subChars[subLat].toUpperCase();
}

// 地图移动时更新网格
function updateGridOnMove() {
    if (showGridOverlay && gridOverlayLayer) {
        renderGridOverlay();
    }
}

async function toggleGrayline() {
    if (!map) return;
    showGrayline = !showGrayline;
    const btn = document.getElementById('btn-gray');
    
    if (showGrayline) {
        if (btn) btn.classList.add('active');
        await loadGrayline();
        // 每 5 分钟更新灰线
        graylineUpdateTimer = setInterval(loadGrayline, 300000);
    } else {
        if (btn) btn.classList.remove('active');
        if (graylineLayer) {
            map.removeLayer(graylineLayer);
            graylineLayer = null;
        }
        if (graylineUpdateTimer) {
            clearInterval(graylineUpdateTimer);
            graylineUpdateTimer = null;
        }
    }
}

async function loadGrayline() {
    try {
        const resp = await fetch('/api/terminator');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success || !data.terminator) return;
        renderGrayline(data.terminator);
    } catch(e) {
        console.error('加载灰线数据失败:', e);
    }
}

function renderGrayline(geojson) {
    if (!map) return;
    
    // 移除旧图层
    if (graylineLayer) {
        map.removeLayer(graylineLayer);
    }
    
    // 灰线样式
    const lineStyle = {
        color: '#FFD700',
        weight: 2,
        opacity: 0.8,
        dashArray: '8, 4'
    };
    
    // 夜晚区域半透明覆盖
    const nightStyle = {
        color: '#000033',
        weight: 1,
        fillColor: '#000022',
        fillOpacity: 0.25,
        opacity: 0.6
    };
    
    graylineLayer = L.layerGroup();
    
    // 绘制灰线
    L.geoJSON(geojson, {
        style: lineStyle,
        onEachFeature: function(feature, layer) {
            layer.bindPopup(feature.properties.name + ' (' + feature.properties.type + ')');
        }
    }).addTo(graylineLayer);
    
    // 绘制夜晚区域
    // 找到日出线和日落线坐标
    const sunriseFeature = geojson.features.find(f => f.properties.type === 'sunrise');
    const sunsetFeature = geojson.features.find(f => f.properties.type === 'sunset');
    
    if (sunriseFeature && sunsetFeature) {
        const sunriseCoords = sunriseFeature.geometry.coordinates.map(c => [c[1], c[0]]);
        const sunsetCoords = sunsetFeature.geometry.coordinates.map(c => [c[1], c[0]]);
        
        // 构建夜晚多边形：日出线 → 北极 → 日落线反向 → 南极
        const nightPoly = [];
        nightPoly.push(...sunriseCoords);
        nightPoly.push([90, sunsetCoords[sunsetCoords.length - 1][1]]);
        nightPoly.push(...[...sunsetCoords].reverse());
        nightPoly.push([-90, sunriseCoords[0][1]]);
        
        L.polygon(nightPoly, nightStyle).addTo(graylineLayer);
    }
    
    graylineLayer.addTo(map);
}

// WebSocket
function initSocket() {
    socket = io();

    socket.on('connect', () => {
        updateConnectionStatus(true);
        loadHistory();
    });

    socket.on('disconnect', () => {
        updateConnectionStatus(false);
    });

    // 收到新 Spot
    socket.on('new_spot', (spotData) => {
        if (!isValidSpot(spotData)) return;

        addSpotToHistory(spotData);

        totalSpots++;
        document.getElementById('total-spots').textContent = totalSpots;

        if (spotData.band && bandCounts.hasOwnProperty(spotData.band)) {
            bandCounts[spotData.band]++;
            updateBandCount(spotData.band, bandCounts[spotData.band]);
            updateActiveBands(bandCounts);
        }
    });

    // 波段更新
    socket.on('band_update', (data) => {
        if (data.total !== undefined) {
            totalSpots = data.total;
            document.getElementById('total-spots').textContent = totalSpots;
        }
        if (data.band_counts) {
            bandCounts = {...bandCounts, ...data.band_counts};
            for (const band in data.band_counts) {
                updateBandCount(band, data.band_counts[band]);
            }
            updateActiveBands(bandCounts);
        }
    });

    // 服务器状态
    socket.on('server_status', (data) => {
        updateConnectionStatus(data.cluster_connected || data.connected);
        updateSystemStatus(data);
        updateQsoStats(); // 更新 QSO 统计
        if (data.band_counts) {
            bandCounts = {...bandCounts, ...data.band_counts};
            for (const band in data.band_counts) {
                updateBandCount(band, data.band_counts[band]);
            }
            updateActiveBands(bandCounts);
        }
        if (data.total_spots !== undefined) {
            totalSpots = data.total_spots;
            document.getElementById('total-spots').textContent = totalSpots;
        }
    });
    
    // 太阳数据更新
    socket.on('solar_update', (data) => {
        if (data.sfi) {
            document.getElementById('solar-sfi').textContent = data.sfi;
        }
        if (data.sn) {
            document.getElementById('solar-ssn').textContent = data.sn;
        }
        if (data.k) {
            document.getElementById('solar-k').textContent = data.k;
        }
        if (data.a_index) {
            document.getElementById('solar-a').textContent = data.a_index;
        }
    });
}

// 加载历史
async function loadHistory() {
    try {
        const resp = await fetch('/api/history');
        const data = await resp.json();

        if (data.spots && data.spots.length > 0) {
            console.log(`加载历史: ${data.spots.length} 条`);
            data.spots.forEach(spot => {
                if (!isValidSpot(spot)) return;
                addSpotToHistory(spot, true);
            });

            if (data.total !== undefined) {
                totalSpots = data.total;
                document.getElementById('total-spots').textContent = totalSpots;
            }
            if (data.band_counts) {
                bandCounts = {...bandCounts, ...data.band_counts};
                for (const band in data.band_counts) {
                    updateBandCount(band, data.band_counts[band]);
                }
                updateActiveBands(bandCounts);
            }

            rerenderAllMarkers();
        }
    } catch (e) {
        console.error('加载历史失败:', e);
    }
}

// 有效性检查
function isValidSpot(spot) {
    return spot && spot.callsign && spot.lat !== 0 && spot.lon !== 0;
}

// 添加 Spot 到历史
function addSpotToHistory(spotData, silent) {
    const now = Date.now();
    const serverTs = spotData._server_ts ? spotData._server_ts * 1000 : now;
    const receivedAt = spotData.receivedAt || serverTs;

    const cutoff = timeFilter > 0 ? now - timeFilter * 60000 : 0;
    const visible = receivedAt >= cutoff;

    // 波段筛选
    if (activeBandFilter && spotData.band !== activeBandFilter) {
        visible = false;
    }

    let marker = null;
    if (visible) {
        marker = createSpotMarker(spotData);
    }

    spotHistory.push({
        spot: spotData,
        marker: marker,
        receivedAt: receivedAt
    });

    while (spotHistory.length > MAX_HISTORY) {
        const entry = spotHistory.shift();
        if (entry.marker) {
            map.removeLayer(entry.marker);
        }
    }

    updateVisibleCount();
}

// 创建标记
function createSpotMarker(spotData) {
    if (!map) return null;

    const mode = spotData.mode || 'UNKNOWN';
    const color = MODE_COLORS[mode] || MODE_COLORS['UNKNOWN'];
    const precision = spotData.precision || 'dxcc';

    // 根据精度调整标记大小：grid/grid_db 显示小一点（精确），其他显示大一点
    const size = (precision === 'grid' || precision === 'grid_db') ? 10 : 14;
    const pulseSize = size + 12;

    try {
        const icon = L.divIcon({
            className: 'spot-marker-wrapper',
            html: '<div class="spot-pin" style="--pin-color:' + color + ';--pin-size:' + size + 'px;">' +
                  '<div class="spot-pulse" style="width:' + pulseSize + 'px;height:' + pulseSize + 'px;"></div>' +
                  '<div class="spot-dot" style="width:' + size + 'px;height:' + size + 'px;"></div>' +
                  '</div>',
            iconSize: [pulseSize, pulseSize],
            iconAnchor: [pulseSize / 2, pulseSize / 2]
        });

        const marker = L.marker([spotData.lat, spotData.lon], {icon: icon}).addTo(map);

        const gridInfo = spotData.grid ? '<br/>📍 Grid: ' + spotData.grid : '';
        console.log(`[DEBUG] ${spotData.callsign}: grid=${spotData.grid}, precision=${spotData.precision}, freq=${spotData.freq}`);
        const cqItuInfo = (spotData.cq || spotData.itu) ? 
            '<br/>🗺️ CQ:' + (spotData.cq || '?') + ' ITU:' + (spotData.itu || '?') : '';
        const lotwBadge = spotData.lotw_verified ? 
            '<span style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:2px 6px;border-radius:3px;font-size:10px;margin-left:6px;">✓ LoTW</span>' : '';
        const sourceInfo = spotData.source === 'pskreporter' ? '<br/>📡 PSKReporter' : '<br/>📡 Cluster';
        const dxccLabel = spotData.dxcc ? '<br/>🏳️ ' + spotData.dxcc : '';
        const timeStr = spotData.time ? '<br/>🕐 ' + spotData.time : '';
        const spotterInfo = spotData.spotter ? '<br/>📢 报告：' + spotData.spotter : '';
        const commentInfo = spotData.comment ? '<br/>💬 ' + spotData.comment : '';
        const precisionLabel = (spotData.precision === 'grid' || spotData.precision === 'grid_db') ? ' (精确)' : (spotData.precision === 'china_province' ? ' (省份)' : (spotData.precision === 'cty' ? ' (CTY)' : (spotData.precision === 'dxcc' ? ' (国家)' : '')));

        marker.bindTooltip(
            '<div style="min-width:180px;">' +
            '<div style="font-weight:bold;font-size:14px;margin-bottom:6px;color:' + color + '">' + spotData.callsign + '</div>' +
            '<div style="font-size:12px;color:#ccc">' +
            '📻 ' + (typeof spotData.freq === 'number' ? spotData.freq.toFixed(3) : spotData.freq) + ' MHz' +
            '<br/>📡 ' + spotData.band + ' · ' + spotData.mode + precisionLabel +
            dxccLabel +
            gridInfo +
            timeStr +
            sourceInfo +
            spotterInfo +
            commentInfo +
            '</div></div>',
            {
                className: 'spot-tooltip',
                direction: 'top',
                offset: [0, -12],
                opacity: 0.95
            }
        );

        return marker;
    } catch (e) {
        console.error('标记创建失败:', e);
        return null;
    }
}

// 清理过期标记
function cleanupExpiredMarkers() {
    if (timeFilter <= 0) return;

    const now = Date.now();
    const cutoff = now - timeFilter * 60000;

    spotHistory.forEach(entry => {
        if (entry.receivedAt < cutoff && entry.marker) {
            map.removeLayer(entry.marker);
            entry.marker = null;
        }
    });

    updateVisibleCount();
}

// 设置时间筛选
function setTimeFilter(minutes) {
    timeFilter = minutes;
    document.querySelectorAll('.time-btn, .time-btn2').forEach(btn => {
        const onclick = btn.getAttribute('onclick') || '';
        const match = onclick.match(/setTimeFilter\((\d+)\)/);
        btn.classList.toggle('active', match && parseInt(match[1]) === minutes);
    });
    rerenderAllMarkers();
}

// 设置模式筛选
function setModeFilter(mode) {
    modeFilter = mode;
    const selectEl = document.getElementById('mode-filter-select');
    if (selectEl) {
        selectEl.value = mode;
    }
    // 同步所有下拉框
    document.querySelectorAll('#mode-filter-select').forEach(el => {
        el.value = mode;
    });
    rerenderAllMarkers();
}

// 波段筛选
function toggleBandFilter(band) {
    const bandEl = document.getElementById('band-' + band);

    if (activeBandFilter === band) {
        // 取消筛选
        activeBandFilter = null;
        bandEl.classList.remove('filter-active');
    } else {
        // 切换到新波段
        if (activeBandFilter) {
            document.getElementById('band-' + activeBandFilter).classList.remove('filter-active');
        }
        activeBandFilter = band;
        bandEl.classList.add('filter-active');
    }

    rerenderAllMarkers();
}

// 重新渲染
function rerenderAllMarkers() {
    const now = Date.now();
    const cutoff = timeFilter > 0 ? now - timeFilter * 60000 : 0;

    spotHistory.forEach(entry => {
        const timeVisible = entry.receivedAt >= cutoff;
        const bandVisible = !activeBandFilter || entry.spot.band === activeBandFilter;
        const modeVisible = !modeFilter || modeFilter === 'ALL' || entry.spot.mode === modeFilter;
        const visible = timeVisible && bandVisible && modeVisible;

        if (visible && !entry.marker) {
            entry.marker = createSpotMarker(entry.spot);
        } else if (!visible && entry.marker) {
            map.removeLayer(entry.marker);
            entry.marker = null;
        }
    });

    updateVisibleCount();
}

// 更新可见计数
function updateVisibleCount() {
    const visibleCount = spotHistory.filter(e => e.marker !== null).length;
    const countEl = document.getElementById('visible-count');
    if (countEl) countEl.textContent = visibleCount;
}

// 渲染波段条
function renderBandBar() {
    const container = document.getElementById('band-bar');
    if (!container) return;

    container.innerHTML = '';
    BANDS.forEach(band => {
        const bandEl = document.createElement('div');
        bandEl.className = 'band-item';
        bandEl.id = 'band-' + band;
        bandEl.dataset.band = band;
        bandEl.innerHTML =
            '<span class="band-count" id="count-' + band + '">0</span>' +
            '<span class="band-name">' + band + '</span>';
        bandEl.addEventListener('click', () => toggleBandFilter(band));
        container.appendChild(bandEl);
    });
}

// 更新波段计数
function updateBandCount(band, count) {
    const countEl = document.getElementById('count-' + band);
    if (!countEl) return;
    countEl.textContent = count;
    const bandEl = document.getElementById('band-' + band);
    if (count > 0) {
        bandEl.classList.remove('inactive');
        bandEl.classList.add('active');
    } else {
        bandEl.classList.remove('active');
        bandEl.classList.add('inactive');
    }
}

// 更新活跃波段
function updateActiveBands(counts) {
    const active = Object.keys(counts).filter(b => counts[b] > 0);
    const el = document.getElementById('active-bands');
    if (el) el.textContent = active.length > 0 ? active.join(', ') : '-';
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const dot = document.getElementById('conn-dot');
    const text = document.getElementById('conn-text');
    if (!dot || !text) return;

    if (connected) {
        dot.className = 'dot dot-on';
        text.textContent = '已连接';
        text.style.color = '#4CAF50';
    } else {
        dot.className = 'dot dot-off';
        text.textContent = '已断开';
        text.style.color = '#f44336';
    }
}

// =========== 传播预测面板 ===========
async function loadPropagation() {
    try {
        const resp = await fetch('/api/propagation');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        renderPropagation(data.propagation);
    } catch(e) {
        console.error('加载传播数据失败:', e);
    }
}

function renderPropagation(bands) {
    const container = document.getElementById('propagation-container');
    if (!container) return;
    
    let html = '';
    for (const b of bands) {
        const color = b.score >= 70 ? '#4CAF50' : (b.score >= 50 ? '#FF9800' : '#f44336');
        const icon = b.score >= 70 ? '🟢' : (b.score >= 50 ? '🟡' : '🔴');
        html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:11px;">
            <span>${icon} <b>${b.band}</b></span>
            <span style="color:${color};font-weight:bold;">${b.quality}</span>
        </div>`;
    }
    container.innerHTML = html;
}

// ========== 波段趋势分析 ==========
async function loadTrends() {
    try {
        const resp = await fetch('/api/trends');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        renderTrends(data.trends);
    } catch(e) {
        console.error('加载趋势数据失败:', e);
    }
}

function renderTrends(trends) {
    const container = document.getElementById('trends-container');
    if (!container) return;
    
    if (!trends || !trends.bands || Object.keys(trends.bands).length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:8px;">暂无数据</div>';
        return;
    }
    
    let html = '';
    
    // 整体趋势
    const overallColor = trends.overall === '上升' ? '#4CAF50' : (trends.overall === '下降' ? '#f44336' : '#FF9800');
    html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:6px;">
        <span style="color:#aaa;">整体趋势</span>
        <span style="color:${overallColor};font-weight:bold;">${trends.overall}</span>
    </div>`;
    
    // 各波段趋势
    const bandOrder = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m'];
    for (const band of bandOrder) {
        const bandData = trends.bands[band];
        if (!bandData) continue;
        
        const trendColor = bandData.trend_label === '上升' ? '#4CAF50' : (bandData.trend_label === '下降' ? '#f44336' : '#FF9800');
        const trendIcon = bandData.trend_label === '上升' ? '↗' : (bandData.trend_label === '下降' ? '↘' : '→');
        
        html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:11px;">
            <span><b>${band}</b> <span style="color:#666;font-size:10px;">${bandData.count}个</span></span>
            <span style="color:${trendColor};font-weight:bold;">${trendIcon} ${bandData.trend_label}</span>
        </div>`;
        
        // 热门DXCC (如果有)
        if (bandData.top_dxcc && bandData.top_dxcc.length > 0) {
            const top3 = bandData.top_dxcc.slice(0, 3);
            html += `<div style="font-size:10px;color:#666;padding-left:8px;margin-bottom:4px;">
                🔥 ${top3.map(d => `${d.call}(${d.count})`).join(', ')}
            </div>`;
        }
    }
    
    // 最近速率
    if (trends.recent_rate) {
        html += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.1);font-size:10px;color:#888;text-align:center;">
            最近5分钟平均: ${trends.recent_rate} Spot/分钟
        </div>`;
    }
    
    container.innerHTML = html;
}

// ========== VOACAP 传播预测 ==========
async function loadVOACAP() {
    try {
        const resp = await fetch('/api/voacap/best-bands');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        renderVOACAP(data);
    } catch(e) {
        console.error('加载VOACAP数据失败:', e);
    }
}

function renderVOACAP(data) {
    const container = document.getElementById('voacap-container');
    if (!container) return;
    
    let html = '';
    
    // 太阳数据
    const sfi = data.solar?.sfi || 0;
    const k = data.solar?.k_index || 0;
    const sfiColor = sfi > 120 ? '#4CAF50' : (sfi > 80 ? '#FF9800' : '#f44336');
    html += `<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:10px;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:6px;">
        <span style="color:#aaa;">SFI: <span style="color:${sfiColor};font-weight:bold;">${sfi}</span></span>
        <span style="color:#aaa;">K: <span style="color:${k<=2?'#4CAF50':'#f44336'};font-weight:bold;">${k}</span></span>
    </div>`;
    
    // 推荐波段
    if (data.recommended_bands && data.recommended_bands.length > 0) {
        html += `<div style="font-size:10px;color:#888;margin-bottom:4px;">推荐波段:</div>`;
        for (const b of data.recommended_bands) {
            const color = b.total_score > 200 ? '#4CAF50' : (b.total_score > 100 ? '#FF9800' : '#f44336');
            html += `<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:11px;">
                <span style="color:#fff;">${b.band}</span>
                <span style="color:${color};font-weight:bold;">${b.total_score}</span>
            </div>`;
        }
    }
    
    // 各目标传播条件
    if (data.targets && data.targets.length > 0) {
        html += `<div style="font-size:10px;color:#888;margin-top:8px;margin-bottom:4px;">传播条件:</div>`;
        for (const t of data.targets) {
            const dist = t.distance_km > 1000 ? (t.distance_km/1000).toFixed(1)+'k' : t.distance_km;
            const bands = t.best_bands.map(b => b.band).join(', ');
            const grayline = t.grayline ? ' 🌙' : '';
            html += `<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:10px;">
                <span style="color:#aaa;">${t.target} <span style="color:#666;">${dist}km${grayline}</span></span>
                <span style="color:#e94560;">${bands || '-'}</span>
            </div>`;
        }
    }
    
    container.innerHTML = html;
}

// ========== 波段开放预测 ==========
async function loadBandOpening() {
    try {
        const resp = await fetch('/api/band-opening');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        renderBandOpening(data.forecast);
    } catch(e) {
        console.error('加载波段开放预测失败:', e);
    }
}

function renderBandOpening(forecast) {
    const container = document.getElementById('bandopening-container');
    if (!container) return;
    
    const keyBands = ['40m', '30m', '20m', '17m', '15m', '10m', '6m'];
    let html = '<table style="width:100%;font-size:10px;border-collapse:collapse;">';
    
    // 表头
    html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.2);">';
    html += '<th style="color:#888;padding:2px;">时间</th>';
    for (const band of keyBands) {
        html += `<th style="color:#888;padding:2px;">${band}</th>`;
    }
    html += '</tr>';
    
    // 每小时一行
    for (const h of forecast) {
        html += '<tr>';
        html += `<td style="color:#aaa;padding:1px 2px;">${h.label}</td>`;
        for (const band of keyBands) {
            const b = h.bands[band];
            if (!b) {
                html += '<td style="padding:1px 2px;">-</td>';
                continue;
            }
            const color = b.score >= 80 ? '#4CAF50' : (b.score >= 60 ? '#FF9800' : (b.score >= 40 ? '#e94560' : '#666'));
            const icon = b.open ? '●' : '○';
            html += `<td style="color:${color};padding:1px 2px;text-align:center;">${icon}</td>`;
        }
        html += '</tr>';
    }
    
    html += '</table>';
    html += '<div style="font-size:9px;color:#666;margin-top:4px;text-align:center;">● 开放 ○ 关闭 | 绿≥80 黄≥60 红≥40</div>';
    
    container.innerHTML = html;
}

