# DX Guardian - 开发计划书 v6.4：Wavelog 深度集成

> 版本：v6.4
> 日期：2026-05-07
> 更新：新增 Wavelog MySQL 直接调用、用户登录适配、界面主题适配

---

## 一、概述

**目标：与 Wavelog 深度集成，实现数据互通和界面统一**

- Wavelog 里有的数据直接调取，不再手动维护
- 用户登录、主题、页面布局与 Wavelog 一致

---

## 二、Wavelog MySQL 数据库连接

### 2.1 核心表结构（需映射）

```sql
-- Wavelog 核心表
users              -- 用户账户
stations           -- 电台 station 配置
qsos               -- QSO 日志记录
qso_details        -- QSO 详细（如 RST、QTH）
lotw_users         -- LoTW 用户数据
club_log_qsos      -- ClubLog 上传记录
dxcc_entities      -- DXCC 实体表
```

### 2.2 数据映射策略

| DX Guardian 数据 | Wavelog 源 | 同步策略 |
|------------------|------------|----------|
| 用户信息 | users.station_callsign | 只读 |
| QSO 日志 | qsos | 只读 + 缓存 |
| DXCC 实体 | dxcc_entities / ClubLog API | 每日增量 |
| LoTW 状态 | lotw_users | 每周同步 |

### 2.3 任务分解

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 2.1 | Wavelog 数据库连接配置 | 0.5天 | 数据库连接池 |
| 2.2 | Wavelog 用户数据同步 | 1天 | 用户表映射 |
| 2.3 | Wavelog 日志数据直接查询 | 1.5天 | QSO 数据读取 |
| 2.4 | ClubLog DXCC 更新同步 | 1天 | DXCC 同步机制 |
| 2.5 | 数据一致性校验 | 1天 | 对比报告 |

---

## 三、用户登录适配

### 3.1 认证流程

```
用户登录 → Wavelog 验证 → 获取 Station → 绑定 DX Guardian
```

### 3.2 任务分解

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 3.1 | Wavelog 用户认证集成 | 1天 | OAuth/密码认证 |
| 3.2 | 多 station 支持 | 0.5天 | 电台选择 |
| 3.3 | Session 共享 | 0.5天 | SSO 方案 |

---

## 四、界面主题适配

### 4.1 Wavelog 布局结构

```
┌─────────────────────────────────────────┐
│ Header (Logo + Nav + User)              │
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │     Main Content             │
│ (Menu)   │                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

### 4.2 主题变量映射

| Wavelog 变量 | DX Guardian 变量 | 用途 |
|--------------|------------------|------|
| --primary-color | --color-primary | 主色调 |
| --bg-color | --bg-primary | 背景色 |
| --text-color | --text-primary | 文字色 |
| --header-bg | --header-background | 顶部栏 |
| --sidebar-bg | --sidebar-background | 侧边栏 |

### 4.3 任务分解

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 4.1 | Wavelog 主题检测 | 0.5天 | 主题检测 |
| 4.2 | 颜色变量映射 | 0.5天 | CSS 变量 |
| 4.3 | 深色/浅色模式适配 | 1天 | 双主题 |
| 4.4 | 页面布局一致性 | 1天 | Header/Footer/Sidebar |

---

## 五、直接调用 Wavelog 数据

### 5.1 数据调用矩阵

| 数据类型 | 调用方式 | 用途 |
|----------|----------|------|
| 用户 station | MySQL 直接查询 | 多电台切换 |
| QSO 历史 | MySQL + 缓存 | 日志分析 |
| 已确认 DXCC | MySQL 查询 | 缺失 DXCC 计算 |
| ClubLog 上传 | ClubLog API | DXCC 状态验证 |
| LoTW 确认 | MySQL 查询 | LoTW 徽章显示 |

### 5.2 数据流

```
Wavelog MySQL ──→ DX Guardian API ──→ 前端展示
     │                                    │
     └─ 每日增量同步 → 本地缓存           │
