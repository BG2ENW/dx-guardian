# DX Guardian - 开发计划书 v8.0（多数据源实时 DX Cluster）

> 版本：v8.0
> 日期：2026-05-10
> 基于：v7.1 重大修订
> 修订内容：预测公式修正（确定性 SNR → MUF 波段开通模型）、MVP 依赖重排、数据库补全、API 合并、去重去残
> 呼号：BG2ENW | 位置：PN35HS（哈尔滨）

---

## 一、项目定位

> **多数据源实时 DX Spot 聚合 + 通联概率预测 + 全球电台地图 + 传播条件分析**
> 支持两种运行模式：Wavelog 深度集成模式 或 独立模式

---

## 二、运行模式

### 2.1 模式概述

| 模式 | 说明 | 数据来源 | 用户认证 |
|------|------|----------|----------|
| **Wavelog 集成模式** | 作为 Wavelog 子模块运行 | Wavelog MySQL 数据库 | 🔒 需另设计（见 2.4） |
| **独立模式** | 完全独立运行 | ADIF 文件导入 | 无（单用户本地） |

### 2.2 目录结构

```
# Wavelog 集成模式
wavelog/
├── application/
├── assets/
├── dx_guardian/                    # 后端（Flask）
│   ├── config.yaml
│   ├── backend/
│   │   ├── start.py
│   │   ├── config_loader.py
│   │   ├── prediction/
│   │   │   ├── link_budget.py      # 链路余量
│   │   │   ├── history_matcher.py  # 历史匹配
│   │   │   ├── grayline.py         # 灰线计算
│   │   │   └── muf.py              # MUF 计算
│   │   ├── services/
│   │   │   ├── psk_reporter.py
│   │   │   ├── dx_cluster.py
│   │   │   ├── pota_sota.py
│   │   │   ├── noaa_fetcher.py
│   │   │   ├── adif_parser.py
│   │   │   └── dedup.py
│   │   └── routes/
│   └── data/
│       └── dx_guardian.db          # SQLite（反馈/缓存/配置）
└── dx_frontend/                    # 前端（纯 HTML/CSS/JS）
    ├── index.html
    ├── config.js
    ├── css/
    └── js/

# 独立模式
dx_guardian/
├── config.yaml
├── backend/
├── frontend/
└── data/
    └── input/
        └── my_log.adif
```

### 2.3 数据库策略

| 数据类型 | Wavelog 模式 | 独立模式 |
|---------|-------------|---------|
| QSO 日志 | 读取 Wavelog MySQL | ADIF → SQLite |
| 用户配置 | Wavelog MySQL 或 SQLite | SQLite |
| 反馈记录 | SQLite（独立表） | SQLite |
| 缓存数据 | SQLite | SQLite |
| 太阳数据 | SQLite 缓存 | SQLite 缓存 |

**说明**：两种模式内部都使用 SQLite 作为本地数据层（反馈/配置/缓存），区别仅在于 QSO 来源。

### 2.4 Wavelog 认证说明（待实现时确定方案）

PHP Session 直接读取存在跨语言兼容问题（文件格式/序列化/路径）。以下方案二选一，**实现时再决定**：

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **内嵌代理** | 前端通过 Wavelog PHP 页面代理 API 请求 | 零改动 Wavelog | 多一层代理 |
| **API Key** | DX Guardian 独立认证，用户手动填 Key | 彻底解耦 | Wavelog 需加 Key 生成 |

> MVP 阶段优先使用独立模式开发，Wavelog 集成模式作为 Phase 2。

---

## 三、配置文件（YAML）

### 3.1 完整配置

