# 主题配色显示问题诊断

## 问题：深空配色背景显示为白色

### 已确认的 CSS 定义

```css
:root {
    --bg-primary: #0f0f1a;  /* 深蓝色背景 */
}
body {
    background: var(--bg-primary);
}
```

这应该是正确的深空深色背景。

### 可能的原因和解决方案

#### 1. 浏览器缓存问题
**解决方法：**
- 强制刷新：`Ctrl+Shift+R`（Windows/Linux）或 `Cmd+Shift+R`（Mac）
- 清除浏览器缓存后重新加载
- 使用无痕模式打开

#### 2. 浏览器扩展干扰
某些浏览器扩展（如 Dark Reader、Stylus）可能覆盖了 CSS 变量。

**检查方法：**
- 禁用所有扩展后刷新页面
- 如果正常显示，逐个启用扩展找出问题

#### 3. 系统深色模式冲突
某些系统可能会强制网页使用深色/浅色模式。

**检查方法：**
- 在浏览器开发者工具中检查 `computed` 样式
- 查看 `background` 属性最终值是什么

### 诊断步骤

1. **打开浏览器开发者工具**（F12）
2. **检查元素** → 选择 `<body>` 标签
3. **查看 Computed 样式** → 搜索 `background`
4. **确认最终应用的背景色**

### CSS 变量检查清单

在开发者工具控制台中运行：
```javascript
getComputedStyle(document.documentElement).getPropertyValue('--bg-primary')
```

应该返回：`#0f0f1a`

### 临时解决方案

如果 CSS 变量不起作用，可以直接在浏览器控制台运行：
```javascript
document.body.style.background = '#0f0f1a'
```

这会立即将背景设置为深空色。

### 已部署主题列表

| 主题名 | data-theme 值 | 背景色 |
|--------|--------------|--------|
| 默认（深空）| default | `#0f0f1a` |
| 浅色（明亮）| light | `#f5f7fa` |
| 海洋（蓝调）| ocean | `#0a1628` |
| 森林（绿色）| forest | `#0d1a0f` |
| 日落（暖色）| sunset | `#1a0f0f` |
| 紫韵（紫色）| purple | `#1a0f28` |

### 切换主题

在控制台运行：
```javascript
setTheme('default')  // 深空
setTheme('light')    // 浅色
setTheme('ocean')    // 海洋
```

### 联系支持

如果问题持续，请提供：
1. 浏览器版本
2. 操作系统
3. 浏览器扩展列表
4. 开发者工具截图（Computed 样式）
