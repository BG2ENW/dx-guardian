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
| Leaflet 地图 | ✅ | ✅ |
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
| `band_opening.py` | 波段开启预测 | 保留/增强（升级为预测系统核心） |
| `lotw_loader.py` | LoTW 状态加载 | 补充 |
| `log_analyzer.py` | 日志分析 | 补充（升级为历史匹配引擎） |

---

## 七、通联概率预测系统

### 7.1 核心公式

```
估算到场 SNR = 
  发射功率(dBm)             +  // 用户配置, 100W=50dBm, 500W=57dBm
  天线增益(dBi)             +  // 用户配置, DP≈2.5dBi, 三单元Yagi≈6dBi
  - 馈线损耗(dB)            -  // 用户配置, 50米-9电缆≈2.5dB
  - 自由空间路径损耗        -  // = 32.45 + 20log(距离km) + 20log(频率MHz)
  + 电离层增益              +  // SFI + 时段 + 频段 查经验值表
  - 地磁损耗                -  // K-index > 3 时影响, 按路径中纬度加权
  - 噪声基底(dBm)           -  // 城市-100, 郊区-115, 野外-125, 按时段调整

通联概率 = 
  链路概率(SNR vs 噪声基底) × 0.6  +  // 物理链路够不够
  历史匹配概率 × 0.4                    // 相同条件下你成功过没有
```

### 7.2 必须的用户参数（固定选项）

所有硬件参数使用下拉菜单选择，不自由输入。

| 参数 | 选项 | 默认 | 说明 |
|------|------|------|------|
| 功率 | 5W / 10W / 25W / 50W / 100W / 200W / 500W / 1000W / 1500W | 100W | PWR，影响 10log(PWR) |
| 天线类型 | DP（偶极）/ GP（垂直）/ Yagi3（三单元八木）/ Yagi5（五单元八木）/ Yagi7（七单元八木）/ HB9CV / Quad / HB（Δ环）/ Loop / 长线 / GP（地网垂直）/ 车载鞭 / 其他 | DP | 决定增益基础值 |
| 天线增益 | 自动匹配天线类型，不可单独修改：DP=2.5, GP=1, Yagi3=6, Yagi5=8, Yagi7=10, HB9CV=5.5, Quad=7, HB(Δ环)=2, Loop=3, 长线=(按长度计算), GP(地网)=0.5, 车载鞭=-2, 其他=0 | - | 选天线自动带出 |
| 天线架高 | 5m / 8m / 10m / 12m / 15m / 18m / 20m / 25m / 30m | 10m | 影响发射仰角 |
| 馈线型号 | RG-58 / RG-213 / RG-214 / LMR-200 / LMR-400 / LMR-600 / 特富龙(-3) / 特富龙(-5) / 特富龙(-7) | RG-213 | 每米损耗不同 |
| 馈线长度 | 10m / 15m / 20m / 25m / 30m / 40m / 50m / 60m / 80m / 100m | 30m | 影响总损耗 |
| 位置格网 | 标准 Maidenhead 6字符输入 | PN35HS | 大圆路径计算起点 |
| 环境 | 城市 / 郊区 / 野外 | 郊区 | 噪声基底：城市-100dBm, 郊区-115, 野外-125 |

### 7.3 基础数据源

| 数据 | 来源 | 更新 | 用途 |
|------|------|------|------|
| SFI | NOAA SWPC | 10分钟 | 电离层强度基准 |
| SSN | NOAA SWPC | 每日 | 长期趋势 |
| K-index | NOAA SWPC | 3分钟 | 地磁扰动实时值 |
| A-index | NOAA SWPC | 3小时 | 地磁累积影响 |
| X-ray flux | NOAA SWPC | 1分钟 | 突发吸收事件 |
| 太阳风速 | NOAA SWPC | 实时 | 磁暴前兆 |
| Spot SNR/Grid | PSK Reporter | 实时 | 验证传播通路 |
| 用户日志 | ADIF / Wavelog | 按需 | 历史匹配 |

### 7.4 三个核心算法模块

#### 7.4.1 链路预算模块（link_budget.py）

