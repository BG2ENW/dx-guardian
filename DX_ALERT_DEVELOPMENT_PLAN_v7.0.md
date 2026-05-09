# DX Guardian - 开发计划书 v7.0（多数据源实时 DX Cluster）

> 版本：v7.0
> 日期：2026-05-09
> 基于：v6.4 完整版重构
> 呼号：BG2ENW | 位置：PN35HS（哈尔滨）
> 参考目标：

---

## 一、项目定位

> **多数据源实时 DX Spot 聚合 + 全球电台地图 + 传播条件分析 + 特殊活动追踪**
> 支持两种运行模式：Wavelog 深度集成模式 或 独立模式

---

## 二、运行模式

### 2.1 模式概述

| 模式 | 说明 | 数据来源 | 用户认证 |
|------|------|----------|----------|
| **Wavelog 集成模式** | 深度绑定 Wavelog，作为子模块运行 | Wavelog MySQL 数据库 | Wavelog Session |
| **独立模式** | 完全独立运行，不依赖 Wavelog | ADIF 文件导入 | 无（本地模式） |

### 2.2 Wavelog 集成模式

```
Wavelog 主程序
├── application/
├── assets/
├── dx_guardian/          # DX Guardian 作为子模块
│   ├── backend/          # Flask API
│   ├── frontend/         # 前端页面
│   └── config.yaml       # 配置文件
└── ...
```

**特点**：
- 放在 Wavelog 目录下二级目录 (`dx_guardian/`)
- 复用了 Wavelog 的用户认证
- 直接读取 Wavelog MySQL 数据库
- 界面主题与 Wavelog 一致

### 2.3 独立模式

```
dx_guardian/
├── backend/
├── frontend/
├── data/
│   └── input/
│       └── my_log.adif   # 用户配置的 ADIF 文件
└── config.yaml
```

**特点**：
- 完全独立，不依赖 Wavelog
- 通过配置文件指定 ADIF 文件位置
- 不需要用户认证（本地使用）
- 默认使用 SQLite 存储

---

## 三、Wavelog 配置文件（YAML）

### 3.1 配置文件位置

| 模式 | 配置文件路径 |
|------|-------------|
| Wavelog 集成 | `{Wavelog根目录}/dx_guardian/config.yaml` |
| 独立模式 | `{DX Guardian根目录}/config.yaml` |

### 3.2 完整配置示例

