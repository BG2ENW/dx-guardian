// 波段分布图表实例
let bandChart = null;

// 模拟日志数据
const mockLogs = [
    {callsign: 'JA1AAA', band: '20m', mode: 'FT8', date: '2026-05-01'},
    {callsign: 'VK2BBB', band: '15m', mode: 'SSB', date: '2026-05-01'},
    {callsign: 'W1AW', band: '40m', mode: 'CW', date: '2026-04-30'},
    {callsign: 'G3XXX', band: '30m', mode: 'FT8', date: '2026-04-30'},
    {callsign: 'DL4YYY', band: '17m', mode: 'PSK31', date: '2026-04-29'}
];

// 模拟波段分布
const mockBandDistribution = {
    '160m': 2, '80m': 8, '40m': 25, '30m': 15, '20m': 45,
    '17m': 12, '15m': 30, '12m': 5, '10m': 18, '6m': 3
};

// 渲染日志列表
function renderLogs(logs) {
    const container = document.getElementById('logs-container');
    if (!container) return;
    
    let html = '';
    for (const log of logs) {
        html += `<div class="log-item">
            <div class="log-call">${log.callsign || 'N/A'}</div>
            <div class="log-band">${log.band || ''}</div>
            <div class="log-mode">${log.mode || ''}</div>
            <div class="log-date">${log.date || ''}</div>
        </div>`;
    }
    container.innerHTML = html || '<div style="font-size:10px;color:var(--text-muted);text-align:center;padding:8px;">无日志</div>';
}

// 加载波段分布图表
function loadBandChart(data) {
    const ctx = document.getElementById('band-chart');
    if (!ctx || !window.Chart) return;
    
    const bandOrder = ['160m','80m','40m','30m','20m','17m','15m','12m','10m','6m'];
    const bandData = bandOrder.map(b => data[b] || 0);
    const bandColors = {
        '160m': '#ef4444', '80m': '#f97316', '40m': '#f59e0b', '30m': '#84cc16',
        '20m': '#10b981', '17m': '#14b8a6', '15m': '#06b6d4', '12m': '#3b82f6',
        '10m': '#8b5cf6', '6m': '#a855f7'
    };
    const bgColors = bandOrder.map(b => bandColors[b] || '#999');
    
    if (bandChart) bandChart.destroy();
    
    bandChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bandOrder,
            datasets: [{
                label: 'QSO',
                data: bandData,
                backgroundColor: bgColors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#9ca3af', font: { size: 9 } },
                    grid: { color: 'rgba(148,163,184,0.2)' }
                },
                x: {
                    ticks: { color: '#9ca3af', font: { size: 9 } },
                    grid: { display: false }
                }
            }
        }
    });
}

// 导出函数供 app.js 调用
window.loadBandChart = loadBandChart;
window.renderLogs = renderLogs;

// 加载日志列表
async function loadLogs() {
    try {
        const resp = await fetch('/api/logs');
        if (resp.ok) {
            const data = await resp.json();
            if (data.success) {
                renderLogs(data.logs || mockLogs);
                loadBandChart(data.band_distribution || mockBandDistribution);
                return;
            }
        }
    } catch (e) {
        // 使用模拟数据
    }
    renderLogs(mockLogs);
    loadBandChart(mockBandDistribution);
}

function renderMissingDXCC(scores) {
    const container = document.getElementById('missing-dxcc-container');
    if (!container) return;
    
    if (scores.length === 0) {
        container.innerHTML = '<div style="font-size:10px;color:var(--text-muted);text-align:center;padding:8px;">无需补充 DXCC</div>';
        return;
    }
    
    const sorted = scores.sort((a, b) => b.score - a.score).slice(0, 20);
    
    let html = '';
    for (const item of sorted) {
        html += `<div class="score-item">
            <div>
                <div style="font-weight:bold;color:var(--text-primary);font-size:10px;">${item.dxcc || item.entity}</div>
                <div style="font-size:8px;color:var(--text-muted);">${item.count || 0} 次</div>
            </div>
            <div class="opp-score" style="background:${item.score >= 80 ? 'var(--gradient-success)' : (item.score >= 50 ? 'var(--gradient-warning)' : 'var(--gradient-danger)')}">${item.score}</div>
        </div>`;
    }
    container.innerHTML = html;
}

// 加载缺失 DXCC 评分
async function loadMissingDXCC() {
    try {
        const resp = await fetch('/api/score/missing');
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.scores) {
                renderMissingDXCC(data.scores);
                return;
            }
        }
    } catch (e) {
        // 使用模拟数据
    }
    renderMissingDXCC([
        {dxcc: 'Antarctica', entity: 'Antarctica', count: 0, score: 100},
        {dxcc: 'North Korea', entity: 'North Korea', count: 0, score: 95},
        {dxcc: 'Yemen', entity: 'Yemen', count: 1, score: 88},
        {dxcc: 'Syria', entity: 'Syria', count: 2, score: 82},
        {dxcc: 'Cuba', entity: 'Cuba', count: 3, score: 75}
    ]);
}

window.loadMissingDXCC = loadMissingDXCC;

// 拖拽上传
function initDragDrop() {
    const uploadArea = document.getElementById('upload-area');
    if (!uploadArea) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('dragover');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('dragover');
        });
    });
    
    uploadArea.addEventListener('drop', handleDrop);
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

async function handleFiles(files) {
    if (files.length === 0) return;
    
    const statusEl = document.getElementById('upload-status');
    const file = files[0];
    
    statusEl.textContent = `正在上传: ${file.name}...`;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const resp = await fetch('/api/logs/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await resp.json();
        if (result.success) {
            statusEl.textContent = `✅ 上传成功: ${result.qso_count} 条 QSO`;
            loadLogs();
            loadBandChart(result.band_distribution || {});
        } else {
            statusEl.textContent = `❌ 上传失败: ${result.error}`;
        }
    } catch (e) {
        statusEl.textContent = `❌ 上传失败: ${e.message}`;
    }
}