```yaml
# DX Guardian 配置文件 v8.0

# ==================== 运行模式 ====================
mode: "standalone"  # wavelog | standalone

# ==================== Wavelog 集成配置 ====================
wavelog:
  root_path: "/home/jacky/.openclaw/workspace/apps/wavelog"
  database:
    host: "localhost"
    port: 3306
    user: "wavelog"
    password: "your_password"
    name: "wavelog"
  sync:
    qso_interval: 5          # 分钟

# ==================== 独立模式配置 ====================
standalone:
  adif:
    file_path: "/path/to/your/log.adif"
    additional_files: []
    auto_reload: true
  database:
    path: "./data/dx_guardian.db"
  user:
    callsign: "BG2ENW"
    grid: "PN35HS"
    lat: 45.8
    lon: 126.5

# ==================== 数据源配置 ====================
datasources:
  pskreporter:
    enabled: true
    query_interval: 310       # ≥300 秒（PSK Reporter 限制）
    contact_email: "bg2enw@163.com"
    max_results: 200
  
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
  
  pota:
    enabled: true
    refresh_interval: 900
  sota:
    enabled: true
    refresh_interval: 900
  wwff:
    enabled: true
    refresh_interval: 900

# ==================== 太阳数据 ====================
solar:
  noaa_base_url: "https://services.swpc.noaa.gov/json/"
  # 拉取的具体文件：
  # - solar_wind_1h.json    (太阳风速/Bz/Bt)
  # - planetary_k_index_1m.json (K-index)
  # - f107_cm_flux.json     (SFI/F10.7)
  # - goes_xray_flux_1m.json (X-ray)
  refresh_interval: 600       # 10分钟
  cache_ttl: 600

# ==================== 服务器 ====================
server:
  host: "0.0.0.0"
  port: 5001
  debug: false

# ==================== 前端 ====================
frontend:
  refresh_interval: 300000    # 5分钟（毫秒）
  leaflet:
    tile_server: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

# ==================== 应用配置 ====================
app:
  dedup:
    time_window: 300          # 5分钟去重窗口
    key_format: "callsign_frequency_mode"
  cache:
    spots_ttl: 300
    solar_ttl: 600
    activity_ttl: 900
  logging:
    level: "INFO"
    file: "./logs/dx_guardian.log"
```

### 3.2 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `mode` | 是 | `wavelog` 或 `standalone` |
| `standalone.adif.file_path` | 独立模式 | ADIF 文件路径 |
| `standalone.user.callsign` | 独立模式 | 自己的呼号 |
| `datasources.pskreporter.contact_email` | 是 | PSK Reporter API 要求 |
| `datasources.*.enabled` | 是 | 是否启用该数据源 |
| `server.port` | 是 | Flask 端口 |

---

## 四、数据流程（含预测引擎）

```
                          ┌──────────────────┐
                          │   NOAA SWPC       │
                          │ SFI / K / Xray    │
                          └────────┬─────────┘
                                   │
  ┌──────────────┐          ┌─────▼─────┐
  │ PSK Reporter │─────────▶│           │
  │ DX Cluster   │─────────▶│ 聚合+去重  │──▶ Spot 列表
  │ POTA/SOTA    │─────────▶│           │
  └──────────────┘          └─────┬─────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                    │
        ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
        │ MUF 计算   │      │ 链路余量  │      │ 历史匹配  │
        │ (SFI+距离) │      │ (功率+天线│      │ (ADIF日志)│
        └─────┬─────┘      │  +馈线)   │      └─────┬─────┘
              │            └─────┬─────┘            │
              └──────────────────┼──────────────────┘
                                 │
                          ┌──────▼──────┐
                          │  概率评分    │
                          │ MUF×0.45    │
                          │ +链路×0.30  │
                          │ +历史×0.25  │
                          └──────┬──────┘
                                 │
                    ┌────────────▼────────────┐
                    │ 前端展示 + 反馈录入     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  SQLite 反馈表 (学习)   │
                    └─────────────────────────┘
```

---

## 五、API 设计（完整合并版）

### 5.1 所有端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查（呼号/格网/可见电台/今日Spot数） |
| GET | `/api/spots` | 去重后的 Spot 列表 |
| GET | `/api/solar/current` | 当前太阳活动数据 |
| GET | `/api/solar/bands` | 各波段状态（MUF 推荐） |
| GET | `/api/activity/pota` | POTA 激活列表 |
| GET | `/api/activity/sota` | SOTA 激活列表 |
| GET | `/api/activity/wwff` | WWFF 激活列表 |
| GET | `/api/trends` | 频段趋势统计 |
| GET | `/api/propagation` | 传播条件总览 |
| **预测相关** |
| GET | `/api/prediction/spots` | 带通联概率的 Spot 列表 |
| GET | `/api/prediction/single?callsign=X&freq=Y&grid=Z` | 单台通联概率计算 |
| GET | `/api/prediction/grayline` | 灰线数据（含最近 Spot 路径） |
| POST | `/api/prediction/feedback` | 提交通联结果反馈 |
| GET | `/api/prediction/history` | 预测正确率历史 |
| **用户配置** |
| GET | `/api/user/config` | 获取当前用户电站配置 |
| POST | `/api/user/config` | 保存用户电站配置 |
| GET | `/api/user/stats` | 用户通联统计摘要 |