```yaml
# DX Guardian 配置文件
# 说明：YAML 格式，支持两种运行模式

# ==================== 运行模式 ====================
mode: "standalone"  # wavelog | standalone

# ==================== Wavelog 集成配置 ====================
wavelog:
  # Wavelog 安装根目录（集成模式必填）
  root_path: "/home/jacky/.openclaw/workspace/apps/wavelog"
  
  # 数据库连接（集成模式必填）
  database:
    host: "localhost"
    port: 3306
    user: "wavelog"
    password: "your_password"
    name: "wavelog"
  
  # 用户认证配置
  auth:
    # Wavelog Session 密钥（用于验证用户登录状态）
    session_key: "wavelog_session"
    # 登录验证 API 路径
    login_check_path: "/index.php/user/login"
  
  # 数据同步策略
  sync:
    # QSO 日志同步间隔（分钟）
    qso_interval: 5
    # DXCC 实体同步间隔（天）
    dxcc_interval: 1
    # LoTW 状态同步间隔（天）
    lotw_interval: 7

# ==================== 独立模式配置 ====================
standalone:
  # ADIF 文件位置（独立模式必填）
  adif:
    # 主日志文件（支持通配符）
    file_path: "/path/to/your/log.adif"
    # 附加日志文件（可选多个）
    additional_files:
      - "/path/to/contest_log.adif"
      - "/path/to/travel_log.adif"
    # 自动重新加载（文件变化检测）
    auto_reload: true
  
  # 本地数据库（独立模式使用 SQLite）
  database:
    path: "./data/dx_guardian.db"
  
  # 用户配置（独立模式）
  user:
    callsign: "BG2ENW"
    grid: "PN35HS"
    lat: 45.8
    lon: 126.5

# ==================== 数据源配置 ====================
datasources:
  # PSK Reporter
  pskreporter:
    enabled: true
    query_interval: 310  # 秒（≥300）
    contact_email: "bg2enw@163.com"
    max_results: 100
  
  # DX Cluster
  cluster:
    enabled: true
    servers:
      - host: "bh3bbj.rfsec.cn"
        port: 7373
        priority: 1
      - host: "dxc.n4zkf.com"
        port: 7300
        priority: 2
    reconnect_delays: [5, 15, 30, 60]
    max_attempts: 5
  
  # POTA
  pota:
    enabled: true
    refresh_interval: 900  # 15分钟
  
  # SOTA
  sota:
    enabled: true
    refresh_interval: 900
  
  # WWFF
  wwff:
    enabled: true
    refresh_interval: 900

# ==================== 太阳数据配置 ====================
solar:
  noaa_url: "https://services.swpc.noaa.gov/products"
  refresh_interval: 600  # 10分钟
  cache_ttl: 600

# ==================== 服务器配置 ====================
server:
  host: "0.0.0.0"
  port: 5001
  debug: false

# ==================== 前端配置 ====================
# 前端独立部署时，通过此配置连接后端
frontend:
  # 后端 API 地址（前端通过此地址获取数据）
  # 独立部署时修改为实际后端地址
  api_url: "http://localhost:5001"
  
  # WebSocket 地址（可选，用于实时推送）
  # 如果不配置，则前端使用 HTTP 轮询
  # ws_url: "ws://localhost:5001/ws"
  
  # 刷新间隔（毫秒）
  refresh_interval: 300000  # 5分钟
  
  # 地图服务
  # 高德地图（国内用户）
  amap:
    key: "YOUR_AMAP_KEY"
    security_code: "YOUR_SECURITY_CODE"
  # 或 Leaflet（国外用户）
  leaflet:
    tile_server: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

# 前端独立部署示例：
# 1. 拷贝 frontend/ 目录到 Wavelog 目录
# 2. 修改 config.yaml 中的 frontend.api_url 为实际后端地址
# 3. 通过 Wavelog 访问前端页面
#
# Wavelog 集成模式下的目录结构：
# wavelog/
# ├── application/
# ├── assets/
# ├── dx_frontend/              # 前端目录
# │   ├── index.html
# │   ├── css/
# │   ├── js/
# │   └── config.js             # 前端配置（API 地址等）
# └── dx_guardian/              # 后端目录
#     ├── backend/
#     └── config.yaml

# ==================== 应用配置 ====================
app:
  # Spot 去重配置
  dedup:
    time_window: 300  # 5分钟
    max_cache: 1000
    key_format: "callsign_frequency_mode"  # 去重键格式
  
  # 缓存配置
  cache:
   spots_ttl: 300
    solar_ttl: 600
    activity_ttl: 900
  
  # 日志配置
  logging:
    level: "INFO"
    file: "./logs/dx_guardian.log"
```

### 3.3 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `mode` | 是 | `wavelog` 或 `standalone` |
| `wavelog.root_path` | Wavelog模式 | Wavelog 安装目录 |
| `wavelog.database.*` | Wavelog模式 | MySQL 连接信息 |
| `standalone.adif.file_path` | 独立模式 | ADIF 文件路径 |
| `standalone.user.callsign` | 独立模式 | 自己的呼号 |
| `datasources.*.enabled` | 是 | 是否启用该数据源 |
| `server.port` | 是 | 服务端口 |
| `server.amap.key` | 否 | 高德地图 API Key |

---

## 四、数据流程

### 4.1 Wavelog 集成模式

```
┌─────────────────────────────────────────────────────────────┐
│                      Wavelog 主程序                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ MySQL 数据库 │  │ 用户 Session │  │  Theme/CSS          │ │
│  │ - users     │  │             │  │                     │ │
│  │ - stations  │  │             │  │                     │ │
│  │ - qsos      │  │             │  │                     │ │
│  │ - dxcc      │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   DX Guardian (子模块)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 数据读取层   │  │ 认证验证    │  │  界面渲染           │ │
│  │ - MySQL查询  │  │ - Session   │  │  - 复用 Wavelog    │ │
│  │ - 缓存      │  │ - 登录检查  │  │  - 主题一致        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 独立模式

```
┌─────────────────────────────────────────────────────────────┐
│                      独立模式                                │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │ ADIF 文件   │───▶│ ADIF 解析   │───▶│  SQLite 存储    │ │
│  │ (用户配置)  │    │             │    │                 │ │
│  └─────────────┘    └─────────────┘    └────────┬────────┘ │
│                                                  │          │
│  ┌─────────────┐    ┌─────────────┐             │          │
│  │ PSK Reporter│───▶│ Spot 聚合   │◀────────────┘          │
│  │ DX Cluster  │    │ + 去重      │                        │
│  │ POTA/SOTA   │    │             │                        │
│  └─────────────┘    └──────┬──────┘                        │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │  前端展示       │                       │
│                   │  (独立界面)     │                       │
│                   └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、API 设计

