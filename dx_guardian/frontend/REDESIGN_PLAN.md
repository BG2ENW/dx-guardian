# DX Guardian 前端重建设计方案

## 🎨 视觉设计

### 配色方案（鲜艳深色主题）

```css
:root {
  /* 背景 */
  --bg-primary: #0a0e1a;        /* 主背景 - 深蓝黑 */
  --bg-secondary: #111827;      /* 次级背景 */
  --bg-card: #1f2937;           /* 卡片背景 */
  --bg-card-hover: #374151;     /* 卡片悬停 */
  
  /* 强调色（鲜艳） */
  --accent-primary: #3b82f6;    /* 主蓝色 */
  --accent-glow: #60a5fa;       /* 蓝色光晕 */
  --accent-success: #10b981;    /* 翠绿 - 在线/成功 */
  --accent-warning: #f59e0b;    /* 琥珀 - 警告 */
  --accent-danger: #ef4444;     /* 鲜红 - 危险/预警 */
  --accent-purple: #8b5cf6;     /* 紫色 - 特殊标记 */
  --accent-pink: #ec4899;       /* 粉红 - 高亮 */
  
  /* 渐变 */
  --gradient-accent: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  --gradient-success: linear-gradient(135deg, #10b981 0%, #34d399 100%);
  --gradient-danger: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  
  /* 文字 */
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  
  /* 边框 */
  --border-light: rgba(148, 163, 184, 0.1);
  --border-medium: rgba(148, 163, 184, 0.2);
  --border-accent: rgba(59, 130, 246, 0.3);
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.3);
  --shadow-glow-danger: 0 0 20px rgba(239, 68, 68, 0.3);
}
```

---

## 📐 布局架构

### 可拖拽卡片布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  Top Bar (固定高度 56px)                                            │
│  [📡 DX Guardian]  [波段▼]  [地图类型▼]       [🔔3] [🌙] [⚙️]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────────────────────┐  ┌─────────────┐ │
│  │  ☀️ 太阳    │  │                             │  │  🎯 关注    │ │
│  │  数据卡片   │  │                             │  │  列表卡片   │ │
│  │             │  │      地    图               │  ├─────────────┤ │
│  │  [可拖拽]   │  │                             │  │  ✨ 推荐    │ │
│  └─────────────┘  │    (全屏可调整)             │  │  机会卡片   │ │
│      ↕️拖动       │                             │  ├─────────────┤ │
│  ┌─────────────┐  │                             │  │  🔔 预警    │ │
│  │  🔌 系统    │  │   - Spot 标记               │  │  列表卡片   │ │
│  │  状态卡片   │  │   - 聚类显示                │  │             │ │
│  │             │  │   - 热力图开关              │  │  [可拖拽]   │ │
│  │  [可拖拽]   │  │   - 灰线开关                │  └─────────────┘ │
│  └─────────────┘  │                             │        ↕️拖动    │
│      ↕️拖动       │                             │                  │
│  ┌─────────────┐  │                             │                  │
│  │  📡 我的    │  │                             │                  │
│  │  台站卡片   │  │                             │                  │
│  │             │  │                             │                  │
│  │  [可拖拽]   │  │                             │                  │
│  └─────────────┘  └─────────────────────────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 响应式断点

```css
/* 桌面优先 */
@media (min-width: 1400px) {
  /* 三栏布局：左面板 | 地图 | 右面板 */
  .layout { grid-template-columns: 280px 1fr 320px; }
}

@media (max-width: 1399px) and (min-width: 1024px) {
  /* 双栏布局：左面板 | 地图 + 右面板 */
  .layout { grid-template-columns: 240px 1fr; }
  .right-panel { position: absolute; right: 0; top: 56px; bottom: 0; width: 300px; }
}

@media (max-width: 1023px) {
  /* 平板：地图全屏，面板可滑出 */
  .left-panel { transform: translateX(-100%); }
  .right-panel { transform: translateX(100%); }
  .panel-open { transform: translateX(0) !important; }
}

@media (max-width: 640px) {
  /* 手机：单栏，底部 Tab 导航 */
  .layout { grid-template-columns: 1fr; }
  .bottom-nav { display: flex; } /* 显示底部导航栏 */
}
```

---

## 🎮 交互设计

### 1. 卡片拖拽