### 5.2 重点接口说明

**POST `/api/prediction/feedback`** — 提交通联结果反馈
```json
{
  "spot_id": "JA1AAA_14074_FT8",
  "result": "success",          // success | failed | no_signal
  "actual_snr": "+5",           // 可选，实际收到 SNR
  "comment": "信号很强"
}
```

**POST `/api/user/config`** — 保存用户电站配置
```json
{
  "power": 100,
  "antenna_type": "DP",
  "antenna_height": 10,
  "feedline_type": "RG-213",
  "feedline_length": 30,
  "grid": "PN35HS",
  "environment": "suburb"
}
```

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
| **通联概率预测** | ✅ | ✅ |
| POTA/SOTA/WWFF | ✅ | ✅ |
| 用户认证 | Wavelog（待定） | ❌ 本地 |
| QSO 日志 | MySQL 实时读取 | ADIF 文件导入 |
| 缺失 DXCC | 数据库查询 | ADIF 统计 |
| 预警规则 | ✅ 用户级 | ✅ 本地 |

### 6.2 模块演进

以下模块随版本逐步启用：

| 模块 | 用途 | MVP 版本 |
|------|------|---------|
| `muf.py` | MUF/波段开通计算 | MVP2 |
| `link_budget.py` | 链路余量计算 | MVP2 |
| `history_matcher.py` | 历史 QSO 匹配 | MVP2 |
| `grayline.py` | 灰线路径计算 | MVP2 |
| `noaa_fetcher.py` | 太阳数据拉取 | MVP1 |
| `pskreporter.py` | PSK Reporter 接入 | MVP1 |
| `dedup.py` | Spot 去重 | MVP1 |
| `adif_parser.py` | ADIF 解析 | MVP3 |
| `alert_engine_v2.py` | 预警引擎 | MVP5 |

---

## 七、通联概率预测系统（v8.0 修订）

### 7.1 预测思路

> **旧思路（v7.1，已废弃）：** 用确定性 SNR 链路方程计算到场信号强度。
> **问题：** 电离层传播是概率性的（MUF 到了就通、没到不通），不是"增益+dB"的卫星链路。
> 且公式缺少频率/模式依赖，接收方噪声不可知。

> **新思路（v8.0）：** 分三步判断 ——
> 1. **波道通不通？**（MUF ≥ 频率？灰线加成？K 抑制？）
> 2. **通了之后你够不够？**（链路余量 vs 模式门限）
> 3. **你以前在这条件下成功过吗？**（历史 QSO 匹配）

### 7.2 核心公式（v8.0）

```
if 频率 > MUF_effective:
    通联概率 = 0%                    // 波道根本不通
else:
    MUF 分 = (MUF_effective - 频率) / max(MUF_margin, 5)   // 波道余量
    链路分 = (链路余量 - 模式门限) / max(20, 链路余量范围)  // 归一化到 0~1
    历史分 = 该组合条件下是否有历史 QSO ? 1.0 : 0.3        // 2选1

    通联概率 = MUF分 × 0.45  +  链路分 × 0.30  +  历史分 × 0.25
    最终概率 = clip(概率, 0%, 100%)
```

**各项说明：**

| 项 | 权重 | 来源 | 说明 |
|----|------|------|------|
| MUF 分 | 45% | MUF(SFI, SSN, 大圆路径中点) | 波道是否开通是第一位 |
| 链路分 | 30% | EIRP - 传播损耗 - 噪声基底 vs 模式门限 | 设备够不够 |
| 历史分 | 25% | QSO 日志同频段/距离匹配 | 有经验加权 |

### 7.3 MUF 计算（muf.py）

**输入：** SFI (F10.7)、SSN、路径中点经纬度、当前 UTC
**公式：** 使用 ITU-R P.533 推荐的简化 MUF 公式