### 5.1 REST API 端点

| 方法 | 路径 | 描述 | 模式 |
|------|------|------|------|
| GET | `/api/spots` | 获取去重后的 Spot 列表 | 全部 |
| GET | `/api/spots/merge` | 合并多数据源 Spot | 全部 |
| GET | `/api/solar/current` | 当前太阳活动数据 | 全部 |
| GET | `/api/solar/bands` | 波段推荐 | 全部 |
| GET | `/api/activity/pota` | POTA 激活 | 全部 |
| GET | `/api/activity/sota` | SOTA 激活 | 全部 |
| GET | `/api/activity/wwff` | WWFF 激活 | 全部 |
| GET | `/api/dxpeditions` | DX 远征 | 全部 |
| GET | `/api/user/profile` | 当前用户信息 | Wavelog |
| GET | `/api/user/stations` | 用户电台列表 | Wavelog |
| GET | `/api/user/logs` | QSO 日志统计 | Wavelog |
| GET | `/api/user/dxcc` | 已确认 DXCC | Wavelog |
| GET | `/api/health` | 健康检查 | 全部 |

---

## 六、功能模块对比

### 6.1 两种模式功能差异

| 功能 | Wavelog 集成 | 独立模式 |
|------|-------------|----------|
| 实时 Spot 监控 | ✅ | ✅ |
| 多数据源聚合 | ✅ | ✅ |
| 去重引擎 | ✅ | ✅ |
| 高德地图 | ✅ | ✅ |
| 太阳活动数据 | ✅ | ✅ |
| 传播预测 | ✅ | ✅ |
| POTA/SOTA/WWFF | ✅ | ✅ |
| **用户认证** | Wavelog Session | ❌ 本地 |
| **QSO 日志** | MySQL 实时读取 | ADIF 文件导入 |
| **缺失 DXCC** | 数据库查询 | ADIF 统计 |
| **LoTW 状态** | 数据库查询 | ADIF 注释 |
| **Web Push** | ✅ | ❌（可选） |
| **预警规则** | ✅ 用户级 | ✅ 本地 |

### 6.2 需要保留的模块（补充）

以下模块在 v7.0 MVP 中简化，但在完整版中应保留：

| 模块 | 用途 | 状态 |
|------|------|------|
| `alert_engine_v2.py` | 规则预警引擎 | 补充 |
| `push_routes.py` | Web Push 推送 | 补充 |
| `scorer.py` | 机会评分系统 | 补充 |
| `band_opening.py` | 波段开启预测 | 保留/增强 |
| `lotw_loader.py` | LoTW 状态加载 | 补充 |
| `log_analyzer.py` | 日志分析 | 补充 |

---

## 七、数据库设计

### 7.1 Wavelog 集成模式（直接读取）

| Wavelog 表 | 用途 |
|-----------|------|
| `users` | 用户信息 |
| `stations` | 电台配置 |
| `qsos` | QSO 日志 |
| `qso_details` | QSO 详情 |
| `dxcc_entities` | DXCC 实体 |
| `lotw_users` | LoTW 用户 |

### 7.2 独立模式（SQLite）

```python
@dataclass
class SpotActivity:
    callsign: str
    frequency: float
    mode: str
    band: str
    grid: Optional[str]
    timestamp: datetime
    snr: Optional[float]
    source: str
    activity_type: Optional[str]
    comments: Optional[str]
```

---

## 八、分阶段开发计划

### MVP 1：网站框架 + 实时 DX Spot（P0，预计 2-3 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 1.1 | 项目初始化 + config.yaml 模板 | 0.5h |
| 1.2 | 配置加载模块 | 0.5h |
| 1.3 | PSK Reporter 数据接入 | 1h |
| 1.4 | 前端页面 + Spot 列表 | 1h |
| 1.5 | 太阳活动面板 | 0.5h |

### MVP 2：配置系统 + 双模式基础（P0，预计 2-3 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 2.1 | YAML 配置解析 | 0.5h |
| 2.2 | Wavelog 数据库连接 | 1h |
| 2.3 | ADIF 文件读取 | 1h |
| 2.4 | 模式切换逻辑 | 0.5h |

### MVP 3：多数据源 + 去重（P0，预计 3-4 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 3.1 | DX Cluster Telnet | 1.5h |
| 3.2 | POTA/SOTA/WWFF | 1h |
| 3.3 | 去重引擎 | 1h |
| 3.4 | 缓存策略 | 0.5h |

