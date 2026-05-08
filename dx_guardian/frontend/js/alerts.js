/**
 * DX Guardian - 预警系统 V2
 * 功能：优先级分级、声音提醒、去重、静默、确认、统计
 */

let alertHistory = [];
const ALERT_HISTORY_MAX = 200;
let neededDXCC = new Set();
let alertSilencedList = [];
let alertFilter = { priority: null, unreadOnly: false };
let audioCtx = null;

// =========== 声音提醒 ===========
function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

function playAlertSound(priority) {
    try {
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        // 不优先级不同音调
        const freqMap = {
            'urgent': 880,     // 高音 - 紧急
            'important': 660,  // 中音 - 重要
            'normal': 440      // 低音 - 普通
        };
        
        osc.frequency.value = freqMap[priority] || 440;
        osc.type = priority === 'urgent' ? 'square' : 'sine';
        
        // 紧急的播放两声
        if (priority === 'urgent') {
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.3, ctx.currentTime + 0.2);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.35);
        } else {
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.25);
        }
    } catch (e) {
        console.warn('播放预警声音失败:', e);
    }
}

// =========== 数据加载 ===========
async function loadAlerts() {
    try {
        let url = '/api/user/alerts?limit=' + ALERT_HISTORY_MAX;
        if (alertFilter.priority) url += '&priority=' + alertFilter.priority;
        if (alertFilter.unreadOnly) url += '&unread_only=true';
        
        const resp = await fetch(url);
        if (resp.ok) {
            const data = await resp.json();
            alertHistory = data.alerts || [];
            renderAlerts();
        }
    } catch (e) {
        console.error('加载预警列表失败:', e);
    }
}

async function loadSilencedList() {
    try {
        const resp = await fetch('/api/user/alerts/silence');
        if (resp.ok) {
            const data = await resp.json();
            alertSilencedList = data.silenced || [];
        }
    } catch (e) {
        console.error('加载静默列表失败:', e);
    }
}

async function loadAlertStats() {
    try {
        const resp = await fetch('/api/user/alerts/stats');
        if (resp.ok) {
            const data = await resp.json();
            renderAlertStats(data.stats || {});
        }
    } catch (e) {
        console.error('加载预警统计失败:', e);
    }
}