```
foF2 = f(SFI, SSN, 月份, 纬度)    // F2 层临界频率
MUF = foF2 × 路径中点 M-factor   // M 因子（距离+仰角修正）
MUF_effective = MUF × (1 - K_index × 0.1)  // K-index 压制
                + grayline_bonus            // 灰线时段 +10%
```

**输出：**
- 目标路径的 MUF（MHz）
- 各个波段状态：MUF >= 频率 ? 🟢开通 : 🔴不开
- 灰线加成标记

### 7.4 链路余量计算（link_budget.py）

**步骤：**

```
1. EIRP = PWR(dBm) + Ant_Gain(dBi) - Feedline_Loss(dB, freq)
   
   馈线损耗查表（按频率不同）：
   | 频段   | RG-58 | RG-213 | LMR-400 |
   |--------|-------|--------|---------|
   | 3.5MHz | 0.4   | 0.3    | 0.2     |  (dB/30m)
   | 7MHz   | 0.6   | 0.4    | 0.2     |
   | 14MHz  | 0.9   | 0.6    | 0.3     |
   | 21MHz  | 1.1   | 0.7    | 0.4     |
   | 28MHz  | 1.3   | 0.8    | 0.5     |

2. 传播损耗 = 简化的 HF 传播经验公式：
   （不用 FSPL，HF 传播不是视距）
   Loss = 100 + 20×log10(d_km) + freq_dependent_factor
   freq_dependent_factor: 3.5MHz→0, 28MHz→+18dB

3. 接收端噪声基底（按环境+频段+UTC时段）：
   郊区/14MHz/白天 ≈ -115 dBm
   城市/7MHz/夜晚  ≈ -95 dBm

4. 链路余量 = EIRP - 传播损耗 - 噪声基底
```

**输出：**
- 链路余量 (dB)
- 模式门限对比（FT8=-20dB, FT4=-17dB, CW=-10dB, SSB=+0dB）
- 限制因素提示

### 7.5 模式 SNR 门限

不同模式需要的最低 SNR 完全不同：
| 模式 | 门限 (dB) | 说明 |
|------|----------|------|
| FT8 | -20 | 最灵敏 |
| FT4 | -17 | 次灵敏 |
| CW | -10 | 靠人耳 |
| SSB | 0 | 需要明显信号 |
| RTTY | -5 | 中等 |

> 链路余量 < 模式门限 → 即使波段开通也很难通联

### 7.6 硬件参数（固定选项，不变）

| 参数 | 选项 | 默认 |
|------|------|------|
| 功率 | 5W / 10W / 25W / 50W / 100W / 200W / 500W / 1000W / 1500W | 100W |
| 天线类型 | DP / GP / Yagi3 / Yagi5 / Yagi7 / HB9CV / Quad / Loop / 长线 / 车载鞭 / 其他 | DP |
| 天线增益 | 自动匹配（dBi）：DP=2.5, GP=2.0, Yagi3=6, Yagi5=8, Yagi7=10, HB9CV=5.5, Quad=7, Loop=3, 长线=2, 车载鞭=-2, 其他=0 | - |
| 天线架高 | 5m / 8m / 10m / 12m / 15m / 18m / 20m / 25m / 30m | 10m |
| 馈线型号 | RG-58 / RG-213 / LMR-200 / LMR-400 / LMR-600 / 特富龙-5 / 特富龙-7 | RG-213 |
| 馈线长度 | 10m / 15m / 20m / 25m / 30m / 40m / 50m / 60m / 80m / 100m | 30m |
| 位置格网 | 标准 6 字符输入 | PN35HS |
| 环境 | 城市 / 郊区 / 野外 | 郊区 |

**注：天线增益值已修正（GP 从 1.0→2.0）；去掉了 RG-214/RG-58（低频段几乎一样）和 特富龙-3（合并）。**

### 7.7 基础数据源