**功能**：计算目标电台的估算到场 SNR

输入：
- 目标电台格网 → 大圆距离
- 目标电台频率/Mode → 频段
- 当前 SFI / K-index / 当前 UTC → 电离层条件
- 用户功率 / 天线增益 / 馈线损耗 → 链路能力

输出：
- 估算 SNR (dB)
- 信心区间 (基于 SFI 值的历史波动范围)
- 限制因素（功率不足 / 频率高 / 地磁强 / 天线差）

#### 7.4.2 历史匹配引擎（history_matcher.py）

**功能**：从用户日志中检索相似条件的通联历史

匹配维度：
1. **频段匹配** —— 同一频段的历史 SNR 统计（平均/中位数/成功率）
2. **距离匹配** —— 相同距离范围（±500km）的历史成功率
3. **太阳条件匹配** —— 相近 SFI（±20）下的历史表现
4. **季节匹配** —— 同月份的通联条件相近

输入：用户 ADIF 或 Wavelog 数据库
输出：
- 该条件下历史成功次数 / 总尝试次数 → 成功率
- 最佳匹配通联示例（条件最接近的 3 个）
- 相似通联的 SNR 分布（25%/50%/75% 分位数）

#### 7.4.3 灰线预测（grayline_predictor.py）

**功能**：预测灰线经过路径上的最佳频段

输入：我的格网 + 目标格网 + 当前 UTC
输出：
- 灰线是否经过或接近通信路径
- 灰线时段内的最佳频段
- 灰线方向指示（日出/日落方向）

### 7.5 前端展示

每个 Spot 需要展示：

```
┌─────────────────────────────────────────────────────┐
│ JA1AAA    14.074 MHz  FT8   [72% 🟢]   12:34:56    │
│    功率充足 | 20m 状态良好 | 历史匹配 4/5 成功      │
│    📍 PM95 (距你 2100km)                            │
│    📊 估计 SNR: +8dB  | 限制: 无                     │
└─────────────────────────────────────────────────────┘
```

概率颜色规则：
- 🟢 ≥70%：链路充足 + 历史可验证，建议呼叫
- 🟡 30-70%：有机会但不确定，可尝试
- 🔴 <30%：链路预算不足或无历史证据，不建议浪费时间

### 7.6 学习闭环

每次通联结果反馈后：
1. 用户标记通联结果（已通联 / 尝试但失败 / 没听到）
2. 系统记录该条件下（SFI/K/频段/距离/功率/天线）的实际 SNR 和结果
3. 更新历史匹配引擎的权重：
   - 成功 → 该条件组合信任权重 +1
   - 失败 → 该条件组合信任权重 -1
4. 下次在相同或相近条件下预测时，结果更准

### 7.7 配置文件新增字段

```yaml
# 通联概率预测配置
prediction:
  enabled: true
  
  # 链路预算系数
  link_budget:
    noise_floor_city: -100        # dBm
    noise_floor_suburb: -115      # dBm
    noise_floor_rural: -125       # dBm
    ionosphere_gain_table: []     # SFI×频率×时段查表
    marginal_snr: -10             # dB，低于此值概率降至 0
  
  # 历史匹配
  history:
    weight_limit: 0.4             # 历史权重上限
    min_samples: 3                # 最少样本数才参与统计
    distance_tolerance_km: 500    # 距离容差
    sfi_tolerance: 20             # SFI 容差
  
  # 反馈学习
  feedback:
    enabled: true
    success_weight: +1
    failure_weight: -1
    decay_interval_days: 90       # 每90天衰减一次权重
```

### 7.8 API 设计（新增）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/prediction/spots` | 返回带通联概率的 Spot 列表 |
| GET | `/api/prediction/calculate?callsign=X&freq=Y` | 手动计算某台通联概率 |
| POST | `/api/prediction/feedback` | 提交通联结果反馈 |
| GET | `/api/prediction/history` | 历史预测正确率统计 |

---

## 八、数据库设计

### 8.1 Wavelog 集成模式（直接读取）