```javascript
// 使用 Interact.js 实现流畅拖拽
import interact from 'interactjs';

interact('.draggable-card').draggable({
  listeners: {
    move (event) {
      const target = event.target;
      const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
      const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
      
      target.style.transform = `translate(${x}px, ${y}px)`;
      target.setAttribute('data-x', x);
      target.setAttribute('data-y', y);
    }
  },
  modifiers: [
    interact.modifiers.restrictRect({
      restriction: 'parent',
      endOnly: true
    })
  ],
  inertia: true,
  autoScroll: true
});
```

### 2. 卡片调整大小

```javascript
interact('.resizable-card')
  .resizable({
    edges: { left: true, right: true, bottom: true, top: true },
    listeners: {
      move: function (event) {
        let { x, y } = event.target.dataset;
        x = (parseFloat(x) || 0) + event.deltaRect.left;
        y = (parseFloat(y) || 0) + event.deltaRect.top;
        
        Object.assign(event.target.style, {
          width: `${event.rect.width}px`,
          height: `${event.rect.height}px`,
          transform: `translate(${x}px, ${y}px)`
        });
        
        Object.assign(event.target.dataset, { x, y });
      }
    }
  });
```

### 3. 卡片收起/展开

```html
<div class="card collapsible" data-card-id="solar">
  <div class="card-header" onclick="toggleCard('solar')">
    <span class="card-icon">☀️</span>
    <span class="card-title">太阳数据</span>
    <button class="card-action collapse-btn">▼</button>
  </div>
  <div class="card-body collapse-content" id="card-solar">
    <!-- 内容 -->
  </div>
</div>

<script>
function toggleCard(cardId) {
  const card = document.getElementById(`card-${cardId}`);
  const btn = card.parentElement.querySelector('.collapse-btn');
  
  if (card.classList.contains('collapsed')) {
    card.classList.remove('collapsed');
    card.style.maxHeight = card.scrollHeight + 'px';
    btn.textContent = '▼';
    localStorage.setItem(`card-${cardId}`, 'expanded');
  } else {
    card.classList.add('collapsed');
    card.style.maxHeight = '0';
    btn.textContent = '▶';
    localStorage.setItem(`card-${cardId}`, 'collapsed');
  }
}
</script>
```

### 4. Tab 切换

```html
<div class="card-tabs">
  <div class="tab-header">
    <button class="tab-btn active" data-tab="watchlist">🎯 关注</button>
    <button class="tab-btn" data-tab="opportunities">✨ 推荐</button>
    <button class="tab-btn" data-tab="alerts">🔔 预警</button>
    <button class="tab-btn" data-tab="logs">📁 日志</button>
  </div>
  <div class="tab-content">
    <div class="tab-panel active" id="tab-watchlist">
      <!-- 关注列表内容 -->
    </div>
    <div class="tab-panel" id="tab-opportunities">
      <!-- 推荐机会内容 -->
    </div>
    <div class="tab-panel" id="tab-alerts">
      <!-- 预警内容 -->
    </div>
    <div class="tab-panel" id="tab-logs">
      <!-- 日志内容 -->
    </div>
  </div>
</div>

<style>
.tab-header {
  display: flex;
  gap: 0;
  background: var(--bg-secondary);
  border-radius: 8px 8px 0 0;
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
  font-weight: 500;
}

.tab-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--gradient-accent);
  color: white;
  box-shadow: var(--shadow-md);
}

.tab-panel {
  display: none;
  animation: fadeIn 0.3s ease;
}

.tab-panel.active {
  display: block;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

### 5. 通知徽章动画

```css
.notification-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: var(--gradient-danger);
  color: white;
  font-size: 11px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
  box-shadow: var(--shadow-glow-danger);
  animation: pulse-badge 2s infinite;
}

