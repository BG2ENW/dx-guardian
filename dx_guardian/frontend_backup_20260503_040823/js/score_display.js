// 机会评分展示 - 推荐列表 + 地图标记着色

let opportunityList = [];

// =========== 推荐机会面板 ===========

async function loadOpportunities() {
    try {
        const resp = await fetch('/api/score/top?limit=15&min_score=40');
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.success) {
            opportunityList = data.top || [];
            renderOpportunities();
        }
    } catch (e) {
        console.error('加载推荐机会失败:', e);
    }
}

function renderOpportunities() {
    const container = document.getElementById('opportunities-container');
    const countEl = document.getElementById('opportunity-count');
    if (!container) return;

    if (countEl) {
        countEl.textContent = opportunityList.length;
    }

    if (opportunityList.length === 0) {
        container.innerHTML = '<div style="font-size:12px;color:#666;text-align:center;padding:12px;">暂无推荐机会，等数据进来...</div>';
        return;
    }

    container.innerHTML = opportunityList.map((item, idx) => {
        const color = getScoreColor(item.score);
        const rank = idx + 1;
        return `<div class="opportunity-item" style="border-left:3px solid ${color};padding:8px;background:rgba(255,255,255,0.04);margin-bottom:6px;border-radius:4px;cursor:pointer;font-size:12px;" onclick="flyToSpot(${item.lat},${item.lon},'${item.callsign}')" onmouseover="highlightMarker('${item.callsign}')" onmouseout="unhighlightMarker('${item.callsign}')">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:9px;color:#666;margin-right:4px;">#${rank}</span>
                    <span style="font-weight:bold;color:#fff;font-size:13px;">${item.callsign}</span>
                    <span style="font-size:10px;color:#aaa;margin-left:4px;">${item.dxcc || ''}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:16px;font-weight:bold;color:${color};">${item.score}</span>
                    <span style="font-size:9px;color:#aaa;">分</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px;color:#888;">
                <span>${item.band || '?'} · ${item.mode || '?'} · ${item.freq ? item.freq.toFixed(3) : '?'} MHz</span>
                <span style="font-size:10px;color:${color};">${item.recommendation || ''}</span>
            </div>
        </div>`;
    }).join('');
}

// =========== 新高分 Spot WebSocket 推送 ===========
socket.on('score:opportunity', (data) => {
    const spot = data.spot || {};
    const score = data.score || {};
    
    // 更新推荐列表
    const existing = opportunityList.findIndex(x => x.callsign === spot.callsign);
    const entry = {
        callsign: spot.callsign,
        dxcc: spot.dxcc || '',
        band: spot.band || '',
        mode: spot.mode || '',
        freq: spot.freq || 0,
        lat: spot.lat || 0,
        lon: spot.lon || 0,
        grid: spot.grid || '',
        score: score.total || 0,
        recommendation: score.recommendation || '',
        factors: score.factors || {},
        time: spot.time || '',
    };
    
    if (existing >= 0) {
        opportunityList[existing] = entry;
    } else {
        opportunityList.unshift(entry);
    }
    
    // 排序
    opportunityList.sort((a, b) => b.score - a.score);
    
    // 限制数量
    if (opportunityList.length > 20) {
        opportunityList = opportunityList.slice(0, 20);
    }
    
    renderOpportunities();
});

// =========== 新 Spot 到达时着色地图标记 ===========
socket.on('new_spot', (spot) => {
    const score = spot.score || spot.score_total;
    if (score && spot.lat && spot.lon) {
        updateSpotMarkerColor(spot, score);
    }
});

// 地图标记按评分着色
const spotMarkers = window._spotMarkers || {};

function updateSpotMarkerColor(spot, score) {
    const color = getScoreColor(score);
    const callsign = spot.callsign;
    
    // 找到地图上已有的标记
    if (spotMarkers[callsign] && spotMarkers[callsign].marker) {
        const marker = spotMarkers[callsign].marker;
        const icon = L.divIcon({
            className: 'spot-marker-wrapper',
            html: `<div class="spot-pin" style="--pin-color:${color};--pin-size:12px;">
                <div class="spot-pulse" style="width:24px;height:24px;background:${color};"></div>
                <div class="spot-dot" style="width:12px;height:12px;background:${color};border:2px solid rgba(255,255,255,0.9);box-shadow:0 0 8px ${color};"></div>
            </div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
        marker.setIcon(icon);
        
        // 高分标记闪烁提示
        if (score >= 70) {
            const el = marker.getElement?.();
            if (el) {
                el.style.animation = 'none';
                setTimeout(() => { el.style.animation = 'score-flash 1s ease-out'; }, 10);
            }
        }
    }
}

function highlightMarker(callsign) {
    if (spotMarkers[callsign] && spotMarkers[callsign].marker) {
        const m = spotMarkers[callsign].marker;
        m.openPopup();
    }
}

function unhighlightMarker(callsign) {
    if (spotMarkers[callsign] && spotMarkers[callsign].marker) {
        const m = spotMarkers[callsign].marker;
        m.closePopup();
    }
}

function flyToSpot(lat, lon, callsign) {
    if (map && lat && lon) {
        map.flyTo([lat, lon], 5, { duration: 1 });
    }
}

// =========== 工具函数 ===========
function getScoreColor(score) {
    if (score >= 70) return '#4CAF50';
    if (score >= 50) return '#FF9800';
    if (score >= 30) return '#FF5722';
    return '#f44336';
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadOpportunities();
    
    // 每 30 秒刷新一次
    setInterval(() => {
        if (opportunityList.length > 0) {
            loadOpportunities();
        }
    }, 30000);
});