| 数据 | 来源 | 更新间隔 | 用途 |
|------|------|---------|------|
| SFI (F10.7) | NOAA SWPC `f107_cm_flux.json` | 1天（每日值） | MUF 计算基础 |
| SSN | NOAA SWPC | 1天 | MUF 长期趋势 |
| K-index | NOAA SWPC `planetary_k_index_1m.json` | 3分钟 | MUF 地磁压制 |
| A-index | NOAA SWPC | 3小时 | 累积地磁影响 |
| X-ray flux | NOAA SWPC `goes_xray_flux_1m.json` | 1分钟 | D层吸收告警 |
| 太阳风速/Bz | NOAA SWPC `solar_wind_1h.json` | 1小时 | 磁暴前兆 |
| Spot SNR/Grid | PSK Reporter | 实时 | 实际通路验证 |
| 用户日志 | ADIF / Wavelog MySQL | 按需 | 历史匹配 |
| 位置/时间 | 用户输入 + 系统时钟 | - | MUF + 灰线 |

### 7.8 历史匹配引擎（history_matcher.py）

**实际能做到的：** ADIF 只记录成功通联，不记录失败尝试。因此不是算"成功率"，而是**二元匹配**。

匹配逻辑（查询 SQLite / MySQL）：
```sql
-- 是否有该频段 QSO？
SELECT COUNT(*) FROM qsos 
WHERE band = ? 
  AND distance_km BETWEEN ? - 500 AND ? + 500
  AND ABS(MONTH(qso_date) - ?) <= 1  -- 同季节±1月
```

输出：
- `matched`: true/false — 该条件下是否有成功记录
- `match_count`: 匹配到的 QSO 数
- `match_examples`: 最近 3 条匹配 QSO（呼号/日期/频段）
- `missing_dxcc`: 该 DXCC 是否还没通过（缺失 DXCC 加权）

### 7.9 历史 QSO 太阳数据补全

ADIF 导入后，对于每条 QSO，通过日期反查 NOAA 历史数据补全到本地：
- 从 `SWPC` 获取历史 SFI/SSN/K-index
- 用 `pyephem` 反算 QSO 时刻的灰线状态
- 存到本地 SQLite 的 `qso_solar` 关联表

> 工作量评估：1万条 QSO × NOAA 批量查询，约 5-10 分钟（含 API 限速）
> 如 NOAA 历史不可获取，降级为：只用频段/距离/月份匹配，不加 SFI/K 维度

### 7.10 前端展示

```
┌─────────────────────────────────────────────────────┐
│ JA1AAA    14.074 MHz  FT8   [72% 🟢]   12:34:56    │
│    MUF 22MHz > 14MHz ✅ | 链路余量+8dB | 历史:有记录│
│    📍 PM95 (距你 2100km)   🌅 灰线经过              │
│    📊 MUF分:85  链路分:60  历史分:100               │
└─────────────────────────────────────────────────────┘
```

概率颜色：
- 🟢 ≥70%：波段开通 + 设备够 + 历史有——建议呼叫
- 🟡 30-70%：某项不足，可尝试
- 🔴 <30%：波段不开或设备严重不足——不建议

### 7.11 学习闭环

1. 用户在 Spot 上点"✅ 通了"或"❌ 没通"
2. 系统记录：通联时间、实际结果、当时 SFI/K/频段/距离
3. 存入 `feedback_records` 表
4. 预测时检索最近 90 天反馈——调整历史匹配权重
5. 模式门限根据实际反馈动态微调（如：FT8 你实际需要 -15dB 而不是 -20dB）

### 7.12 预测配置

```yaml
prediction:
  enabled: true
  muf:
    k_suppression: 0.1         # K-index 每级降低 10% MUF
    grayline_bonus_pct: 10     # 灰线加成 10%
    min_margin_mhz: 2          # 最小 MUF 余量（MHz）
  link_budget:
    noise_floor:               # dBm，按环境+频段
      city: {low: -95, mid: -105, high: -115}
      suburb: {low: -105, mid: -115, high: -125}
      rural: {low: -115, mid: -125, high: -135}
    mode_thresholds:           # dB，模式最低 SNR
      FT8: -20
      FT4: -17
      CW: -10
      SSB: 0
  history:
    weight_limit: 0.25
    min_samples: 1             # 有 1 条以上即参与
    distance_tolerance_km: 500
  feedback:
    enabled: true
    decay_days: 90
```

---

## 八、数据库设计

### 8.1 表结构（SQLite / Wavelog MySQL 对照）

#### 独立模式 SQLite 表