| Wavelog 表 | 用途 |
|-----------|------|
| `users` | 用户信息 |
| `stations` | 电台配置 |
| `qsos` | QSO 日志 |
| `qso_details` | QSO 详情 |
| `dxcc_entities` | DXCC 实体 |
| `lotw_users` | LoTW 用户 |

### 8.2 独立模式（SQLite）

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

## 十、分阶段开发计划

### MVP 1：网站框架 + 实时 DX Spot（P0，预计 2-3 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 1.1 | 项目初始化 + config.yaml 模板 | 0.5h |
| 1.2 | 配置加载模块 | 0.5h |
| 1.3 | PSK Reporter 数据接入 | 1h |
| 1.4 | 前端页面 + Spot 列表 | 1h |
| 1.5 | 太阳活动面板 | 0.5h |

### MVP 2：通联概率预测引擎（P0，新增，预计 4-6 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 2.1 | 用户配置模块（功率/天线/馈线/位置/环境） | 0.5h |
| 2.2 | 链路预算模块（自由空间路径损耗+电离层增益+噪声基底） | 1h |
| 2.3 | ADIF/Wavelog 日志解析+历史匹配引擎 | 1.5h |
| 2.4 | 通联概率评分 API（链路×0.6 + 历史×0.4） | 1h |
| 2.5 | 灰线计算+路径预测 | 1h |
| 2.6 | 学习闭环（通联结果反馈→调整权重） | 1h |

### MVP 3：配置系统 + 双模式基础（P0，预计 2-3 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 3.1 | YAML 配置解析 | 0.5h |
| 3.2 | Wavelog 数据库连接 | 1h |
| 3.3 | ADIF 文件读取 | 1h |
| 3.4 | 模式切换逻辑 | 0.5h |

### MVP 4：多数据源 + 去重（P0，预计 3-4 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 4.1 | DX Cluster Telnet | 1.5h |
| 4.2 | POTA/SOTA/WWFF | 1h |
| 4.3 | 去重引擎 | 1h |
| 4.4 | 缓存策略 | 0.5h |

### MVP 5：地图 + 前端展示（P1，预计 4-6 小时）

| 序号 | 任务 | 预计时间 |
|------|------|----------|
| 5.1 | Leaflet 地图+Spot 标记+热力图灰线 | 1.5h |
| 5.2 | 通联概率在前端的展示（百分比+颜色+评级理由） | 1h |
| 5.3 | 传播路径在地图画线 | 1h |
| 5.4 | 波段推荐面板 | 0.5h |
| 5.5 | 预警规则引擎 | 1h |
| 5.6 | 通联结果反馈界面（成功/失败） | 1h |

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

## 十一、注意事项

### 11.1 Wavelog 集成模式

- **只读引用**：不修改 Wavelog 任何源码
- **独立目录**：模块代码放在 `dx_guardian/` 独立目录
- **数据隔离**：用户数据存储在 Wavelog 数据库
- **认证复用**：使用 Wavelog Session 验证

### 11.2 独立模式

- **ADIF 路径**：通过配置文件指定，不内置
- **本地存储**：使用 SQLite
- **无认证**：默认单用户本地使用

### 11.3 前端独立部署

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

## 十二、技术栈

### 12.1 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 后端语言 |
| Flask | 3.0+ | Web 框架 |
| PyYAML | 6.0+ | 配置文件解析 |
| pymysql / sqlite3 | - | 数据库 |
| requests | 2.31+ | HTTP 客户端 |

### 12.2 前端

| 技术 | 用途 |
|------|------|
| 原生 HTML/CSS/JS | 页面结构 |
| Leaflet（OpenStreetMap） | 地图渲染 |

---

**文档维护**: 本计划书为开发的唯一依据，所有开发工作必须严格按照此计划执行。

> 更新记录：
> - v7.1 (2026-05-10): 新增「通联概率预测系统」章节，含链路预算公式、历史匹配引擎、灰线预测、学习闭环、用户配置参数、前端展示规范、API 设计、配置字段。重新编号后续章节。分阶段开发计划 MVP2 改为预测引擎。
> - v7.0 (2026-05-09): 增加双模式支持、Wavelog 配置文件（YAML）、补充缺失功能模块