// =========== 预警渲染 ===========
function renderAlerts() {
    const container = document.getElementById('alerts-container');
    const countEl = document.getElementById('alert-count');
    if (!container) return;

    // 更新计数（所有未读，不仅是当前筛选的）
    if (countEl) {
        const unreadCount = alertHistory.filter(a => !a.is_read).length;
        countEl.textContent = unreadCount;
        countEl.style.display = unreadCount > 0 ? 'inline' : 'none';
    }

    if (alertHistory.length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:16px;">🔔 暂无预警</div>';
        return;
    }

    container.innerHTML = alertHistory.map(alert => {
        const spot = alert.spot || {};
        const priority = alert.priority || 'normal';
        const priorityColors = {
            'urgent': '#f44336',
            'important': '#FF9800',
            'normal': '#4CAF50'
        };
        const borderColor = priorityColors[priority] || '#666';
        const icon = getAlertIcon(alert.type);
        const timeStr = formatAlertTime(alert.created_at);
        const readStyle = alert.is_read ? 'opacity:0.5;' : '';
        const dxccCn = spot.dxcc_cn || '';
        const snr = spot.snr ? `SNR:${spot.snr}` : '';
        const srcIcon = spot.source === 'pskreporter' ? '📡' : '📻';
        const priorityText = { urgent: '紧急', important: '重要', normal: '普通' }[priority] || '普通';
        
        return `<div class="alert-item priority-${priority}" ${readStyle} data-id="${alert.id}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                        <span class="alert-priority-badge ${priority}">${priorityText}</span>
                        <span>${icon}</span>
                        <span style="font-weight:bold;color:var(--text-primary);font-size:13px;">${spot.callsign || '?'}</span>
                        <span style="color:var(--text-secondary);font-size:11px;">${spot.band || ''} ${spot.mode || ''}</span>
                        <span style="color:var(--text-tertiary);font-size:10px;">${srcIcon}</span>
                    </div>
                    <div style="font-size:12px;color:var(--text-primary);margin-bottom:4px;">${alert.message}</div>
                    ${dxccCn ? `<div style="font-size:10px;color:var(--text-secondary);margin-bottom:2px;">${dxccCn}</div>` : ''}
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-size:11px;color:var(--text-tertiary);">${timeStr} ${snr}</div>
                        <div style="display:flex;gap:4px;">
                            ${!alert.is_read ? `<button onclick="markAlertRead('${alert.id}')" style="background:rgba(76,175,80,0.2);border:1px solid #4CAF50;color:#4CAF50;border-radius:3px;padding:1px 5px;font-size:10px;cursor:pointer;">已读</button>` : ''}
                            <button onclick="silenceAlert('${spot.callsign || ''}')" style="background:rgba(255,152,0,0.2);border:1px solid #FF9800;color:#FF9800;border-radius:3px;padding:1px 5px;font-size:10px;cursor:pointer;">静默</button>
                            <button onclick="deleteAlert('${alert.id}')" style="background:rgba(244,67,54,0.2);border:1px solid #f44336;color:#f44336;border-radius:3px;padding:1px 5px;font-size:10px;cursor:pointer;">✕</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function renderAlertStats(stats) {
    const statsEl = document.getElementById('alert-stats');
    if (!statsEl) return;
    
    const bp = stats.by_priority || {};
    const bt = stats.by_type || {};
    
    statsEl.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:8px;">
            <div class="solar-item"><div style="font-size:10px;color:#f44336;">紧急</div><div style="font-size:16px;font-weight:bold;color:#fff;">${bp.urgent || 0}</div></div>
            <div class="solar-item"><div style="font-size:10px;color:#FF9800;">重要</div><div style="font-size:16px;font-weight:bold;color:#fff;">${bp.important || 0}</div></div>
            <div class="solar-item"><div style="font-size:10px;color:#4CAF50;">普通</div><div style="font-size:16px;font-weight:bold;color:#fff;">${bp.normal || 0}</div></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#aaa;margin-bottom:4px;">
            <span>今日预警: <b style="color:#fff;">${stats.today || 0}</b></span>
            <span>未读: <b style="color:#e94560;">${stats.unread || 0}</b></span>
            <span>总计: <b style="color:#fff;">${stats.total || 0}</b></span>
        </div>
        ${stats.silenced_count > 0 ? `<div style="font-size:11px;color:#666;margin-top:4px;">🔇 已静默 ${stats.silenced_count} 个呼号</div>` : ''}
    `;
}

function getAlertIcon(type) {
    const icons = {
        'callsign': '📞',
        'prefix': '🔤',
        'dxcc': '🏳️',
        'band': '📻',
        'mode': '📡'
    };
    return icons[type] || '🔔';
}

function formatAlertTime(isoStr) {
    try {
        const date = new Date(isoStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}小时前`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}天前`;
    } catch {
        return '?';
    }
}

// =========== 预警操作 ===========
async function markAlertRead(alertId) {
    try {
        await fetch('/api/user/alerts/' + alertId + '/read', { method: 'PUT' });
        loadAlerts();
        loadAlertStats();
    } catch (e) {
        console.error('标记已读失败:', e);
    }
}

async function markAllAlertsRead() {
    try {
        await fetch('/api/user/alerts/read-all', { method: 'PUT' });
        loadAlerts();
        loadAlertStats();
    } catch (e) {
        console.error('全部标记已读失败:', e);
    }
}

async function deleteAlert(alertId) {
    try {
        await fetch('/api/user/alerts/' + alertId, { method: 'DELETE' });
        loadAlerts();
        loadAlertStats();
    } catch (e) {
        console.error('删除预警失败:', e);
    }
}

async function clearAllAlerts() {
    if (!confirm('确定清空所有预警？')) return;
    try {
        await fetch('/api/user/alerts/clear', { method: 'DELETE' });
        loadAlerts();
        loadAlertStats();
    } catch (e) {
        console.error('清空预警失败:', e);
    }
}

async function silenceAlert(callsign) {
    if (!callsign) return;
    try {
        await fetch('/api/user/alerts/silence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ callsign: callsign })
        });
        loadSilencedList();
        loadAlertStats();
    } catch (e) {
        console.error('静默失败:', e);
    }
}

async function unsilenceAlert(callsign) {
    try {
        await fetch('/api/user/alerts/silence/' + encodeURIComponent(callsign), { method: 'DELETE' });
        loadSilencedList();
        loadAlertStats();
        renderSilencedList();
    } catch (e) {
        console.error('取消静默失败:', e);
    }
}

function renderSilencedList() {
    const container = document.getElementById('silenced-container');
    if (!container) return;
    
    if (alertSilencedList.length === 0) {
        container.innerHTML = '<div style="font-size:11px;color:#666;text-align:center;padding:8px;">无静默呼号</div>';
        return;
    }
    
    container.innerHTML = alertSilencedList.map(cs => 
        `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;background:rgba(255,255,255,0.04);border-radius:4px;margin-bottom:4px;">
            <span style="font-size:12px;color:#aaa;">🔇 ${cs}</span>
            <button onclick="unsilenceAlert('${cs}')" style="background:rgba(76,175,80,0.2);border:1px solid #4CAF50;color:#4CAF50;border-radius:3px;padding:1px 6px;font-size:10px;cursor:pointer;">恢复</button>
        </div>`
    ).join('');
}

// =========== 筛选 ===========
function setAlertFilter(priority) {
    if (alertFilter.priority === priority) {
        alertFilter.priority = null;
    } else {
        alertFilter.priority = priority;
    }
    // 更新按钮状态
    document.querySelectorAll('.alert-filter-btn').forEach(btn => {
        if (btn.dataset.priority === alertFilter.priority) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    loadAlerts();
}

function toggleUnreadOnly() {
    alertFilter.unreadOnly = !alertFilter.unreadOnly;
    loadAlerts();
}

// =========== 缺失 DXCC 高亮 ===========
function highlightNeededDXCC(dxcc, callsign) {
    const targetEntries = spotHistory.filter(entry => 
        entry.spot.callsign === callsign || 
        entry.spot.dxcc === dxcc ||
        entry.spot.dxcc === dxcc.toUpperCase()
    );
    
    targetEntries.forEach(entry => {
        if (entry.marker) {
            const icon = L.divIcon({
                className: 'spot-marker-wrapper',
                html: '<div class="spot-pin" style="--pin-color:#FFD700;--pin-size:14px;">' +
                      '<div class="spot-pulse" style="width:30px;height:30px;background:#FFD700;animation:spot-pulse-anim 1s ease-out infinite;"></div>' +
                      '<div class="spot-dot" style="width:14px;height:14px;border-radius:50%;background:#FFD700;border:3px solid #fff;box-shadow:0 0 12px #FFD700, 0 0 4px #FFD700;"></div>' +
                      '</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            entry.marker.setIcon(icon);
        }
    });
}

// =========== 浏览器通知 ===========
function showBrowserNotification(alert) {
    if (!('Notification' in window)) return;
    
    const priority = alert.priority || 'normal';
    const prefix = priority === 'urgent' ? '🔴' : priority === 'important' ? '🟡' : '🟢';
    
    if (Notification.permission === 'granted') {
        new Notification(`${prefix} DX Guardian`, {
            body: alert.message,
            icon: '/images/marker-icon.png',
            tag: 'dx-alert-' + (alert.id || Date.now()),
            requireInteraction: priority === 'urgent'
        });
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification(`${prefix} DX Guardian`, {
                    body: alert.message,
                    icon: '/images/marker-icon.png',
                    tag: 'dx-alert-' + (alert.id || Date.now()),
                    requireInteraction: priority === 'urgent'
                });
            }
        });
    }
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// =========== WebSocket 接收 ===========
socket.on('alert:new', (alert) => {
    alertHistory.unshift(alert);
    if (alertHistory.length > ALERT_HISTORY_MAX) {
        alertHistory = alertHistory.slice(0, ALERT_HISTORY_MAX);
    }
    renderAlerts();
    
    // 播放声音
    playAlertSound(alert.priority || 'normal');
    
    // 浏览器通知
    showBrowserNotification(alert);
    
    // 刷新统计
    loadAlertStats();
});

socket.on('dxcc:needed', (data) => {
    if (data.needed && data.dxcc) {
        neededDXCC.add(data.dxcc.toUpperCase());
        highlightNeededDXCC(data.dxcc, data.callsign);
    }
});

// =========== 启动 ===========
document.addEventListener('DOMContentLoaded', () => {
    loadAlerts();
    loadSilencedList().then(() => renderSilencedList());
    loadAlertStats();
    loadLogs();
    loadMissingDXCCScores();
    
    setTimeout(() => {
        requestNotificationPermission();
    }, 5000);
});

// =========== DXCC 统计展示 ===========
let userLogs = [];

async function loadLogs() {
    try {
        const resp = await fetch('/api/user/logs');
        if (resp.ok) {
            const data = await resp.json();
            userLogs = data.logs || [];
            renderLogs();
        }
    } catch (e) {
        console.error('加载日志列表失败:', e);
    }
}

function renderLogs() {
    const container = document.getElementById('logs-container');
    if (!container) return;

    if (userLogs.length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:12px;">暂无日志，点击上方上传</div>';
        return;
    }

    const latestLog = userLogs[0];
    const stats = latestLog.dxcc_stats || {};
    const worked = stats.worked_dxcc_count || 0;
    const total = stats.total_dxcc_entities || 0;
    const topEntities = stats.top_entities || [];
    const bandStats = stats.band_stats || {};

    let html = `
        <div class="alert-item" style="border-left:3px solid #4CAF50;">
            <div style="font-weight:bold;color:#fff;font-size:13px;">${latestLog.filename}</div>
            <div style="font-size:11px;color:#aaa;margin-bottom:4px;">${latestLog.record_count} 条记录 · ${formatAlertTime(latestLog.uploaded_at)}</div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span style="font-size:11px;color:#4CAF50;">DXCC ${worked}/${total}</span>
                <button onclick="deleteLog('${latestLog.id}')" style="background:rgba(244,67,54,0.2);border:none;color:#f44336;padding:2px 6px;border-radius:3px;cursor:pointer;font-size:10px;margin-left:auto;">✕</button>
            </div>
        </div>`;
        
    if (topEntities.length > 0) {
        html += `
        <div style="margin-top:8px;padding:8px;background:rgba(255,255,255,0.04);border-radius:4px;">
            <div style="font-size:11px;color:#fff;margin-bottom:4px;">通联最多</div>
            ${topEntities.slice(0, 5).map(([entity, count]) => 
                `<div style="display:flex;justify-content:space-between;font-size:11px;padding:2px 0;">
                    <span style="color:#ddd;">${entity}</span>
                    <span style="color:#4CAF50;">${count}</span>
                </div>`
            ).join('')}
        </div>`;
    }
    
    container.innerHTML = html;
    initBandChart(bandStats);
}

async function deleteLog(logId) {
    try {
        await fetch('/api/user/logs/' + logId, { method: 'DELETE' });
        loadLogs();
        loadMissingDXCCScores();
    } catch (e) {
        console.error('删除日志失败:', e);
    }
}

// =========== 机会评分 UI ===========
let missingDXCCScores = [];

async function loadMissingDXCCScores() {
    try {
        const resp = await fetch('/api/score/missing');
        if (resp.ok) {
            const data = await resp.json();
            missingDXCCScores = data.scores || [];
            renderMissingDXCCScores();
        }
    } catch (e) {
        console.error('加载缺失DXCC评分失败:', e);
    }
}

function renderMissingDXCCScores() {
    const container = document.getElementById('opps-container');
    if (!container) return;

    if (missingDXCCScores.length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:12px;">暂无缺失DXCC数据</div>';
        return;
    }

    container.innerHTML = missingDXCCScores.map(item => {
        const score = item.score || {};
        const factors = score.factors || {};
        const rec = score.recommendation || '';
        const spot = item.spot || {};
        
        return `<div class="alert-item" style="border-left:3px solid ${getScoreColor(score.total || 0)};">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                        <span style="font-weight:bold;color:#fff;font-size:13px;">${item.dxcc || '?'}</span>
                        <span style="font-size:11px;color:#aaa;">${spot.callsign || ''}</span>
                    </div>
                    <div style="font-size:11px;color:#ddd;margin-bottom:4px;">${spot.band || ''} · ${spot.mode || ''}</div>
                    <div style="display:flex;gap:4px;flex-wrap:wrap;">
                        ${renderScoreFactors(factors)}
                    </div>
                </div>
                <div style="text-align:right;min-width:60px;">
                    <div style="font-size:20px;font-weight:bold;color:${getScoreColor(score.total || 0)};">${score.total || 0}</div>
                    <div style="font-size:10px;color:#aaa;">${rec}</div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function renderScoreFactors(factors) {
    const labels = {
        'band_activity': '波段', 'solar': '太阳', 'time_window': '时间',
        'distance': '距离', 'spot_heat': '热度', 'mode_match': '模式'
    };
    
    return Object.entries(factors).map(([key, val]) => {
        const label = labels[key] || key;
        const pct = Math.round((val.score / val.max) * 100);
        return `<div style="font-size:9px;color:#ccc;padding:2px 4px;background:rgba(255,255,255,0.06);border-radius:3px;" title="${val.detail}">
            ${label} ${pct}%
        </div>`;
    }).join('');
}

function getScoreColor(score) {
    if (score >= 70) return '#4CAF50';
    if (score >= 50) return '#FF9800';
    if (score >= 30) return '#FF5722';
    return '#f44336';
}

socket.on('spot:new', () => {
    if (missingDXCCScores.length > 0) {
        loadMissingDXCCScores();
    }
});

// =========== 波段图表 ===========
let bandChart = null;

function initBandChart(bandStats) {
    const canvas = document.getElementById('band-chart');
    if (!canvas) return;

    const bandNames = Object.keys(bandStats);
    const bandCounts = bandNames.map(b => bandStats[b].count);

    if (bandNames.length === 0) return;

    try {
        if (bandChart instanceof Chart) bandChart.destroy();
    } catch (e) {}

    try {
        bandChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: bandNames,
                datasets: [{
                    data: bandCounts,
                    backgroundColor: [
                        '#e94560', '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
                        '#00BCD4', '#8BC34A', '#FFC107', '#FF5722', '#607D8B'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#aaa', font: { size: 10 }, boxWidth: 10, padding: 8 }
                    }
                }
            }
        });
    } catch (e) {
        console.error('创建图表失败:', e);
    }
}