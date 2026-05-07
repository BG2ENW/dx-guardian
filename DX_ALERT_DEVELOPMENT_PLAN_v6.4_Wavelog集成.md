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