```sql
-- 用户电站配置
CREATE TABLE user_config (
    id INTEGER PRIMARY KEY,
    power_w INTEGER DEFAULT 100,
    antenna_type TEXT DEFAULT 'DP',
    antenna_height_m REAL DEFAULT 10,
    feedline_type TEXT DEFAULT 'RG-213',
    feedline_length_m REAL DEFAULT 30,
    grid TEXT DEFAULT 'PN35HS',
    environment TEXT DEFAULT 'suburb',
    updated_at TEXT
);

-- ADIF 导入的 QSO
CREATE TABLE adif_qsos (
    id INTEGER PRIMARY KEY,
    callsign TEXT NOT NULL,
    band TEXT,                    -- 20m, 40m...
    freq_mhz REAL,
    mode TEXT,                    -- FT8, CW, SSB...
    qso_date TEXT,                -- YYYY-MM-DD
    qso_time TEXT,                -- HH:MM
    grid TEXT,
    dxcc TEXT,
    distance_km REAL,
    created_at TEXT
);

-- QSO 太阳数据补全（关联 adif_qsos）
CREATE TABLE qso_solar (
    qso_id INTEGER PRIMARY KEY REFERENCES adif_qsos(id),
    sfi REAL,                     -- 补全的 SFI
    ssn INTEGER,                  -- 补全的 SSN
    k_index REAL,                 -- 补全的 K-index
    grayline BOOLEAN,             -- 灰线状态
    filled_at TEXT                -- 补全时间
);

-- 通联反馈记录
CREATE TABLE feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_callsign TEXT NOT NULL,  -- 对方呼号
    frequency_mhz REAL,           -- 频率
    mode TEXT,                    -- 模式
    band TEXT,                    -- 频段
    result TEXT NOT NULL,         -- success / failed / no_signal
    predicted_prob REAL,          -- 当时预测的概率
    actual_snr REAL,              -- 实际 SNR（如有）
    sfi REAL,                     -- 反馈时的 SFI
    k_index REAL,                 -- 反馈时的 K-index
    distance_km REAL,             -- 距离
    user_power_w INTEGER,         -- 用户当时功率
    user_antenna TEXT,            -- 用户当时天线
    created_at TEXT DEFAULT (datetime('now'))
);

-- 预测日志
CREATE TABLE prediction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_callsign TEXT,
    frequency_mhz REAL,
    mode TEXT,
    muf_score REAL,
    link_score REAL,
    history_score REAL,
    final_prob REAL,
    sfi REAL,
    k_index REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 太阳数据缓存
CREATE TABLE solar_cache (
    key TEXT PRIMARY KEY,         -- sfi / k_index / ssn / xray...
    value REAL,
    updated_at TEXT
);

-- Spot 去重缓存（内存为主，SQLite 备灾）
CREATE TABLE spot_cache (
    dedup_key TEXT PRIMARY KEY,
    callsign TEXT,
    frequency REAL,
    mode TEXT,
    grid TEXT,
    snr REAL,
    source TEXT,
    timestamp TEXT,
    expires_at TEXT
);
```

#### Wavelog 集成模式（直接读 MySQL）

| Wavelog 表 | 读取字段 | DX Guardian 用途 |
|-----------|---------|-----------------|
| `qsos` | COL_CALL, COL_BAND, COL_FREQ, COL_MODE, COL_TIME_ON, COL_GRIDSQUARE, COL_DXCC | 历史匹配 |
| `stations` | station_gridsquare | 默认位置 |
| `dxcc_entities` | name, prefix | DXCC 查询 |

### 8.2 数据流

```
独立模式:
  ADIF 文件 → adif_parser.py → adif_qsos 表
  adif_qsos → qso_solar 补全（NOAA 历史数据）→ qso_solar 表
  history_matcher.py ← adif_qsos + qso_solar

Wavelog 模式:
  MySQL qsos 表 → history_matcher.py 直接查询
  （前提：Wavelog 版本已有 band/distance 字段或可计算）
```

---

## 九、前端设计

### 9.1 技术栈

| 技术 | 用途 |
|------|------|
| 原生 HTML/CSS/JS | 页面结构与交互 |
| Leaflet + OSM | 地图渲染（免费） |
| `pyephem` 或 `suncalc.js` | 灰线计算（前端） |