@keyframes pulse-badge {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

@keyframes shake-badge {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
}

.shake {
  animation: shake-badge 0.5s ease;
}
```

---

## 🗂️ 卡片详细设计

### 1. 太阳数据卡片

```html
<div class="card solar-card" data-card-type="solar">
  <div class="card-header">
    <div class="card-header-left">
      <span class="card-icon">☀️</span>
      <span class="card-title">太阳数据</span>
    </div>
    <div class="card-actions">
      <span class="card-badge" id="solar-condition">良好</span>
      <button class="card-btn" onclick="refreshSolar()" title="刷新">🔄</button>
      <button class="card-btn collapse-btn" onclick="toggleCard('solar')">−</button>
    </div>
  </div>
  <div class="card-body" id="card-solar">
    <div class="solar-grid">
      <div class="solar-stat">
        <div class="stat-label">SFI</div>
        <div class="stat-value gradient-blue" id="solar-sfi">---</div>
        <div class="stat-trend up">↑ +2.3</div>
      </div>
      <div class="solar-stat">
        <div class="stat-label">SSN</div>
        <div class="stat-value gradient-green" id="solar-sn">---</div>
        <div class="stat-trend same">→ 0</div>
      </div>
      <div class="solar-stat">
        <div class="stat-label">K 指数</div>
        <div class="stat-value gradient-yellow" id="solar-k">---</div>
        <div class="stat-trend down">↓ -0.5</div>
      </div>
      <div class="solar-stat">
        <div class="stat-label">A 指数</div>
        <div class="stat-value gradient-purple" id="solar-a">---</div>
      </div>
    </div>
    
    <!-- 传播预测迷你图表 -->
    <div class="mini-chart" id="propagation-chart">
      <canvas id="prop-canvas"></canvas>
    </div>
  </div>
</div>

<style>
.solar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px;
}

.solar-stat {
  text-align: center;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin: 8px 0;
}