```

---

## 六、交付标准

- [ ] Wavelog 用户可直接登录
- [ ] 界面主题与 Wavelog 一致
- [ ] 可直接读取 Wavelog 日志数据
- [ ] ClubLog DXCC 状态自动同步
- [ ] 不再需要手动维护用户数据

---

## 七、预计时间

| 阶段 | 时间 |
|------|------|
| 数据库连接 + 数据映射 | 4天 |
| 用户登录适配 | 2天 |
| 界面主题适配 | 3天 |
| **总计** | **5-7天** |
---

## 八、实际开发记录（2026-05-07）

### 8.1 Wavelog 安装与配置

- [x] PHP 8.3.6 + Apache 2.4.58 安装
- [x] Wavelog v2.4.1 源码部署到 /home/jacky/.openclaw/workspace/apps/wavelog
- [x] 连接远程 MySQL 数据库（39.103.65.85:3306）
- [x] 修复 MySQL 5.7 兼容性问题（upper() 函数）
- [x] 配置 Apache 反向代理（/api/ → Flask:5000）
- [x] 修复 assets 静态文件 404 问题

### 8.2 Wavelog 登录与用户

- [x] Wavelog 登录页面正常显示
- [x] 用户登录功能修复（MySQL SQL 语法问题）
- [x] 中文语言配置（chinese_simplified）
- [x] 用户偏好设置为中文

### 8.3 DX Alert 页面集成

- [x] 创建 Dxalert.php 控制器，复用 Wavelog header/footer
- [x] 创建 /application/views/dxalert/content.php 视图
- [x] 导航栏添加"DX Alert"链接
- [x] 页面样式完全适配 Wavelog Darkly 主题
- [x] 修复 Apache 反向代理配置

### 8.4 API 对接

- [x] 配置 dxalert_config.php 配置文件
- [x] 修复 API 路径重复问题（/api/api/health → /health）
- [x] Apache 反向代理：/api/ → http://127.0.0.1:5000/api/

### 8.5 功能模块（完善中）

- [x] 健康状态 API（/health）
- [x] 波段分布图表
- [x] 太阳数据（太阳通量、SN、A指数）
- [x] 最新 Spot 列表
- [x] 传播预测
- [ ] 告警功能
- [ ] 用户自定义台站配置

### 8.6 文件清单

| 文件 | 说明 |
|------|------|
| /application/controllers/Dxalert.php | 控制器 |
| /application/views/dxalert/content.php | 视图 |
| /dxalert_config.php | API 配置文件 |
| /application/config/config.php | 添加 api_url 配置 |
| /application/config/config.php | language = chinese_simplified |

### 8.7 访问地址

- Wavelog: http://192.168.10.4
- DX Alert: http://192.168.10.4/dxalert
- API: http://192.168.10.4/api/

---

## 九、待完成功能

- [ ] 用户告警配置界面
- [ ] 台站配置自动从 Wavelog 获取（已有初步代码）
- [ ] ADIF 日志上传功能
- [ ] 实时 Spot 推送通知
- [ ] 微信/Telegram 通知集成

---

## 十、新功能扩展规划（v6.5 基于 dxcontest.org 调研）

> 更新：2026-05-07
> 参考：dxcontest.org、pskreporter.info、hamqsl.com

### 10.1 MAP 可视化（详细功能）

| 功能 | 数据来源 | 展示方式 | 优先级 |
|------|----------|----------|--------|
| 实时 Spot 标记 | history | 带时间衰减标记 | P0 |
| 路径弧线 | history → lat/lon | 大圆弧连线发→收 | P1 |
| 距离环 | 计算两点距离 | 1000/3000/5000km 圈 | P1 |
| 热力图 | history 聚合 | 颜色深浅表示活跃度 | P2 |
| 网格覆盖 | Maidenhead | 按 DXCC/分区着色 | P2 |
| 波段/模式过滤 | history | 切换显示特定波段 | P1 |
| 点击详情 | spot 数据 | Call/Freq/Mode/RST/DXCC | P0 |
| 地图切换 | - | 卫星/街道/地形 | P2 |

### 10.2 智能分析

| 功能 | 数据来源 | 展示方式 | 优先级 |
|------|----------|----------|--------|
| 传播评分 | solar + history | 0-100 分 + 环形进度条 | P0 |
| 黄金时段 | history 时序分析 | "现在适合通联 XX" | P1 |
| 稀有度指数 | DXCC 统计 | 🟢🟡🔴 难度指示 | P1 |
| 距离分布图 | history 统计 | 柱状图：各距离段数量 | P1 |
| 模式趋势 | history mode 统计 | 饼图：FT8/FT4/CW 占比 | P1 |
| 太阳风暴预警 | solar k_index | K>5 红色警报 | P0 |
| 实时热点 | history 聚合 | 按数量排序的 DX | P2 |
| 国家/前缀统计 | history | TOP 10 排行榜 | P2 |

### 10.3 预警功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 声音提醒 | 浏览器通知 + 提示音 | P1 |
| 新 Spot 弹窗 | 弹出 + 声音 | P1 |
| 前缀/后缀匹配 | JA*/KH6 等 | P0 |
| DXCC 提醒 | 稀有国家 | P0 |
| 网格提醒 | Grid Square | P1 |
| 波段提醒 | 特定波段 | P1 |
| 模式提醒 | FT8/FT4/CW | P1 |
| LoTW 确认弹窗 | 收到确认时弹出 | P1 |
| 新波段开放 | 40m→20m 打开时提醒 | P2 |
| 条件组合 | AND/OR 多条件 | P1 |

### 10.4 数据源对比

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 三源对比 | PSKRep / RBN / DXCluster 各多少 | P1 |
| 数据新鲜度 | 最后更新时间 | P2 |
| 源质量评分 | 各源可靠性 | P2 |

### 10.5 更直观的展示形式

| 形式 | 位置 | 优先级 |
|------|------|--------|
| 环形进度条 | 传播评分 | P1 |
| 迷你 Sparkline | Spot 列表行 | P2 |
| 状态灯牌 | Cluster 连接状态 | P0 |
| 渐变背景 | 太阳数据好→差 | P1 |
| 数字跳动动画 | Spot 数量变化 | P1 |

### 10.6 其它功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| Spot 发送 | 手动提交 Spot | P2 |
| POTA/SOTA/WWFF | 激活标记 | P2 |
| 竞赛日历 | Contest Schedule | P2 |
| 电台日志 | 直接查 Wavelog | P1 |

---

## 十一、前端 Web 设计样稿（v1）

> 基于 dxcontest.org 风格 + 新功能

### 11.1 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│  [状态栏] Cluster灯 | Spots:2313 | SFI:117 | SSN:38 | A:10  │
├─────────────────────────────────────────────────────────────┤
│  [地图区 220px]  ████████████████████████  ×关闭           │
│  - 实时 Spot 标记 + 路径弧线 + 距离环                        │
├─────────────────────────────────────────────────────────────┤
│  [波段条] 20m 114 | 17m 60 | 15m 61 | 40m 35 | 80m 20      │
├─────────────────────────────────────────────────────────────┤
│  [主体 Spot 列表]                        [传播评分 78/100] │
│  ┌──────┬────────┬────────┬────────┬────────┬─────────┐    │
│  │Time  │Call    │Freq    │Mode    │Country │Source   │    │
│  ├──────┼────────┼────────┼────────┼────────┼─────────┤    │
│  │22:58 │OH6CH  │21070.0 │FT8     │Finland │RBN      │    │
│  │22:57 │LU5DLA │14074.0 │FT8     │Argentina│PSKRep   │    │
│  └──────┴────────┴────────┴────────┴────────┴─────────┘    │
├────────────────────────────┬────────────────────────────────┤
│  [预警设置]                │  [智能分析]                    │
│  ○ 新 Spot 提醒            │  ┌────────────────────────┐   │
│  ☑ JA/* 前缀               │  │    传播评分 78/100     │   │
│  ☑ 稀有 DXCC               │  │    ████████░░ 环形     │   │
│  输入: [________] [+添加]  │  │ 推荐波段: 20m 17m 15m   │   │
│  [我的告警列表]            │  └────────────────────────┘   │
│  - JA1XYZ  21MHz  22:58   │  [距离分布] [模式占比] [TOP]   │
├────────────────────────────┴────────────────────────────────┤
│  [数据源] PSKRep: 45% | RBN: 35% | DXCluster: 20%          │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 设计规范

| 元素 | 规范 |
|------|------|
| 主色调 | #f57c00 (橙色) |
| 背景 | #1a1a1a (深灰) |
| 卡片 | #262626 |
| 文字 | #e0e0e0 |
| 成功 | #10b981 (绿色) |
| 警告 | #f59e0b (黄色) |
| 危险 | #ef4444 (红色) |
| 字体 | SF Pro Display, Segoe UI, Roboto |
| 圆角 | 8-10px |
| 间距 | 8px / 12px / 16px |

### 11.3 组件清单

| 组件 | 说明 |
|------|------|
| status-bar | 顶部状态栏 |
| map-section | 地图区域（可关闭） |
| band-bar | 波段活跃条 |
| spot-table | Spot 列表（可滚动） |
| propagation-score | 传播评分环形图 |
| alert-config | 预警配置面板 |
| source-stats | 数据源统计 |
| alert-list | 告警列表 |
| station-info | 电台信息 |


---

## 十二、模块集成规范（v6.5 补充）

> 更新：2026-05-07

### 12.1 集成原则

| 原则 | 说明 |
|------|------|
| **深度集成** | 模块功能深度嵌入 Wavelog 页面布局 |
| **样式统一** | 配色、模板、文字与 Wavelog 保持一致 |
| **只读引用** | 不修改 Wavelog 任何源码，只读取和引用 |
| **独立目录** | 模块代码独立存放，不与 Wavelog 混同 |
| **数据隔离** | 用户数据存储在独立数据库/文件 |

### 12.2 禁止事项

- ❌ 修改 Wavelog 核心文件
- ❌ 直接覆盖 Wavelog 视图模板
- ❌ 在 Wavelog 目录混建文件
- ❌ 推送 Wavelog 源码到 GitHub

### 12.3 目录结构

```
wavelog/
├── application/views/dxalert/     # 我们的视图（独立目录）
├── assets/js/dxalert/             # 我们的 JS
├── assets/css/dxalert/            # 我们的 CSS
└── ...

dx-guardian-new/                   # 我们的主项目（独立）
├── backend/                       # Flask API
├── docs/                          # 文档
└── ...
```

### 12.4 引用规范

| 资源 | 引用方式 |
|------|----------|
| Wavelog 配色 | 通过 CSS 变量或继承 Wavelog 主题 |
| Wavelog 字体 | 使用 Wavelog 引用的字体 |
| Wavelog Header/Footer | 通过 `$this->load->view()` 加载 |
| Wavelog 用户数据 | 通过 Wavelog Model 读取 |
| Wavelog 静态资源 | 通过 `base_url()` 引用 |