### 9.2 五个 Tab

| Tab | 内容 | 数据来源 |
|-----|------|---------|
| 实时 | Spot 列表 + 通联概率（颜色+百分比） | `/api/prediction/spots` |
| 传播 | 各波段 MUF 状态 + 灰线地图 | `/api/propagation` + `/api/prediction/grayline` |
| 趋势 | 24h 频段热度趋势 | `/api/trends` |
| 预警 | 用户规则触发列表 | `/api/...` (MVP5) |
| 设置 | 电站配置表单（下拉选项） | `/api/user/config` |

### 9.3 前端配置（config.js）

```javascript
// frontend/config.js
window.DXGuardian_CONFIG = {
    apiUrl: 'http://localhost:5001',
    refreshIntervalMs: 300000,
    leaflet: {
        tileServer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        defaultCenter: [45.8, 126.5],  // PN35HS
        defaultZoom: 5
    },
    callsign: 'BG2ENW',
    grid: 'PN35HS'
};
```

### 9.4 主题

适配 Wavelog Darkly 暗色风格，单一主题（不搞多套）。参考现有 `css/style.css`。

---

## 十、分阶段开发计划（修正依赖顺序）

### MVP 1：网站框架 + 基础数据（P0，3-4 小时）

| 序号 | 任务 | 说明 |
|------|------|------|
| 1.1 | 项目初始化 + config.yaml 模板 | 配置文件 + 加载模块 |
| 1.2 | Flask API 框架 | 基础路由 + 健康检查 |
| 1.3 | NOAA 太阳数据拉取 | `noaa_fetcher.py`，存 solar_cache |
| 1.4 | 前端页面框架 | 5 Tab 骨架 + 暗色主题 |
| 1.5 | 太阳活动面板 | 前端展示 SFI/K/Xray |

### MVP 2：单数据源 + Spot 列表（P0，2-3 小时）

| 序号 | 任务 | 说明 |
|------|------|------|
| 2.1 | PSK Reporter 接入 | 按格网查询，解析 JSON |
| 2.2 | 去重引擎 | callsign_frequency_mode 去重 |
| 2.3 | WebSocket 或 SSE 推送 | 实时 Spot 更新到前端 |
| 2.4 | Spot 列表前端 | 表格 + 搜索 + 排序 |

### MVP 3：QSO 日志接入（P0，3-4 小时）

| 序号 | 任务 | 说明 |
|------|------|------|
| 3.1 | ADIF 解析器 | `adif_parser.py`，存 adif_qsos |
| 3.2 | QSO 太阳数据补全 | NOAA 历史反查，存 qso_solar |
| 3.3 | Wavelog MySQL 只读连接 | pymysql，查询 qsos 表 |
| 3.4 | 模式和距离计算 | 从 GRIDSQUARE 算距离、分频段 |

### MVP 4：通联概率预测引擎（P0，4-6 小时）

| 序号 | 任务 | 说明 |
|------|------|------|
| 4.1 | MUF 计算模块 | ITU-R P.533 简化版 |
| 4.2 | 链路余量计算 | 频率相关馈线损耗 + 噪声基底 + 模式门限 |
| 4.3 | 历史匹配引擎 | QSO 数据库查询（频段+距离+季节） |
| 4.4 | 概率评分 API | 合并 MUF×0.45 + 链路×0.30 + 历史×0.25 |
| 4.5 | 灰线计算 | `suncalc.js` 前端或 `pyephem` 后端 |
| 4.6 | 预测 Spot 列表端点 | `/api/prediction/spots` |

### MVP 5：多源 + 地图 + 前端完善（P1，4-6 小时）

| 序号 | 任务 | 说明 |
|------|------|------|
| 5.1 | DX Cluster Telnet 接入 | 多服务器 + 重连 |
| 5.2 | POTA/SOTA/WWFF | API 拉取 + 展示 |
| 5.3 | Leaflet 地图 | Spot 标记 + 灰线 + 热力图 |
| 5.4 | 通联概率前端展示 | 颜色/百分比/评级理由 |
| 5.5 | 用户配置表单 | 下拉选项 + 保存 API |
| 5.6 | 反馈界面 + 学习闭环 | "通了/没通"按钮 + feedback 表 |