.gradient-blue {
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.gradient-green {
  background: var(--gradient-success);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.gradient-yellow {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.gradient-purple {
  background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-trend {
  font-size: 11px;
  margin-top: 4px;
}

.stat-trend.up { color: var(--accent-success); }
.stat-trend.down { color: var(--accent-danger); }
.stat-trend.same { color: var(--text-muted); }

.mini-chart {
  padding: 12px;
  border-top: 1px solid var(--border-light);
}
</style>
```

### 2. 预警卡片（高优先级展示）

```html
<div class="card alerts-card" data-card-type="alerts">
  <div class="card-header">
    <div class="card-header-left">
      <span class="card-icon">🔔</span>
      <span class="card-title">预警中心</span>
      <span class="alert-count-badge" id="alert-count">3</span>
    </div>
    <div class="card-actions">
      <button class="card-btn" onclick="markAllRead()" title="全部已读">✓</button>
      <button class="card-btn" onclick="clearAllAlerts()" title="清空">✕</button>
      <button class="card-btn collapse-btn" onclick="toggleCard('alerts')">−</button>
    </div>
  </div>
  <div class="card-body" id="card-alerts">
    <!-- 筛选 Tab -->
    <div class="alert-filters">
      <button class="filter-btn active" data-filter="all">全部</button>
      <button class="filter-btn" data-filter="urgent">🔴 紧急</button>
      <button class="filter-btn" data-filter="important">🟡 重要</button>
      <button class="filter-btn" data-filter="normal">🟢 普通</button>
    </div>
    
    <!-- 预警列表 -->
    <div class="alert-list" id="alert-list">
      <!-- 紧急预警 -->
      <div class="alert-item alert-urgent unread" data-alert-id="123">
        <div class="alert-marker urgent"></div>
        <div class="alert-content">
          <div class="alert-header">
            <span class="alert-title">DX: JA1AAA on 14.074 MHz</span>
            <span class="alert-time">2 分钟前</span>
          </div>
          <div class="alert-body">
            <span class="alert-badge urgent">紧急</span>
            <span class="alert-detail">稀有 DXCC - Japan</span>
            <span class="alert-score">评分：95</span>
          </div>
        </div>
        <div class="alert-actions">
          <button class="btn-icon" onclick="silenceAlert(123)" title="静默">🔇</button>
          <button class="btn-icon" onclick="markRead(123)" title="已读">✓</button>
        </div>
      </div>
      
      <!-- 重要预警 -->
      <div class="alert-item alert-important unread" data-alert-id="124">
        <div class="alert-marker important"></div>
        <div class="alert-content">
          <div class="alert-header">
            <span class="alert-title">Band Opening: 10m</span>
            <span class="alert-time">5 分钟前</span>
          </div>
          <div class="alert-body">
            <span class="alert-badge important">重要</span>
            <span class="alert-detail">波段开放预测</span>
          </div>
        </div>
        <div class="alert-actions">
          <button class="btn-icon" onclick="silenceAlert(124)" title="静默">🔇</button>
          <button class="btn-icon" onclick="markRead(124)" title="已读">✓</button>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
.alert-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  margin: 8px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border-left: 4px solid var(--border-medium);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: slideIn 0.4s ease;
  cursor: pointer;
}

.alert-item:hover {
  background: var(--bg-card-hover);
  transform: translateX(4px);
  box-shadow: var(--shadow-md);
}

.alert-item.unread {
  background: linear-gradient(90deg, 
    rgba(59, 130, 246, 0.1) 0%, 
    var(--bg-secondary) 100%);
}

.alert-item.alert-urgent {
  border-left-color: var(--accent-danger);
}

.alert-item.alert-important {
  border-left-color: var(--accent-warning);
}

.alert-item.alert-normal {
  border-left-color: var(--accent-success);
}

.alert-marker {
  width: 4px;
  border-radius: 2px;
  animation: glow-pulse 2s infinite;
}

.alert-marker.urgent {
  background: var(--gradient-danger);
}

.alert-marker.important {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
}

.alert-marker.normal {
  background: var(--gradient-success);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 4px currentColor; opacity: 0.8; }
  50% { box-shadow: 0 0 12px currentColor; opacity: 1; }
}

.alert-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
  text-transform: uppercase;
}

.alert-badge.urgent {
  background: var(--gradient-danger);
  color: white;
}

.alert-badge.important {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  color: white;
}

.alert-score {
  float: right;
  font-weight: bold;
  color: var(--accent-primary);
}
</style>
```

### 3. Top Bar（顶栏）

```html
<header class="top-bar">
  <div class="top-bar-left">
    <div class="logo">
      <span class="logo-icon">📡</span>
      <span class="logo-text">DX Guardian</span>
    </div>
    
    <!-- 波段筛选器 -->
    <div class="band-filter">
      <button class="band-btn" data-band="all">全部</button>
      <button class="band-btn" data-band="160m">160m</button>
      <button class="band-btn" data-band="80m">80m</button>
      <button class="band-btn" data-band="40m">40m</button>
      <button class="band-btn active" data-band="20m">20m <span class="band-count">12</span></button>
      <button class="band-btn" data-band="15m">15m</button>
      <button class="band-btn" data-band="10m">10m <span class="band-count">5</span></button>
    </div>
  </div>
  
  <div class="top-bar-right">
    <!-- WebSocket 状态 -->
    <div class="status-indicator" id="ws-status">
      <span class="status-dot connected"></span>
      <span class="status-text">已连接</span>
    </div>
    
    <!-- 通知 -->
    <button class="icon-btn notification-btn" onclick="toggleNotifications()">
      <span class="icon">🔔</span>
      <span class="badge" id="notification-badge">3</span>
    </button>
    
    <!-- Web Push 开关 -->
    <div class="push-toggle">
      <input type="checkbox" id="push-toggle" onchange="togglePush()">
      <label for="push-toggle" class="toggle-label">
        <span class="toggle-track"></span>
        <span class="toggle-thumb"></span>
      </label>
      <span class="toggle-text">Push</span>
    </div>
    
    <!-- 主题切换 -->
    <button class="icon-btn" onclick="toggleTheme()" title="切换主题">
      <span class="icon">🌙</span>
    </button>
    
    <!-- 设置 -->
    <button class="icon-btn" onclick="openSettings()" title="设置">
      <span class="icon">⚙️</span>
    </button>
  </div>
</header>

<style>
.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: rgba(17, 24, 39, 0.95);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 1000;
  border-bottom: 1px solid var(--border-medium);
  box-shadow: var(--shadow-md);
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
  background: var(--gradient-accent);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.logo-icon {
  font-size: 24px;
  animation: rotate-satellite 10s linear infinite;
}

@keyframes rotate-satellite {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.band-filter {
  display: flex;
  gap: 4px;
  margin-left: 24px;
  overflow-x: auto;
}

.band-btn {
  padding: 6px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  color: var(--text-secondary);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.band-btn:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-accent);
}

.band-btn.active {
  background: var(--gradient-accent);
  border-color: transparent;
  color: white;
}

.band-count {
  background: rgba(255,255,255,0.2);
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 10px;
  margin-left: 4px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border-radius: 20px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--accent-success);
  box-shadow: 0 0 8px var(--accent-success);
  animation: pulse-dot 2s infinite;
}

.status-dot.disconnected {
  background: var(--accent-danger);
}

.status-dot.connecting {
  background: var(--accent-warning);
  animation: blink-dot 1s infinite;
}