### MVP 4：地图增强 + 高级功能（P1，预计 3-4 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 4.1 | 高德地图集成 | 1h |
| 4.2 | Grid 坐标转换 | 0.5h |
| 4.3 | 波段推荐 | 0.5h |
| 4.4 | 预警规则引擎 | 1h |
| 4.5 | 机会评分 | 1h |

---

## 九、文件结构

```
# Wavelog 集成模式（前后端分开部署）
wavelog/
├── application/
├── assets/
├── dx_frontend/                    # 前端（可独立部署）
│   ├── config.js                   # 前端配置（API 地址等）
│   ├── index.html
│   ├── css/
│   └── js/
├── dx_guardian/                    # 后端
│   ├── config.yaml                 # 后端配置
│   ├── backend/
│   │   ├── app.py
│   │   ├── config_loader.py
│   │   └── ...
│   └── data/
└── ...

# 独立模式
dx_guardian/
├── config.yaml                     # 配置文件
├── backend/
│   ├── app.py
│   ├── config_loader.py
│   ├── services/
│   │   ├── adif_parser.py
│   │   └── ...
│   └── modules/
├── frontend/                       # 前端
│   ├── config.js                   # 前端配置
│   ├── index.html
│   ├── css/
│   └── js/
└── data/
    └── input/
        └── my_log.adif
```

### 前端配置文件 (config.js)

前端通过 `config.js` 配置后端连接信息：

```javascript
// frontend/config.js
window.DX Guardian_CONFIG = {
    apiUrl: 'http://localhost:5001',
    refreshInterval: 300000,
    mapProvider: 'amap',
    amap: {
        key: 'YOUR_AMAP_KEY',
        securityCode: 'YOUR_SECURITY_CODE'
    }
};
```

# 独立模式
dx_guardian/
├── config.yaml                     # 配置文件
├── backend/
│   ├── app.py
│   ├── config_loader.py
│   ├── services/
│   │   ├── adif_parser.py          # ADIF 解析
│   │   └── ...
├── frontend/
└── data/
    └── input/
        └── my_log.adif             # 用户日志文件
```

---

## 十、注意事项

### 10.1 Wavelog 集成模式

- **只读引用**：不修改 Wavelog 任何源码
- **独立目录**：模块代码放在 `dx_guardian/` 独立目录
- **数据隔离**：用户数据存储在 Wavelog 数据库
- **认证复用**：使用 Wavelog Session 验证

### 10.2 独立模式

- **ADIF 路径**：通过配置文件指定，不内置
- **本地存储**：使用 SQLite
- **无认证**：默认单用户本地使用

### 10.3 前端独立部署

前端可以独立部署，通过配置文件连接后端：

```javascript
// frontend/config.js
// 前端配置文件

window.DX Guardian_CONFIG = {
    // 后端 API 地址（必填）
    // 部署时修改为实际后端地址
    apiUrl: 'http://localhost:5001',
    
    // WebSocket 地址（可选）
    // 如果不配置，使用 HTTP 轮询
    // wsUrl: 'ws://localhost:5001/ws',
    
    // 刷新间隔（毫秒）
    refreshInterval: 300000,  // 5分钟
    
    // 地图类型：'amap' | 'leaflet'
    mapProvider: 'amap',
    
    // 高德地图配置
    amap: {
        key: 'YOUR_AMAP_KEY',
        securityCode: 'YOUR_SECURITY_CODE'
    },
    
    // Leaflet 配置
    leaflet: {
        tileServer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
    }
};
```

**部署步骤**：
1. 拷贝 `frontend/` 目录到目标位置
2. 修改 `config.js` 中的 `apiUrl` 为实际后端地址
3. 访问 index.html 即可

**Wavelog 集成示例**：
```
wavelog/
├── application/
├── assets/
├── dx_frontend/          # 前端独立目录
│   ├── index.html
│   ├── config.js         # 修改 apiUrl 即可
│   ├── css/
│   └── js/
└── dx_guardian/          # 后端
    ├── backend/
    └── config.yaml

---

## 十一、技术栈

### 11.1 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 后端语言 |
| Flask | 3.0+ | Web 框架 |
| PyYAML | 6.0+ | 配置文件解析 |
| pymysql / sqlite3 | - | 数据库 |
| requests | 2.31+ | HTTP 客户端 |

### 11.2 前端

| 技术 | 用途 |
|------|------|
| 原生 HTML/CSS/JS | 页面结构 |
| 高德地图 JS API | 地图渲染 |

---

**文档维护**: 本计划书为开发的唯一依据，所有开发工作必须严格按照此计划执行。

> 更新记录：
> - v7.0 (2026-05-09): 增加双模式支持、Wavelog 配置文件（YAML）、补充缺失功能模块