---

## 十一、错误处理与容灾

### 11.1 降级策略

| 故障 | 影响 | 降级方案 |
|------|------|---------|
| NOAA API 宕机 | MUF 算不了 | 用最近缓存数据，标⭐过期 |
| PSK Reporter 限流 | 无新 Spot | 用最近 Spot，标"数据过期" |
| DX Cluster 断连 | 少一个源 | 自动重连，降级用其他源 |
| Wavelog MySQL 不可用 | 无 QSO 历史 | 历史匹配降级为 0（不影响 MUF+链路分） |
| ADIF 文件不存在 | 无 QSO 历史 | 同上 |
| SQLite 写失败 | 反馈存不了 | 前端提示，下次重试 |

### 11.2 前端降级展示

当数据源异常时，前端不崩溃，而是：
- Spot 列表显示"数据更新于 X 分钟前"
- MUF 栏标黄色感叹号 + hover 显示原因
- 概率值降精度（如"72% ± 不确定"）

---

## 十二、测试与验证

### 12.1 单元测试

| 模块 | 测试项 |
|------|--------|
| `muf.py` | 输入 SFI=150/SSN=100/格网→距离 → 验证 MUF 合理范围 |
| `link_budget.py` | 输入 100W/DP/RG-213/30m/14MHz → 验证链路余量 |
| `history_matcher.py` | 输入 500 条测试 ADIF → 验证查询正确 |
| `adif_parser.py` | 标准 ADIF 文件 → 验证字段完整解析 |

### 12.2 预测准确性验证

| 方法 | 做法 |
|------|------|
| **历史回测** | 取最近半年 QSO，检查预测概率 vs 实际结果 |
| **Live 对比** | PSK Reporter 显示的 Spot SNR vs 预测链路余量 |
| **用户反馈** | 统计 `feedback_records` 中 success/total 比率 |

### 12.3 预期目标

- 预测 ≥ 70% 的 Spot，实际成功 ≥ 60%（基线）
- 随着反馈累积，准确率应持续上升
- 标注预测置信度（样本少时低置信）

---

## 十三、注意事项

### 13.1 Wavelog 集成

- **只读引用**：不修改 Wavelog 任何源码
- **独立目录**：`dx_guardian/` 与 Wavelog 代码隔离
- **认证方案待定**：PHP Session 跨语言读取需在实现时评估

### 13.2 独立模式

- ADIF 路径通过配置文件指定
- SQLite 足够，不需要额外数据库
- 不需要用户认证

### 13.3 前端独立部署

前端通过 `config.js` 配置后端地址，可以部署到任意位置：

```javascript
// 修改 apiUrl 即可
window.DXGuardian_CONFIG = {
    apiUrl: 'http://your-server:5001',  // 改为实际后端地址
    // ...
};
```

---

## 十四、技术栈

### 14.1 后端

| 技术 | 用途 |
|------|------|
| Python 3.11+ | 后端语言 |
| Flask 3.0+ | Web 框架 |
| PyYAML | 配置解析 |
| pymysql | Wavelog MySQL 连接 |
| sqlite3 | 本地数据库 |
| requests | HTTP 客户端（NOAA/PSK Reporter） |
| pyephem | 灰线 + MUF 辅助计算 |

### 14.2 前端

| 技术 | 用途 |
|------|------|
| 原生 HTML/CSS/JS | 页面结构 |
| Leaflet + OSM | 地图（免费，无需 API Key） |
| suncalc.js | 前端灰线计算 |

---

> **v8.0 修订摘要：**
> - 预测公式彻底重写（确定性 SNR → MUF+链路余量+历史 三元模型）
> - MVP 顺序重排（预测引擎移到配置+数据源之后）
> - 历史匹配从"成功率"改为"二元匹配"
> - 新增模式 SNR 门限（FT8/CW/SSB 不同）
> - 新增馈线损耗频率依赖表
> - 数据库补全（user_config/feedback_records/prediction_log/qso_solar/solar_cache/spot_cache）
> - API 表合并为单一版本（13 个端点）
> - 去重：config.js 只保留一处，删除重复文件结构
> - 新增降级策略（容灾）和测试验证章节
> - 更新版本号 v7.0 → v8.0