.notification-btn {
  position: relative;
}

.notification-btn .badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--gradient-danger);
  color: white;
  font-size: 10px;
  font-weight: bold;
  padding: 2px 5px;
  border-radius: 8px;
  animation: pulse-badge 2s infinite;
}

.push-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  position: relative;
  width: 44px;
  height: 24px;
  cursor: pointer;
}

.toggle-track {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-medium);
  border-radius: 12px;
  transition: background 0.3s;
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: transform 0.3s, background 0.3s;
}

#push-toggle:checked + .toggle-label .toggle-track {
  background: var(--gradient-success);
  border-color: transparent;
}

#push-toggle:checked + .toggle-label .toggle-thumb {
  transform: translateX(20px);
  background: white;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.icon-btn:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-accent);
  transform: scale(1.05);
}
</style>
```

---

## 🎬 动画效果

### Spot 标记动画

```css
.spot-marker {
  position: relative;
}

.spot-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--gradient-accent);
  border: 2px solid white;
  box-shadow: 
    0 2px 8px rgba(0,0,0,0.5),
    0 0 12px var(--accent-glow),
    inset 0 -2px 4px rgba(0,0,0,0.3),
    inset 0 2px 4px rgba(255,255,255,0.3);
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.spot-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--accent-primary);
  opacity: 0;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0.6; }
  100% { transform: translate(-50%, -50%) scale(2.5); opacity: 0; }
}

/* 新 Spot 入场动画 */
@keyframes spot-enter {
  0% {
    opacity: 0;
    transform: scale(0) rotate(-180deg);
  }
  60% {
    transform: scale(1.2) rotate(10deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }
}

.spot-marker.new {
  animation: spot-enter 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### 卡片进入动画

```css
.card {
  opacity: 0;
  transform: translateY(20px);
  animation: card-enter 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.card:nth-child(1) { animation-delay: 0.1s; }
.card:nth-child(2) { animation-delay: 0.2s; }
.card:nth-child(3) { animation-delay: 0.3s; }

@keyframes card-enter {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 📦 技术选型

### 依赖库

```json
{
  "dependencies": {
    "interactjs": "^1.10.20",      // 拖拽库
    "chart.js": "^4.4.0",          // 图表
    "leaflet": "^1.9.4",           // 地图
    "socket.io-client": "^4.7.0"   // WebSocket
  }
}
```

### 文件结构

```
dx_guardian/frontend/
├── index.html              # 主页面（重写）
├── css/
│   ├── main.css           # 全局样式
│   ├── cards.css          # 卡片样式
│   ├── animations.css     # 动画
│   └── responsive.css     # 响应式
├── js/
│   ├── app.js             # 主逻辑
│   ├── layout.js          # 布局管理（拖拽/调整）
│   ├── cards.js           # 卡片交互
│   ├── map.js             # 地图
│   ├── socket.js          # WebSocket
│   ├── storage.js         # 本地存储
│   └── utils.js           # 工具函数
└── images/
```

---

## ✅ 实施检查清单

### Phase 1: 基础架构
- [ ] 创建新的 HTML 结构
- [ ] 实现 CSS 变量系统
- [ ] 实现 Top Bar
- [ ] 实现基础卡片样式

### Phase 2: 交互功能
- [ ] 集成 interact.js
- [ ] 实现卡片拖拽
- [ ] 实现卡片调整大小
- [ ] 实现收起/展开
- [ ] 实现 Tab 切换

### Phase 3: 数据集成
- [ ] 迁移 WebSocket 连接
- [ ] 迁移地图功能
- [ ] 迁移 Spot 显示
- [ ] 实现实时更新

### Phase 4: 优化
- [ ] 添加动画效果
- [ ] 响应式适配
- [ ] 性能优化
- [ ] 本地存储偏好

---

## 🎯 设计原则

1. **视觉层次清晰** - 使用阴影、渐变、大小区分层级
2. **交互动画流畅** - 所有交互都有反馈动画
3. **色彩鲜艳但不刺眼** - 深色背景衬托鲜艳强调色
4. **可自定义布局** - 用户可拖拽调整卡片位置
5. **响应式优先** - 桌面/平板/手机全适配

---

这个方案包含了丰富的交互和鲜艳的配色，你觉得如何？可以直接开始实现，还是需要调整哪些细节？
