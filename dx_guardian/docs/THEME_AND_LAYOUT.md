# 主题配色与布局设计文档

## 📋 修改历史

### 2026-05-03 主题配色系统

#### 新增主题选择器
- **位置**：Top Bar 右上角
- **按钮**：显示"主题"文字 + 彩色图标
- **下拉菜单**：6 个主题选项，带预览色块

#### 6 种配色方案

| 主题名 | data-theme | 主背景 | 卡片 | 强调色 | 文字 | 适用场景 |
|--------|-----------|--------|------|--------|------|---------|
| **默认（深空）** | default | `#0f0f1a` | `#16213e` | `#e94560` | `#e0e0e0` | 夜间工作 |
| **浅色（明亮）** | light | `#f5f7fa` | `#ffffff` | `#409EFF` | `#303133` | 白天办公 |
| **海洋（蓝调）** | ocean | `#0a1628` | `#1a3a5c` | `#00d9ff` | `#e0f0ff` | 专业冷静 |
| **森林（绿色）** | forest | `#0d1a0f` | `#1a3a1f` | `#4CAF50` | `#e0ffe0` | 自然舒适 |
| **日落（暖色）** | sunset | `#1a0f0f` | `#3a1a1a` | `#ff6b6b` | `#ffe0e0` | 温暖柔和 |
| **紫韵（紫色）** | purple | `#1a0f28` | `#3a1a5c` | `#d580ff` | `#f0e0ff` | 神秘优雅 |

#### CSS 变量系统

```css
:root {
    --bg-primary: #0f0f1a;        /* 主背景 */
    --bg-secondary: #16213e;      /* 次要背景 */
    --bg-tertiary: #1a1a2e;       /* 第三层背景 */
    --bg-card: #16213e;           /* 卡片背景 */
    --accent-primary: #e94560;    /* 主强调色 */
    --accent-secondary: #4CAF50;  /* 次要强调色 */
    --text-primary: #e0e0e0;      /* 主文字色 */
    --text-secondary: #aaa;       /* 次要文字色 */
    --border-color: rgba(255,255,255,0.08);
    --border-hover: rgba(255,255,255,0.15);
}

[data-theme="light"] {
    --bg-primary: #f5f7fa;
    --bg-secondary: #ffffff;
    --bg-tertiary: #ebeef5;
    --bg-card: #ffffff;
    --accent-primary: #409EFF;
    --accent-secondary: #67C23A;
    --text-primary: #303133;
    --text-secondary: #606266;
    --border-color: #dcdfe6;
    --border-hover: #b4bbc9;
}
```

#### 主题切换功能

**JavaScript 实现**：
```javascript
function setTheme(themeName) {
    applyTheme(themeName);
    localStorage.setItem('dx-theme', themeName);
    updateThemeUI(themeName);
}

function initTheme() {
    const saved = localStorage.getItem('dx-theme');
    if (saved) applyTheme(saved);
}
```

**特性**：
- ✅ localStorage 持久化
- ✅ 平滑过渡动画 (0.3s)
- ✅ 点击外部关闭下拉菜单
- ✅ 高对比度文字 (#303133)

### 2026-05-03 三栏布局设计

#### 布局结构

```
┌─────────────────────────────────────────────┐
│ Top Bar (48px)                              │
│ 📡 DX Guardian  [波段条]      主题选择器   │
├──────────┬─────────────────────┬───────────┤
│ 左侧栏   │  地图栏             │  右侧栏   │
│ (280px)  │  (flex)             │  (360px)  │
│          │                     │           │
│ 卡片列表 │  世界地图           │  卡片列表 │
│ - 太阳   │  - Spot 标记        │  - 传播   │
│ - 系统   │  - 热力图           │  - 趋势   │
│ - 台站   │  - 灰线             │  - 预警   │
│ - 关注   │                     │  - 机会   │
│          │                     │  - 波段   │
│          │                     │  - VOACAP │
│          │                     │  - 日志   │
└──────────┴─────────────────────┴───────────┘
```

#### 响应式设计

```css
/* 默认：三栏布局 */
.layout {
    display: grid;
    grid-template-columns: 280px 1fr 360px;
}

/* 平板：调整宽度 */
@media (max-width: 1024px) {
    .layout {
        grid-template-columns: 220px 1fr 280px;
    }
}

/* 手机：单栏堆叠 */
@media (max-width: 768px) {
    .layout {
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr auto;
    }
}
```

#### 可拖拽卡片

**功能**：
- ✅ SortableJS 实现拖拽
- ✅ 跨列拖拽（左右栏之间）
- ✅ localStorage 保存位置
- ✅ 卡片折叠（+/- 按钮）

**实现**：
```javascript
function initDragAndDrop() {
    Sortable.create(document.getElementById('col-left'), {
        group: 'cards',
        animation: 150,
        handle: '.card-header',
        store: {
            set: (sortable) => {
                localStorage.setItem(
                    'dx-card-order-col-left',
                    sortable.toArray().join('|')
                );
            }
        }
    });
}
```

#### 卡片样式

```css
.card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    margin-bottom: 8px;
    transition: all 0.3s;
}

.card:hover {
    border-color: var(--border-hover);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.card-header {
    background: rgba(255,255,255,0.04);
    color: var(--accent-primary);
    cursor: move;  /* 拖拽手柄 */
}
```

### Git 提交记录

```
commit 8c9e309 - UI 布局升级
  - 三栏布局 + 卡片拖拽
  - 模态框功能
  - 修复 ID 不匹配

commit e354a06 - 新增主题配色
  - 5 种深色主题
  - CSS 变量系统
  - localStorage 保存

commit 5c08c92 - 新增浅色主题
  - light 主题
  - 修复默认主题显示

commit 155b9e0 - 修复选择器样式
  - 下拉菜单样式修复
  - 文字颜色优化

commit 01d1d4c - 优化选择器效果
  - 阴影深度增加
  - 字体调整

commit 0a38711 - 优化文字对比度
  - "配色" → "主题"
  - 统一浅色内衬
  - 固定深色文字
```

## 🎨 设计原则

1. **统一性**：CSS 变量贯穿所有颜色和样式
2. **可访问性**：所有主题保证 WCAG 对比度标准
3. **灵活性**：用户可自定义主题和布局
4. **性能**：硬件加速过渡动画，localStorage 持久化
5. **响应性**：从手机到桌面完美适配

## 📦 文件位置

- **样式**：`dx_guardian/frontend/index.html` (内嵌 CSS)
- **逻辑**：`dx_guardian/frontend/js/app.js`
- **布局**：`dx_guardian/frontend/index.html`

## 🔗 相关链接

- GitHub: https://github.com/BG2ENW/dx-guardian
- 分支：`260502-chore-secure-config-secrets`
