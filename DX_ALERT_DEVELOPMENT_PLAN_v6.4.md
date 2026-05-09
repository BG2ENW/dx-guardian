# DX Guardian - 开发计划书 v6.3（完整版）

> 版本：v6.3（含架构决策记录 + PSK Reporter 地图分析）
> 日期：2026-05-06
> 更新：
> - Maidenhead Grid 数据集成功能、Grid 中心点精确定位 ✅
> - JTDX grid_data.bin 二进制格式逆向工程详细说明
> - Grid 数据库解析算法和转换公式
> - 坐标解析 5 级优先级策略
> 呼号：BG2ENW | 位置：PN35HS（哈尔滨）
> 参考目标：dxcontest.org/monitor.html（参考功能形态，不复制代码）

---

## 一、项目定位

> **实时 DX Spot 地图 + 波段活动统计 + 规则预警 + 日志匹配**
> 分阶段交付，每个 MVP 独立可用。

---

## 二、术语修正

| 原表述 | 修正为 | 原因 |
|--------|--------|------|
| 实时QSO流 | **实时 DX Spot 流** | Cluster/RBN 提供的是 Spot（台站活跃报告），不是已完成的通联 |
| 成功率计算 | **机会评分** | 第一版基于规则评分，不承诺准确概率，后续用日志验证 |
| 复制 dxcontest 代码 | **参考功能形态** | dxcontest 无明确开源许可，不直接复制代码/翻译/数据 |

---

## 三、技术栈

### 3.1 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 后端语言 |
| Flask | 3.0+ | Web 框架 |
| Flask-SocketIO | 5.0+ | WebSocket 实时通信 |
| SQLAlchemy | 2.0+ | ORM |
| PyMySQL | 1.1+ | MySQL 驱动 |
| eventlet | 0.33+ | 异步并发 |
| python-socketio | 5.0+ | Socket.IO 服务端 |
| requests | 2.31+ | HTTP 客户端 |
| authlib | 1.3+ | OAuth 支持 |

### 3.2 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Leaflet | 1.9.4 | 地图渲染 |
| Socket.io Client | 4.7+ | WebSocket 客户端 |
| TailwindCSS | 3.4+ | 样式框架 |
| Chart.js | 4.0+ | 统计图表 |

### 3.3 数据存储

| 技术 | 用途 |
|------|------|
| MySQL 8.0+ | 用户数据、配置、日志、预警记录 |
| 内存缓存 | Spot 去重缓存（使用 Python dict + TTL） |
| JSON 文件 | DXCC 前缀库（静态数据） |

### 3.4 不使用的技术（移除）

| 移除项 | 原因 |
|--------|------|
| telnetlib | Python 3.12+ 已废弃，改用 telnetlib3 或原生 socket |
| leaflet-heat | 后置到增强版，MVP 先做基础地图 |
| Web Push API | 后置到增强版，MVP 用浏览器内通知 |
| 10语言国际化 | 后置到增强版，MVP 只做中文+英文结构预留 |

---

## 四、系统架构

### 4.1 系统架构图

```mermaid
graph TB
    subgraph Client["客户端层"]
        Browser[("浏览器")]
        LeafletMap["Leaflet 地图"]
        SocketClient["Socket.io 客户端"]
        NotificationAPI["Notification API"]
    end

    subgraph Backend["后端服务层"]
        FlaskApp["Flask 应用"]
        SocketIO["Flask-SocketIO"]
        ClusterConn["Cluster 连接模块"]
        SpotParser["Spot 解析器"]
        AlertEngine["预警规则引擎"]
        ScoreEngine["机会评分引擎"]
        SolarData["太阳数据模块"]
    end

    subgraph DataLayer["数据层"]
        MySQL[("MySQL 数据库")]
        SpotCache[("Spot 缓存")]
        DXCCData["DXCC 前缀库"]
    end

    subgraph External["外部数据源"]
        ClusterServer["DXSpider Cluster"]
        HamQSL["hamqsl.com"]
        NOAA["NOAA Space Weather"]
        OAuth["GitHub/Google OAuth"]
    end

    Browser <-->|"HTTP/HTTPS"| FlaskApp
    Browser <-->|"WebSocket"| SocketIO
    FlaskApp <-->|"TCP Socket"| ClusterConn
    ClusterConn <-->|"Telnet"| ClusterServer
    FlaskApp <-->|"SQLAlchemy ORM"| MySQL
    SolarData <-->|"HTTP GET"| HamQSL
    SolarData <-->|"HTTP GET"| NOAA
    FlaskApp <-->|"OAuth"| OAuth
```

### 4.2 组件架构图

```mermaid
graph TB
    subgraph API["API 路由层"]
        AuthRoutes["/auth/* 认证路由"]
        UserRoutes["/api/user/* 用户路由"]
        SpotRoutes["/api/spots/* Spot路由"]
        StatsRoutes["/api/stats/* 统计路由"]
        AdminRoutes["/admin/* 管理路由"]
    end

    subgraph Services["业务逻辑层"]
        AuthService["认证服务"]
        UserService["用户服务"]
        SpotService["Spot服务"]
        WatchlistService["关注列表服务"]
        LogService["日志服务"]
        AlertService["预警服务"]
        ScoreService["评分服务"]
    end

    subgraph Workers["后台任务层"]
        ClusterWorker["Cluster连接Worker"]
        SpotDeduplicator["Spot去重Worker"]
        SolarDataWorker["太阳数据Worker"]
        CleanupWorker["清理Worker"]
    end

    subgraph Models["数据模型层"]
        User["User模型"]
        Station["Station配置模型"]
        Watchlist["Watchlist模型"]
        QSOLog["QSO日志模型"]
        Alert["Alert模型"]
    end

    AuthRoutes --> AuthService
    UserRoutes --> UserService
    SpotRoutes --> SpotService
    StatsRoutes --> ScoreService
    UserService --> User
    UserService --> Station
    WatchlistService --> Watchlist
    LogService --> QSOLog
    AlertService --> Alert
    ClusterWorker --> SpotParser
    SpotParser --> SpotDeduplicator
    SpotDeduplicator --> SpotService
    AlertService --> SpotService
```

---

## 五、数据源与异常策略

### 5.1 数据源

| 数据源 | 获取方式 | 更新频率 | 本地缓存 |
|--------|---------|----------|----------|
| hamqsl.com（太阳数据） | HTTP GET | 5分钟 | 缓存5分钟 |
| NOAA（空间天气） | HTTP GET | 1小时 | 缓存1小时 |
| Cluster Telnet | TCP Socket 连接 | 实时 | Spot 缓存（去重用） |
| **PSKReporter** | **HTTP GET（XML）** | **5分钟（310秒）** | **Spot 缓存（去重用）** |
| 用户日志 | ADIF/CSV 文件上传 | 按需 | 本地存储 |

### 5.2 PSKReporter 数据源

**API地址：** `https://retrieve.pskreporter.info/query`

**查询参数：**
| 参数 | 值 | 说明 |
|------|------|------|
| `rptlimit` | 100 | 返回条数（注意：不是 `limit`） |
| `flowStartSeconds` | 当前时间-86400 | 查询起始时间（不超过24小时） |
| `appcontact` | 邮箱 | 官方建议提供 |

**当前实现（2026-04-26）：**
- 查询全球所有接收报告（不限 `senderCallsign`），覆盖更多地区
- 查询间隔 310 秒（遵守官方 ≥5分钟 要求）
- 默认返回100条，最多6小时数据
- XML 解析：`senderCallsign` = 被spot的台（发送台），`callsign` = 接收台
- 429 限流时等待10分钟后重试
- 返回数据转换为统一 Spot 格式，与 Cluster 数据合并去重

**API频率限制注意事项：**
- 官方建议查询间隔 ≥5分钟
- 建议提供 `appcontact` 参数
- 被限流时返回 429，需等待后重试
- 默认返回100条，`flowStartSeconds` 不超过 -86400

### 5.3 Telnet 连接异常策略

```
连接失败 → 等待 5s 重连
第2次失败 → 等待 15s 重连
第3次失败 → 等待 30s 重连
第4次+ → 等待 60s 重连（上限）
连续5次失败 → 记录日志，通知用户，5分钟后重试

登录失败 → 检查呼号格式，3次重试后切换备用服务器
连接断开 → 自动重连（退避策略同上）
心跳检测 → 每60秒发送 keepalive，超时120秒视为断开
```

### 5.4 Cluster 多服务器策略

**服务器列表（按优先级排序）：**
| 优先级 | 服务器 | 位置 |
|--------|--------|------|
| 1 | bh3bbj.rfsec.cn:7373 | 天津（亚洲优先） |
| 2 | dxc.n4zkf.com:7300 | 北美 |
| 3 | k1ttt.net:7300 | 北美 |
| 4 | w3lpl.net:7300 | 北美 |
| 5 | dxc.kf7h.net:7300 | 北美 |
| 6 | dxcc.g7vjr.org:7300 | 欧洲 |
| 7 | dxc.ve3te.net:7300 | 北美 |
| 8 | cluster.dxheat.com:7300 | 欧洲 |

**切换策略：**
- 按优先级顺序尝试连接
- 连接失败自动切换下一台
- 登录失败检查呼号格式，3次重试后切换
- 连接断开按退避策略自动重连

### 5.5 Spot 去重策略

```
去重键：呼号 + 频率（取整到100Hz）+ 时间窗口（5分钟内）
同一呼号同一频率5分钟内只保留最新一条
缓存大小上限：1000条（FIFO淘汰）
```

### 5.6 HTTP 数据源异常策略

```
请求失败 → 重试1次（间隔3秒）
连续失败 → 使用缓存数据（标记为"缓存于 HH:MM"）
缓存过期 → 保留最后一份有效数据，标记为"过期"
所有源不可用 → 显示"数据暂不可用"，不崩溃
```

---

## 六、地图坐标解析策略

Spot 数据只有呼号和频率，没有经纬度。按以下优先级解析坐标：

| 优先级 | 方法 | 精度 | 说明 |
|--------|------|------|------|
| 1 | **Grid 方格** | ~数km | Spot 中若包含 grid（如 PN35HS），直接转换经纬度 |
| 2 | **呼号数据库查询** | ~城市级 | 调用 qrz.com 或 clublog.org API 查询呼号位置 |
| 3 | **DXCC 前缀匹配** | ~国家/区域中心 | 根据呼号前缀匹配 DXCC 实体的中心坐标 |

### 6.1 Maidenhead Grid 转换算法

```python
def grid_to_latlon(grid: str) -> tuple[float, float]:
    """
    将 Maidenhead Grid 转换为经纬度
    格式: FN31pr (6字符) = 字段(18°x18°) + 方格(2°x1°) + 子方格(5'x2.5')
    """
    grid = grid.upper().strip()

    lon_field = ord(grid[0]) - ord('A')
    lat_field = ord(grid[1]) - ord('A')
    lon_sq = int(grid[2])
    lat_sq = int(grid[3])

    lon = (lon_field * 20) + (lon_sq * 2) - 180
    lat = (lat_field * 10) - 90 + lat_sq

    if len(grid) >= 6:
        lon_subsq = ord(grid[4]) - ord('A')
        lat_subsq = ord(grid[5]) - ord('A')
        lon += (lon_subsq * (2 / 24)) - (1 / 24)
        lat += (lat_subsq * (1 / 24)) - (0.5 / 24)
        lon += (1 / 24)
        lat += (0.5 / 24)

    return (lat, lon)
```

### 6.2 DXCC 前缀库格式

```json
{
  "K": {
    "entity": "United States",
    "lat": 39.8283,
    "lon": -98.5795,
    "continent": "NA",
    "cq_zone": 4,
    "itu_zone": 8
  },
  "JA": {
    "entity": "Japan",
    "lat": 36.2048,
    "lon": 138.2529,
    "continent": "AS",
    "cq_zone": 25,
    "itu_zone": 45
  }
}
```

### 6.3 精度标注

| 来源 | 样式 | 说明 |
|------|------|------|
| Grid | 蓝色实心圆 | 精确到~数公里 |
| API查询 | 空心圆 | 城市级精度 |
| DXCC匹配 | 黄色半透明大圆 | 国家/区域级别 |

---

## 七、数据库设计

### 7.1 ER 图

```mermaid
erDiagram
    USER ||--o{ STATION : has
    USER ||--o{ WATCHLIST : has
    USER ||--o{ QSO_LOG : has
    USER ||--o{ ALERT : has
    USER ||--o{ USER_SETTING : has

    USER {
        int id PK
        string oauth_provider
        string oauth_id
        string username
        string email
        datetime created_at
        datetime last_login
    }

    STATION {
        int id PK
        int user_id FK
        string callsign
        int power
        string antenna
        string grid
        float lat
        float lon
    }

    WATCHLIST {
        int id PK
        int user_id FK
        enum target_type
        string target_value
        string band_preference
        string mode_preference
        bool enabled
    }

    QSO_LOG {
        int id PK
        int user_id FK
        string callsign
        string band
        string mode
        datetime qso_date
        string time_on
        string grid
    }

    ALERT {
        int id PK
        int user_id FK
        string spot_id
        string alert_type
        string message
        bool is_read
    }
```

### 7.2 表结构

```sql
-- users 表
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    oauth_provider ENUM('github', 'google') NOT NULL,
    oauth_id VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    UNIQUE KEY unique_oauth (oauth_provider, oauth_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- stations 表
CREATE TABLE stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    callsign VARCHAR(20) NOT NULL,
    power INT DEFAULT 100,
    antenna VARCHAR(255),
    grid VARCHAR(10),
    lat DECIMAL(10, 7),
    lon DECIMAL(10, 7),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- watchlists 表
CREATE TABLE watchlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    target_type ENUM('dxcc', 'prefix', 'callsign', 'band', 'mode') NOT NULL,
    target_value VARCHAR(255) NOT NULL,
    band_preference VARCHAR(50),
    mode_preference VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- qso_logs 表
CREATE TABLE qso_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    callsign VARCHAR(20) NOT NULL,
    band VARCHAR(10) NOT NULL,
    mode VARCHAR(10) NOT NULL,
    qso_date DATE NOT NULL,
    time_on TIME NOT NULL,
    grid VARCHAR(10),
    country VARCHAR(100),
    freq DECIMAL(10, 5),
    rst_sent VARCHAR(10),
    rst_rcvd VARCHAR(10),
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- alerts 表
CREATE TABLE alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    spot_id VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 八、API 设计

### 8.1 REST API 端点

#### 认证相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /auth/login/{provider} | OAuth 登录入口 (github/google) |
| GET | /auth/callback/{provider} | OAuth 回调处理 |
| POST | /auth/logout | 退出登录 |
| GET | /auth/me | 获取当前用户信息 |

#### 用户相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/user/profile | 获取用户配置信息 |
| PUT | /api/user/profile | 更新用户配置 |
| GET | /api/user/station | 获取台站配置 |
| PUT | /api/user/station | 更新台站配置 |
| GET | /api/user/settings | 获取用户设置 |
| PUT | /api/user/settings | 更新用户设置 |

#### 关注列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/user/watchlist | 获取关注列表 |
| POST | /api/user/watchlist | 添加关注项 |
| PUT | /api/user/watchlist/{id} | 更新关注项 |
| DELETE | /api/user/watchlist/{id} | 删除关注项 |
| POST | /api/user/watchlist/import | 批量导入关注列表 |

#### Spot 数据

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/spots | 获取最新 Spot 列表 |
| GET | /api/spots/{id} | 获取单个 Spot 详情 |

#### 统计

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/stats/bands | 获取波段活动统计 |
| GET | /api/stats/solar | 获取太阳数据 |
| GET | /health | 健康检查（当前实现） |
| GET | /api/history | 历史 Spot 数据（当前实现） |
| GET | /api/stats/user/logs | 获取用户日志统计 |
| GET | /api/stats/user/dxcc | 获取用户 DXCC 统计 |

#### 日志

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/user/logs/upload | 上传日志文件 |
| GET | /api/user/logs | 获取用户日志列表 |
| DELETE | /api/user/logs/{id} | 删除日志记录 |

#### 预警

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/user/alerts | 获取预警列表 |
| PUT | /api/user/alerts/{id}/read | 标记已读 |
| PUT | /api/user/alerts/read-all | 全部已读 |

### 8.2 WebSocket 事件

#### 服务端推送

| 事件名 | 描述 | 数据格式 |
|--------|------|----------|
| spot:new | 新 Spot | `{id, callsign, freq, mode, time, sender, lat, lon, source}` |
| spot:remove | 移除 Spot | `{id}` |
| band:stats | 波段统计更新 | `{band: count, ...}` |
| solar:update | 太阳数据更新 | `{sfi, k, ssn, ...}` |
| alert:new | 新预警 | `{id, type, message, spot}` |
| connection:status | 连接状态 | `{cluster_connected, timestamp}` |

#### 客户端发送

| 事件名 | 描述 | 数据格式 |
|--------|------|----------|
| spot:subscribe | 订阅波段筛选 | `{bands: ['20m', '40m']}` |
| alert:ack | 确认预警 | `{alert_id}` |

### 8.3 API 响应格式

```json
// 成功响应
{
    "success": true,
    "data": { ... },
    "timestamp": "2026-04-25T10:30:00Z"
}

// 错误响应
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid callsign format"
    }
}
```

---

## 九、核心模块设计

### 9.1 Cluster 连接模块

```python
class ClusterConnection:
    def connect(self, host: str, port: int, callsign: str) -> bool:
        """建立 TCP 连接并登录"""

    def disconnect(self) -> None:
        """断开连接"""

    def is_connected(self) -> bool:
        """检查连接状态"""

    def send_command(self, command: str) -> None:
        """发送命令"""

    def read_lines(self, timeout=1.0) -> list:
        """读取多行数据"""
```

**连接流程：**
1. TCP 连接到 dxspam.noi.org:7300
2. 接收欢迎信息（DXSpider 版本）
3. 发送 login CALLSIGN
4. 如需密码，发送密码
5. 进入命令模式，接收 Spot 数据

### 9.2 Spot 解析器

```python
class SpotParser:
    CLUSTER_PATTERN = re.compile(
        r'^DX\s+(?P<callsign>\S+)\s+(?P<freq>[\d.]+)\s+(?P<spotter>\S+)\s+'
        r'(?P<time>\d{4}z)\s*(?P<comment>.*)$'
    )

    def parse(self, raw_line: str) -> Spot | None:
        """解析单行 Spot 数据"""

    def parse_freq(self, freq_str: str) -> float:
        """解析频率，支持 kHz 和 MHz"""
        # 14032.5 -> 14.0325
        # 14.032 -> 14.032
        # 14032 -> 14.032
```

### 9.3 坐标解析模块

```python
class CoordinateResolver:
    def resolve(self, callsign: str) -> dict | None:
        """根据呼号解析 DXCC 信息"""

    def get_coordinates(self, callsign: str) -> tuple[float, float]:
        """获取呼号对应的国家/区域中心坐标"""
    
    def grid_to_latlon(self, grid: str) -> tuple[float, float]:
        """将 Maidenhead Grid 转换为经纬度"""
```

### 9.3.1 Maidenhead Grid 转换算法

**Grid 格式说明：**
```
格式：FN31pr (6 字符标准)
组成：
  - 字段 (Field):   2 字母 (A-R) → 18°×18° 粗粒度
  - 方格 (Square):  2 数字 (0-9) → 2°×1° 中粒度  
  - 子方格 (Subsquare): 2 字母 (A-X) → 5'×2.5' 细粒度
  
转换示例：PN35HS → 经纬度 (近似中心点)
  P = 15 (第 15 个字母) → 经度字段
  N = 13 (第 13 个字母) → 纬度字段
  3 = 3 → 经度方格
  5 = 5 → 纬度方格
  H = 7 (第 7 个字母) → 经度子方格
  S = 18 (第 18 个字母) → 纬度子方格

计算公式：
  经度 = (经度字段 × 20°) + (经度方格 × 2°) + (经度子方格 × 5') - 180°
  纬度 = (纬度字段 × 10°) + (纬度方格 × 1°) + (纬度子方格 × 2.5') - 90°

PN35 HS 中心点 ≈ 45.0833°N, 127.5417°E (哈尔滨附近)
```

**转换代码实现：**
```python
def grid_to_latlon(grid: str) -> tuple[float, float]:
    """
    将 Maidenhead Grid 转换为经纬度（返回 Grid 中心点）
    格式：FN31pr (6 字符) = 字段 (18°x18°) + 方格 (2°x1°) + 子方格 (5'x2.5')
    """
    grid = grid.upper().strip()
    if len(grid) < 6:
        return None
    
    # 解析字段（2 字母）
    lon_field = ord(grid[0]) - ord('A')
    lat_field = ord(grid[1]) - ord('A')
    
    # 解析方格（2 数字）
    lon_sq = int(grid[2])
    lat_sq = int(grid[3])
    
    # 解析子方格（2 字母）
    lon_subsq = ord(grid[4]) - ord('A')
    lat_subsq = ord(grid[5]) - ord('A')
    
    # 计算经纬度（Grid 中心点）
    lon = (lon_field * 20) + (lon_sq * 2) + (lon_subsq * (5/60)) + (2.5/60) - 180
    lat = (lat_field * 10) + (lat_sq * 1) + (lat_subsq * (2.5/60)) + (1.25/60) - 90
    
    return (lat, lon)
```

### 9.3.2 Grid 数据库集成

**数据源**：
- 原始文件：`/workspace/grid_data.bin`（JTDX JTAlert 2.50.5 使用）
- 压缩格式：zlib（4 字节文件头 + 压缩数据）
- 压缩后大小：3.8 MB
- 解压后大小：11.2 MB
- **解析状态：✅ 已成功逆向工程**（2026-05-03）
- 数据量：**29,950 条唯一呼号-Grid 映射**
- 有效记录：29,948 条（99.99%）
- 存储位置：`/workspace/dx_guardian/backend/data/grid_callsign_map_extracted.json`

**二进制格式**（详见 [JTDX_GRID_DATABASE_FORMAT.md](./dx_guardian/docs/JTDX_GRID_DATABASE_FORMAT.md)）

```
记录结构：
+----------------+----------------+---------------------+
|  长度 (2 bytes) |  ID (2 bytes)  |  数据 (N bytes)    |
|  Big-Endian    |  Big-Endian    |  ASCII 字符串      |
+----------------+----------------+---------------------+

数据格式：<CALLSIGN><GRID>
- 呼号长度：3-7 字符，模式 [A-Z0-9]{3,7}
- Grid 模式：[A-R]{2}\d{2}([A-X]{2})?（4 或 6 字符）
- 示例："W7CIEIO82", "U8YDFF60", "5KIMPM30"

解析算法：
1. 读取 2 字节长度（大端序）
2. 读取 2 字节 ID（大端序）
3. 读取 N 字节 ASCII 数据
4. 使用正则提取 Grid：([A-R]{2}\d{2}[A-X]{0,2})
5. Grid 之前部分为呼号
6. 验证呼号格式：^[A-Z0-9]{3,12}$
```
记录格式：
- 2 字节：记录长度（大端序）
- 2 字节：未知字段 ID
- N 字节：ASCII 数据（呼号 + Grid 混合）

Grid 模式：[A-R]{2}\d{2}([A-X]{2})?
示例：JO21SP, DN40JJ, JO48, EM77

呼号-Grid 配对规则：
- Grid 之前的部分为呼号
- 去除非字母数字字符
- 长度 3-12 字符
```

**已提取数据：**
- 文件：`/workspace/grid_callsign_map_extracted.json`
- 唯一呼号数：29,950
- 有效 Grid 数：29,948（99.99%）
- 无效 Grid 数：2（<0.01%）

**加载代码实现：**
```python
import zlib
import json
import re

class GridDatabase:
    def __init__(self):
        self.grid_map = {}  # callsign -> grid
    
    def load_jtdx_format(self, filepath: str) -> int:
        """加载 JTDX 格式的 Grid 数据库"""
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # zlib 解压（跳过 4 字节头）
        decompressed = zlib.decompress(data[4:])
        
        # 解析记录
        offset = 0
        grid_re = re.compile(r'([A-R]{2}\d{2}[A-X]{0,2})', re.I)
        callsign_re = re.compile(r'^[A-Z0-9]{3,12}$')
        
        while offset + 8 <= len(decompressed):
            length = struct.unpack('>H', decompressed[offset:offset+2])[0]
            
            if length == 0 or length > 100:
                offset += 1
                continue
            
            id_val = struct.unpack('>H', decompressed[offset+2:offset+4])[0]
            text = decompressed[offset+4:offset+4+length].decode('ascii', errors='ignore').strip()
            
            # 查找 Grid
            grid_match = grid_re.search(text)
            if grid_match:
                grid = grid_match.group(1).upper()
                # Grid 之前的部分为呼号
                callsign = text[:grid_match.start()].strip()
                callsign = re.sub(r'[^A-Z0-9/]', '', callsign).upper()
                
                if callsign_re.match(callsign):
                    self.grid_map[callsign] = grid
            
            offset += 4 + length
        
        return len(self.grid_map)
    
    def load_from_json(self, filepath: str) -> int:
        """从预解析的 JSON 文件加载"""
        with open(filepath, 'r') as f:
            self.grid_map = json.load(f)
        return len(self.grid_map)
    
    def lookup(self, callsign: str) -> str | None:
        """查询呼号对应的 Grid"""
        return self.grid_map.get(callsign.upper())
```

**解析优先级：**
1. PSK Reporter → `senderLocator` 直接提供 Grid → 精确坐标（精度±5km）
2. Grid 数据库查询 → 29,950 条呼号-Grid 映射 → 精确坐标（精度±5km）
3. CTY.DAT 前缀匹配 → DXCC 实体中心 + 散射 → 区域坐标（精度±50km）

**坐标精度对比：**
| 数据源 | 精度 | Grid 字符 | 覆盖范围 | 示例 |
|--------|------|----------|----------|------|
| PSK Reporter Grid | ±5km | 6 字符 | FT8/FT4 用户 | W7CIE IO82 |
| JTDX Grid 数据库 | ±5km | 4 字符 | 29,950 呼号 | U8YD FF60 |
| CTY.DAT DXCC 实体 | ±50km | - | 26,895 前缀 | BG2ENW |

**数据库统计：**
- 总记录数：29,950
- 有效 Grid: 29,948 (99.99%)
- 无效记录：2 (0.01%)
- 唯一 Grid 数：3,391
- 平均每个 Grid 的呼号数：8.8

**地域分布：**
- 欧洲：~1,200 Grids (G, DL, F, I, EA)
- 北美：~800 Grids (W, K, VE)
- 亚洲：~600 Grids (JA, UA, BY, HL)
- 大洋洲：~200 Grids (VK, ZL)
- 南美：~150 Grids (PY, LU, HC)
- 非洲：~100 Grids (ZS, CT1)

**样例数据：**
```
U8YD         -> FF60   (俄罗斯)
W7CIE        -> IO82   (英国)
A8UET        -> EN70   (美国)
N4IUD        -> DM31   (美国)
A6ZPA/P      -> JO48   (德国)
5KIM         -> PM30   (日本)
B8CDK/P      -> MO06   (中国)
```

### 9.4 预警规则引擎

```python
class AlertEngine:
    def match_spot(self, spot: dict, watchlist: list) -> list[Alert]:
        """匹配 Spot 与用户关注列表"""

    def match_dxcc(self, spot: dict, dxcc: str) -> bool:
        """匹配 DXCC 实体"""

    def match_prefix(self, spot: dict, prefix: str) -> bool:
        """匹配呼号前缀"""

    def match_band(self, spot: dict, band: str) -> bool:
        """匹配波段"""

    def match_mode(self, spot: dict, mode: str) -> bool:
        """匹配模式"""
```

### 9.5 机会评分引擎

| 因素 | 权重 | 最大得分 | 评分规则 |
|------|------|----------|----------|
| 波段活跃度 | 25% | 25 | 该波段当前 Spot 数量 / 总 Spot 数量 |
| 太阳数据 | 20% | 20 | SFI 分（好/中/差）+ K 指数分 |
| 时间窗口 | 15% | 15 | 灰线时间+5分，白天F2层+3分，深夜-5分 |
| 距离匹配 | 15% | 15 | 短距→低频段，远距→高频段匹配度 |
| Spot 热度 | 15% | 15 | 该 DXCC 当前 Spot 数量 |
| 模式匹配 | 10% | 10 | 用户支持的模式与当前活跃模式的匹配度 |

**评分展示示例：**
```
🎯 机会评分：73/100
├─ 波段活跃度：18/25（20m 活跃，Spot 234个）
├─ 太阳条件：16/20（SFI 105 正常，K=2 稳定）
├─ 时间窗口：10/15（UTC 09:00，F2层可用）
├─ 距离匹配：12/15（3500km → 20m 合适）
├─ Spot 热度：12/15（该区域近期活跃）
└─ 模式匹配：5/10（FT8 活跃，你支持 CW+FT8）
```

### 9.6 ADIF 解析器

**必需字段：** `CALL`、`BAND`、`MODE`、`QSO_DATE`、`TIME_ON`

**可选字段：** `GRID`、`COUNTRY`、`FREQ`、`RST_SENT`、`RST_RCVD`

```python
class ADIFParser:
    REQUIRED_FIELDS = ['CALL', 'BAND', 'MODE', 'QSO_DATE', 'TIME_ON']

    def parse(self, file_path: str) -> tuple[list[QSORecord], list[ParseError]]:
        """解析 ADIF 文件"""

    def parse_record(self, record_str: str) -> QSORecord | None:
        """解析单条记录"""

    def validate_record(self, record: QSORecord) -> bool:
        """验证必需字段"""
```

---

## 十、前端架构

### 10.1 页面结构

```mermaid
graph TB
    subgraph Pages["页面"
        LoginPage["登录页"]
        MainPage["主页面"]
        SettingsPage["设置页"]
        LogsPage["日志页"]
    ]

    subgraph Components["组件"]
        Map["地图组件 (Leaflet)"]
        BandBar["波段活动条"]
        SpotList["Spot列表"]
        AlertPanel["预警面板"]
        StationConfig["台站配置"]
        WatchlistEditor["关注列表编辑器"]
        SolarPanel["太阳数据面板"]
        StatsCharts["统计图表"]
        FileUpload["文件上传"]
    end

    MainPage --> Map
    MainPage --> BandBar
    MainPage --> SpotList
    MainPage --> AlertPanel
    MainPage --> SolarPanel
    SettingsPage --> StationConfig
    SettingsPage --> WatchlistEditor
    LogsPage --> FileUpload
    LogsPage --> StatsCharts
```

### 10.2 状态管理

```javascript
const store = {
    user: { id, callsign, grid, settings },
    spots: new Map(),  // spotId -> Spot
    alerts: [],
    bandStats: {},
    solarData: {},
    filters: { bands: [], modes: [] },
    connection: { cluster: false, websocket: false }
};
```

### 10.3 地图配置

```javascript
// Leaflet 配置
const map = L.map('map-container', {
    center: [20, 0],
    zoom: 3,
    minZoom: 2,
    maxZoom: 18
});

// OpenStreetMap 瓦片
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

// 标记集群
const markers = L.markerClusterGroup({
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false
});
```

---

## 十一、分阶段开发计划

### MVP 1：实时 Spot 地图（核心，10-14天）

**目标：能跑起来的实时 DX Spot 地图**

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 1.1 | Flask + Flask-SocketIO 项目初始化 | 0.5天 | 可访问的空白页面 |
| 1.2 | Cluster Telnet 连接模块（socket实现） | 1.5天 | 能连接、登录、接收 Spot |
| 1.3 | Spot 解析器（解析标准 Cluster 格式） | 1天 | 结构化 Spot 数据 |
| 1.4 | Spot 去重 + 限流模块 | 0.5天 | 去重后的 Spot 流 |
| 1.5 | DXCC 前缀库（JSON，从 ARRL 整理） | 1天 | prefix_to_dxcc.json |
| 1.6 | 坐标解析模块（grid/callsign/DXCC三级） | 1天 | Spot → 经纬度 |
| 1.7 | Leaflet 地图初始化 + OpenStreetMap | 0.5天 | 空白地图页面 |
| 1.8 | WebSocket 推送 Spot 到前端 | 1天 | 实时点渲染 |
| 1.9 | 波段活动条（顶部统计） | 0.5天 | 波段计数+高亮 |
| 1.10 | 基础筛选（波段/模式/时间） | 0.5天 | 前端过滤控件 |
| 1.11 | 响应式布局（桌面+移动端） | 0.5天 | 手机可正常查看 |
| 1.12 | 测试 + 调试 + 修复 | 1天 | 稳定运行 |

**MVP 1 交付标准：**
- [ ] 打开页面能看到世界地图
- [ ] Cluster Spot 实时出现在地图上
- [ ] 波段活动条显示各波段 Spot 数量
- [ ] 能按波段筛选
- [ ] 断线自动重连
- [ ] 手机端可用

---

### MVP 2：预警规则（5-7天）

**目标：当关注的电台/区域活跃时提醒用户**

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 2.1 | 用户台站配置界面 | 1天 | 呼号/功率/天线/Grid 配置页 |
| 2.2 | 关注列表管理 | 1天 | 关注 DXCC/呼号/波段/模式 |
| 2.3 | 预警规则引擎 | 1.5天 | 匹配关注列表 → 触发预警 |
| 2.4 | 页面内预警列表 | 0.5天 | 实时预警消息区 |
| 2.5 | 浏览器通知（Notification API） | 0.5天 | 桌面弹窗通知 |
| 2.6 | 太阳数据面板（hamqsl） | 1天 | SFI/K/SSN 显示 |
| 2.7 | 测试 + 修复 | 1天 | 稳定运行 |

**MVP 2 交付标准：**
- [ ] 能配置自己的台站参数
- [ ] 能添加关注的 DXCC/呼号
- [ ] 关注目标活跃时页面内弹预警
- [ ] 浏览器通知弹出
- [ ] 太阳活动数据实时显示

---

### MVP 3：日志分析（5-7天）

**目标：上传日志，统计已通/缺失 DXCC，与实时 Spot 匹配**

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 3.1 | ADIF 文件解析器 | 1.5天 | 解析标准 ADIF 3.1 格式 |
| 3.2 | CSV 文件解析器 | 0.5天 | 解析 Wavelog 导出的 CSV |
| 3.3 | DXCC 统计（已通/缺失） | 1天 | 已通 DXCC 列表 + 缺失列表 |
| 3.4 | 文件上传界面 | 0.5天 | 拖拽上传 + 进度条 |
| 3.5 | 缺失 DXCC 与实时 Spot 匹配 | 1天 | 缺失 DXCC 活跃时高亮 |
| 3.6 | 统计面板（DXCC 计数/波段统计） | 1天 | 图表展示 |
| 3.7 | 测试 + 修复 | 1天 | 稳定运行 |

**MVP 3 交付标准：**
- [ ] 能上传 ADIF 文件
- [ ] 正确统计已通 DXCC 数量
- [ ] 缺失 DXCC 列表显示
- [ ] 缺失 DXCC 有 Spot 时在地图上特殊标记
- [ ] 基础统计图表（DXCC 计数、波段分布）

---

### MVP 4：机会评分（5-7天）

**目标：基于规则的"机会评分"，不是"成功率预测"**

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 4.1 | 规则评分模型设计 | 1.5天 | 评分规则表 |
| 4.2 | 评分计算模块 | 1.5天 | 输入：太阳数据+距离+波段+时间 → 输出：评分+依据 |
| 4.3 | 评分展示（推荐列表） | 1天 | 排序列表 + 评分依据说明 |
| 4.4 | 历史日志验证 | 1天 | 用用户历史通联数据验证评分准确性 |
| 4.5 | 测试 + 修复 | 1天 | 稳定运行 |

**MVP 4 交付标准：**
- [ ] 每个缺失 DXCC 显示机会评分
- [ ] 评分有具体依据说明
- [ ] 能用历史日志验证评分与实际结果的偏差
- [ ] 不承诺"准确概率"，明确标注为"机会评分"

---

### 增强版（MVP 全部完成后）

| 功能 | 说明 | 前置依赖 |
|------|------|----------|
| Web Push 推送 | HTTPS + Service Worker + VAPID | 域名+SSL证书 |
| 热点图（Heatmap） | Leaflet.heat 高频区域可视化 | MVP 1 稳定运行 |
| 多语言 | 中英文为主，结构预留其他语言 | MVP 2 完成 |
| DXCC 实体中文翻译 | 自行整理 ARRL DXCC 列表中文版 | 数据整理 |
| 趋势预测 | 基于历史 Spot 数据的趋势分析 | MVP 3 + 4 完成 |
| VOACAP 集成 | 专业 HF 传播预测模型 | MVP 4 评分模型稳定 |
| 机器学习评分 | 用历史日志训练预测模型 | 大量历史数据积累 |

---

## 十二、文件结构

```
dx_guardian/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # Flask 主程序
│   ├── config.py                 # 配置管理
│   ├── extensions.py            # Flask 扩展初始化
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── station.py
│   │   ├── watchlist.py
│   │   ├── qso_log.py
│   │   └── alert.py
│   ├── routes/                   # 路由
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── spots.py
│   │   │   ├── user.py
│   │   │   ├── watchlist.py
│   │   │   ├── logs.py
│   │   │   ├── alerts.py
│   │   │   └── stats.py
│   │   └── admin.py
│   ├── services/                # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── spot_service.py
│   │   ├── alert_service.py
│   │   ├── score_service.py
│   │   └── log_service.py
│   ├── workers/                 # 后台任务
│   │   ├── __init__.py
│   │   ├── cluster_worker.py
│   │   ├── spot_deduplicator.py
│   │   ├── solar_data_worker.py
│   │   └── cleanup_worker.py
│   ├── modules/                 # 核心模块
│   │   ├── __init__.py
│   │   ├── cluster_connection.py
│   │   ├── spot_parser.py
│   │   ├── coordinate_resolver.py
│   │   ├── grid_database.py     # Grid 数据库查询（新增）
│   │   ├── adif_parser.py
│   │   └── alert_engine.py
│   ├── utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── decorators.py
│   │   └── validators.py
│   └── data/
│       ├── prefix_to_dxcc.json  # DXCC 前缀库
│       └── grid_data.bin        # Grid 数据库（28 万条，新增）
├── frontend/
│   ├── templates/
│   │   ├── index.html           # 主页面
│   │   └── login.html           # 登录页
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js              # 主应用
│       ├── map.js               # 地图逻辑
│       ├── grid.js              # Grid 方格计算（新增）
│       ├── socket.js            # WebSocket
│       └── api.js              # API 调用
├── tests/
│   ├── test_spot_parser.py
│   ├── test_coordinate_resolver.py
│   ├── test_grid_database.py    # Grid 数据库测试（新增）
│   ├── test_adif_parser.py
│   ├── test_alert_engine.py
│   └── test_score_engine.py
├── migrations/
│   └── versions/
├── requirements.txt
├── .env.example
└── run.py
```

---

## 十三、时间估算

| 阶段 | 内容 | 预计时间 | 累计 |
|------|------|----------|------|
| MVP 1 | 实时 Spot 地图 | 10-14 天 | 10-14 天 |
| **Grid 增强** | **Maidenhead Grid 数据集成** | **3-5 天** | **13-19 天** |
| MVP 2 | 预警规则 | 5-7 天 | 18-26 天 |
| MVP 3 | 日志分析 | 5-7 天 | 23-33 天 |
| MVP 4 | 机会评分 | 5-7 天 | 28-40 天 |
| **总计** | **稳定可用版（含 Grid）** | **6-8 周** | |

说明：按每天有效开发 3-4 小时估算。每个 MVP 结束后验收确认再开始下一个。

### Grid 数据集成功能详细说明

**功能目标：**
- 解析 `/workspace/grid_data.bin` 文件（28 万条呼号-Grid 映射）
- 建立 呼号 → Grid 的快速查询数据库
- DX Cluster Spot 到达时，查询 Grid 并转换为精确经纬度
- 地图上将电台显示在其报告的 Grid 中心点（精度±5km），而非 DXCC 国家中心

**技术实现步骤：**
1. 解析二进制文件（zlib 解压 + UTF-16 LE 解码）
2. 构建内存哈希表（callsign → grid）
3. 修改 `coordinate_resolver.py` 添加 Grid 查询层
4. 前端地图显示 Grid 中心点坐标
5. 添加 Grid 覆盖层显示功能（可选）

**数据格式说明：**
- 文件路径：`/workspace/grid_data.bin`
- 压缩方式：zlib（跳过 4 字节文件头）
- 编码格式：UTF-16 LE
- 记录格式：`CALLSIGN\0GRID\0CALLSIGN\0GRID...`
- 数据量：约 28 万条唯一呼号-Grid 映射

**坐标解析优先级（已更新）：**
1. **PSK Reporter** → `senderLocator` 直接提供 Grid → 精确坐标（±5km）
2. **Grid 数据库** → 查询呼号对应 Grid → 精确坐标（±5km）
3. **CTY.DAT 前缀匹配** → DXCC 实体中心 + 散射 → 区域坐标（±50km）

**Map 渲染改进：**
- PSK Reporter spots：精确显示在 Grid 中心点
- Cluster spots：查询 Grid 数据库，有 Grid 则显示 Grid 中心点，无 Grid 则使用 CTY 坐标
- 添加 Grid 方格覆盖层（可选，按钮切换）
- Tooltip 显示 Grid 信息（如 `Grid: PN35HS`）

---

## 十三.1 Grid 数据库测试验证

**✅ 解析测试（已完成）：**
```bash
# 验证 grid_data.bin 可以成功解析
python3 scripts/parse_jtdx_griddb.py /workspace/grid_data.bin

# 输出：
# ✓ 解析成功：29,950 条呼号-Grid 映射
# ✓ 提取文件：/workspace/grid_callsign_map_extracted.json
# ✓ 有效率：99.99%
```

**✅ 数据验证（已完成）：**
```python
import json

with open('/workspace/grid_callsign_map_extracted.json', 'r') as f:
    grid_map = json.load(f)

print(f"总呼号数：{len(grid_map):,}")  # 29,950

# 验证 Grid 有效性
import re
grid_re = re.compile(r'^[A-R]{2}\d{2}([A-X]{2})?$')
valid_grids = sum(1 for gr in grid_map.values() if grid_re.match(gr))
print(f"有效 Grid 数：{valid_grids:,}")  # 29,948
```

**样例数据：**
| 呼号 | Grid | 位置 |
|------|------|------|
| U8YD | FF60 | 俄罗斯 |
| W7CIE | IO82 | 英国 |
| A6ZPA/P | JO48 | 德国 |
| 5KIM | PM30 | 日本 |
| B8CDK/P | MO06 | 中国 |

**查询测试（待实现）：**
```python
from backend.modules.grid_database import GridDatabase

db = GridDatabase()
db.load_from_json('/workspace/grid_callsign_map_extracted.json')

# 测试查询
grid = db.lookup('BG2ENW')
if grid:
    print(f"BG2ENW -> {grid}")  # 预期：PN35HS 或类似
    
    lat, lon = grid_to_latlon(grid)
    print(f"Grid {grid} -> Lat: {lat:.4f}, Lon: {lon:.4f}")
```

**地图渲染测试（待实现）：**
1. 打开地图页面
2. 观察 Cluster spot 是否显示在正确 Grid 中心点
3. 对比 hamqsl.com/cluster 和 dxwatch.com 的 spot 位置
4. 确认地图上的电台位置与实际 Grid 报告一致

**数据集统计：**
- 总记录数：29,950
- 有效 Grid：29,948 (99.99%)
- 无效 Grid：2 (0.01%)
- 覆盖国家/地区：约 150 个 DXCC 实体
- Grid 分布：全球范围（AA-RR）

---

## 十三.2 已知问题与待确认

**Grid 数据格式：✅ 已解决（2026-05-03）**
- JTDX 的 `grid_data.bin` 格式已成功逆向
- 解析出 29,950 条呼号-Grid 映射
- 提取文件：`/workspace/grid_callsign_map_extracted.json`
- 数据验证：99.99% 有效 Grid

**已实现的解析方法：**
- 记录格式：2 字节长度（大端序）+ 2 字节 ID + N 字节 ASCII 数据
- Grid 模式：`[A-R]{2}\d{2}([A-X]{2})?`
- 配对规则：Grid 之前的部分为呼号，去除非字母数字字符

**下一步工作：**
- [x] JTDX grid_data.bin 格式逆向工程 ✅
- [x] 提取呼号-Grid 映射 ✅
- [x] 保存为 JSON 格式 ✅
- [x] 集成到 `coordinate_resolver.py` ✅
- [x] 实现 `grid_database.py` 模块 ✅
- [x] 测试 Grid 数据库查询 ✅
- [x] 前端标记支持 Grid 精度显示 ✅
- [ ] 验证地图渲染 Grid 中心点（服务已启动，人工验证中）

**备用方案（仍然保留）：**
1. **PSK Reporter API** - 查询呼号历史 Grid 报告（实时数据补充）
2. **QRZ.com API** - 查询呼号注册信息中的 Grid（需要订阅）
3. **ClubLog.org** - 导入已通联记录中的 Grid 数据（用户手动上传）
4. **用户贡献** - 收集用户上报的呼号-Grid 映射

**已实现功能：**
- [x] Grid 到经纬度的转换算法 (`grid_to_latlon`) ✅
- [x] JTDX Grid 数据库逆向工程 ✅
- [x] 提取 29,950 条呼号-Grid 映射 ✅
- [x] 保存为 JSON 格式 ✅
- [x] Grid 数据库加载模块 ✅
- [ ] 地图渲染支持 Grid 中心点显示
- [x] PSK Reporter 的 `senderLocator` 字段已保留 ✅
- [x] 集成到 CoordinateResolver（5 级优先级） ✅

---

## 十四、验收标准

### MVP 1 验收清单

- [ ] 页面加载 ≤ 3秒
- [ ] Spot 延迟 ≤ 5秒（从 Cluster 收到到地图显示）
- [ ] 断线重连 ≤ 30秒
- [ ] 同时显示 500+ Spot 不卡顿
- [ ] 手机端可正常操作
- [ ] Chrome / Firefox / Safari 兼容

### MVP 2 验收清单

- [ ] 配置保存后刷新不丢失
- [ ] 预警 ≤ 10秒（从 Spot 到通知）
- [ ] 浏览器通知正常弹出

### MVP 3 验收清单

- [ ] 支持 ADIF 3.1 标准格式
- [ ] 10MB 日志文件解析 ≤ 10秒
- [ ] DXCC 统计与 Club Log / Wavelog 对比无差异

### MVP 4 验收清单

- [ ] 评分与依据同步显示
- [ ] 用历史日志回测评分准确率 ≥ 60%
- [ ] 不承诺"精确概率"

---

## 十五、部署架构

### 15.1 部署拓扑

```mermaid
graph TB
    subgraph Internet["互联网"]
        User[("用户浏览器")]
    end

    subgraph Server["服务器"]
        Nginx["Nginx 反向代理"]
        FlaskApp["Flask + Gunicorn"]
        MySQL["MySQL 数据库"]
    end

    User -->|HTTPS| Nginx
    Nginx -->|HTTP| FlaskApp
    FlaskApp <-->|TCP| MySQL

    FlaskApp -->|Telnet| ClusterServer["DXSpider Cluster"]
    FlaskApp -->|HTTP| HamQSL["hamqsl.com"]
    FlaskApp -->|OAuth| OAuth["GitHub/Google OAuth"]
```

### 15.2 Nginx 配置

```nginx
server {
    listen 443 ssl;
    server_name dxguardian.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 十六、错误处理与重试策略

### 16.1 异常分类

| 异常类型 | 处理策略 | 示例 |
|----------|----------|------|
| ValidationError | 返回 400 | 呼号格式错误 |
| AuthenticationError | 返回 401 | OAuth 失败 |
| AuthorizationError | 返回 403 | 无权限操作 |
| NotFoundError | 返回 404 | 资源不存在 |
| RateLimitError | 返回 429 | API 过于频繁 |
| ClusterError | 内部处理，触发重连 | Cluster 连接断开 |
| ExternalServiceError | 使用缓存 | hamqsl.com 不可用 |

### 16.2 重试策略

```python
RETRY_STRATEGY = {
    'cluster_connection': {
        'max_attempts': 5,
        'backoff': [5, 15, 30, 60, 60],  # seconds
    },
    'http_request': {
        'max_attempts': 2,
        'delay': 3,  # seconds
    }
}
```

---

## 十七、测试策略

### 17.1 测试分层

```
     端到端测试 (Playwright)
            ↓
     集成测试 (Flask TestClient)
            ↓
       单元测试 (Pytest)
```

### 17.2 单元测试覆盖

| 模块 | 测试项 |
|------|--------|
| SpotParser | 解析标准格式、频率解析、时间解析 |
| CoordinateResolver | Grid 转经纬度、DXCC 前缀匹配 |
| AlertEngine | DXCC 匹配、前缀匹配、波段匹配、模式匹配 |
| ScoreEngine | 各因素评分、权重计算 |
| ADIFParser | 标准 ADIF 解析、字段验证 |

---

## 十八、性能指标

| 指标 | 目标值 |
|------|--------|
| 页面加载时间 | ≤ 3秒 |
| Spot 延迟（从 Cluster 到地图显示） | ≤ 5秒 |
| 断线重连时间 | ≤ 30秒 |
| 同时显示 Spot 数量 | 500+ 不卡顿 |
| ADIF 解析速度（10MB 文件） | ≤ 10秒 |
| API 响应时间（P99） | ≤ 200ms |

---

## 十九、安全措施

1. **HTTPS**：全站强制 HTTPS
2. **OAuth CSRF**：使用 state 参数防止 CSRF
3. **输入验证**：所有用户输入进行验证和清理
4. **SQL 注入防护**：使用 SQLAlchemy ORM
5. **XSS 防护**：前端对用户数据进行转义
6. **Rate Limiting**：API 端点限流

---

## 二十、环境变量配置

```bash
# OAuth Credentials
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Session
SECRET_KEY=your-very-long-random-secret-key-here

# Cluster 服务器配置
CLUSTER_HOST=dxspam.noi.org
CLUSTER_PORT=7300
CLUSTER_CALLSIGN=YOURCALL

# 数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dxguardian
```

---

*开发计划书 v5.2（完整技术版）*
*最后更新：2026-04-26*
*核心改动：补充 PSKReporter 数据源、多 Cluster 服务器、当前实现状态、部署环境说明*

---

## 十一、部署环境

### 11.1 Python 虚拟环境

项目使用 venv 隔离依赖，系统 Python 无需安装 flask 等包。

```bash
# 创建虚拟环境（首次）
cd dx_guardian
python3 -m venv venv
source venv/bin/activate
pip install flask flask-socketio eventlet requests

# 启动服务
source venv/bin/activate
python3 backend/app.py
```

### 11.2 运行端口

- 默认端口：5000
- 端口被占用时：`lsof -ti:5000 | xargs kill -9`

### 11.3 后台运行

```bash
# 后台启动
cd ~/.openclaw/workspace/dx_guardian
source venv/bin/activate
nohup python3 backend/app.py > /tmp/dx_guardian.log 2>&1 &

# 查看日志
tail -f /tmp/dx_guardian.log

# 健康检查
curl http://127.0.0.1:5000/health
```

---

## 十二、当前实现状态（2026-05-02 更新）

### ✅ 已完成
| 功能 | 说明 |
|------|------|
| DX Cluster 连接 | 多服务器自动切换，当前优先天津 BH3BBJ |
| PSKReporter 数据源 | 全球查询，5 分钟间隔，429 限流处理 |
| Spot 解析与缓存 | Cluster + PSKReporter 统一格式，去重 |
| 波段活动统计 | 实时统计各波段 Spot 数量 |
| 太阳数据面板 | hamqsl.com 数据获取与展示 |
| Leaflet 地图 | Spot 地图标记 |
| WebSocket 实时推送 | 新 Spot 实时推送到前端 |
| health API | 健康检查接口 |
| **后端模块化重构** | 拆分为 6 个路由模块，app.py 从 1682 行降至 955 行 |
| **单元测试** | 10 个测试用例，覆盖所有新增路由模块 |
| **Docker 容器化** | Dockerfile + docker-compose.yml |
| **CI/CD 流水线** | GitHub Actions 自动测试/构建/部署 |
| **安全配置** | 环境变量管理 + 生产配置检查脚本 |

### 🔄 计划中（按优先级）
| 功能 | 优先级 | 说明 |
|------|--------|------|
| 用户系统（OAuth） | P1 | 登录、台站配置 |
| 关注列表/预警 | P1 | watchlist + alert 引擎 |
| 机会评分引擎 | P2 | 6 因素加权评分 |
| ADIF日志上传 | P2 | 日志导入与匹配 |
| MySQL数据库 | P3 | 替换内存缓存 |
| 多页面路由 | P3 | 设置页、日志页 |

### 📊 技术债
- `data_sources.py` 拆分：因 `nonlocal` 依赖复杂，延后处理

---

## 十三、文档变更记录

### v6.1 (2026-05-03) - Grid 数据库格式文档完善
**新增文档**：
- `dx_guardian/docs/JTDX_GRID_DATABASE_FORMAT.md` - JTDX Grid 数据库格式详细解析

**格式说明**：
- ✅ 二进制记录格式：2 字节长度 + 2 字节 ID + N 字节 ASCII 数据
- ✅ 压缩方式：zlib（4 字节文件头）
- ✅ 数据格式：`<CALLSIGN><GRID>` ASCII 字符串
- ✅ Grid 模式：`[A-R]{2}\d{2}([A-X]{2})?`（4 或 6 字符）
- ✅ 呼号识别：正则 `^[A-Z0-9]{3,12}$`
- ✅ 解析算法：从后向前查找 Grid，Grid 之前为呼号

**算法文档**：
- ✅ Grid ↔ 经纬度双向转换公式
- ✅ Maidenhead 网格系统分层说明（Field/Square/Subsquare）
- ✅ 4 字符 Grid 精度：±5km（2°×1° 中心点）
- ✅ 6 字符 Grid 精度：±500m（5′×2.5′ 中心点）

**统计数据**：
- ✅ 总记录数：29,950
- ✅ 有效率：99.99%（29,948 条有效 Grid）
- ✅ 唯一 Grid 数：3,391
- ✅ 地域分布：欧洲~1,200、北美~800、亚洲~600

**解析优先级更新**：
1. PSK Reporter Grid（用户实时上报）
2. JTDX Grid 数据库查询（29,950 条历史数据）
3. CTY.DAT 前缀匹配（26,895 前缀，±50km 散射）
4. DXCC 兜底（317 实体，国家中心点）

### v6.0 (2026-05-03) - Grid 数据库集成
- ✅ JTDX grid_data.bin 逆向工程
- ✅ 提取 29,950 条呼号-Grid 映射
- ✅ `grid_database.py` 模块实现
- ✅ `coordinate_resolver.py` 5 级优先级集成
- ✅ 前端地图支持 Grid 精度显示

### v5.0 (2026-05-02) - 模块化重构
- ✅ 后端拆分为 6 个路由模块
- ✅ 单元测试覆盖
- ✅ Docker 容器化
- ✅ CI/CD 流水线

---

*文档版本：v6.1 | 最后更新：2026-05-03 | 维护者：DX Guardian 开发团队*

---

## 二十一、架构决策记录（ADR）

### ADR-001：数据源架构决策

**日期**：2026-05-05  
**决策者**：BG2ENW + AI Agent  
**状态**：✅ 已确认

#### 问题

DX Guardian 部署在远程服务器（VPS/云服务器），需要决定如何获取本地 WSJT-X 的解码数据。

#### 上下文

```
┌─────────────────┐         ┌─────────────────┐
│   本地电脑       │         │   远程服务器     │
│   (用户家)       │         │   (VPS/云服务器)  │
│                 │         │                 │
│  ┌───────────┐  │  网络    │  ┌───────────┐  │
│  │ WSJT-X    │  │  不可达  │  │ DX Guardian│  │
│  │ (UDP 2237)│──┼──✗──────┼──│ (Flask)   │  │
│  └───────────┘  │         │  └───────────┘  │
│                 │         │       ▲         │
│  ┌───────────┐  │         │       │         │
│  │ 本地电台   │  │         │       │         │
│  └───────────┘  │         │       │         │
└─────────────────┘         │       │         │
                            │       │         │
                            │  可访问            │
                            │       │         │
                            └───────┼─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │DX Cluster │   │PSK Reporter│   │ Wavelog   │
            │ (Telnet)  │   │  (API)    │   │  (API)    │
            └───────────┘   └───────────┘   └───────────┘
```

**核心约束**：
- WSJT-X 运行在用户本地电脑，UDP 端口 2237 无法从远程服务器直接访问
- DX Guardian 定位为**纯分析系统**，不参与日志写入和设备控制
- 系统需要实时 DX Spot 数据进行分析和预警

#### 可选方案

| 方案 | 描述 | 复杂度 | 实时性 | 推荐度 |
|------|------|--------|--------|--------|
| **A** | 本地 UDP 转发代理 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **B** | WSJT-X 外部程序插件 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **C** | 仅依赖远程数据源 | - | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

#### 决策

**选择方案 C：仅依赖远程数据源**

**原因**：
1. **架构简洁**：无需在用户本地运行额外程序，降低运维复杂度
2. **数据覆盖足够**：DX Cluster + PSK Reporter 已覆盖全球大部分 DX 活动
3. **符合定位**：DX Guardian 是分析系统，不是数据采集系统
4. **用户友好**：用户只需部署远程服务，无需配置本地代理

#### 数据源配置

| 数据源 | 获取方式 | 更新频率 | 实时性 | 覆盖率 |
|--------|----------|----------|--------|--------|
| **DX Cluster** | Telnet 连接 | 实时 | ⭐⭐⭐⭐ | 高 |
| **PSK Reporter** | HTTP API | 5 分钟 | ⭐⭐⭐ | 中 |
| **Wavelog API** | HTTP API | 按需 | ⭐⭐ | 低（仅已通联） |

#### 后续可选扩展

如果用户需要更精确的本地解码数据，可提供**可选组件**：

```
scripts/wsjtx_forwarder.py  # 本地转发代理（可选，非核心）
```

该脚本作为独立组件提供，用户按需部署，不集成到主应用。

---

### ADR-002：系统定位决策

**日期**：2026-05-05  
**决策者**：BG2ENW + AI Agent  
**状态**：✅ 已确认

#### 问题

DX Guardian 是否应该参与日志写入和设备控制？

#### 决策

**DX Guardian 定位为纯分析系统**

**不实现的功能**：
- ❌ ADIF 日志写入
- ❌ QSO 自动推送
- ❌ CAT 设备控制
- ❌ 电台参数配置

**实现的功能**：
- ✅ 实时 DX Spot 接收与分析
- ✅ 坐标解析与地图显示
- ✅ 机会评分与预警
- ✅ 历史日志查询（只读）
- ✅ Wavelog 数据查询（只读）

#### 原因

1. **职责分离**：日志写入和设备控制应由专业软件（WSJT-X、Wavelog）处理
2. **降低风险**：避免意外写入错误日志或误控设备
3. **简化架构**：只读接口更稳定，无需处理写入冲突
4. **符合用户需求**：用户明确说明"不参与日志写入和设备控制"

---

## 二十二、核心模块改进计划

### 22.1 智能去重算法（优先级：P0）

**当前问题**：
- 单一时间窗口去重（5 分钟）
- 仅按呼号+频率去重
- 无数据源置信度区分

**改进方案**：

```python
# backend/smart_deduplicator.py
class SmartDeduplicator:
    """智能去重器（多源置信度）"""
    
    # 数据源置信度（越高越可信）
    SOURCE_CONFIDENCE = {
        'pskreporter': 90,   # PSK Reporter（高，全球接收）
        'cluster': 70,       # DX Cluster（中，用户报告）
        'user': 50           # 用户手动提交（低）
    }
    
    WINDOW_SECONDS = 300  # 5 分钟
    
    def _make_key(self, spot):
        """生成去重键：呼号 + 频率 + Grid"""
        callsign = spot.get('callsign', '').upper()
        freq = spot.get('freq', 0)
        grid = spot.get('grid', '')[:4]  # 只取前 4 位 Grid
        return f"{callsign}:{freq}:{grid}"
    
    def process(self, spot):
        """处理新 Spot，返回是否应该保留"""
        key = self._make_key(spot)
        now = time.time()
        
        self._cleanup(now)
        existing = self.seen.get(key)
        new_confidence = self.SOURCE_CONFIDENCE.get(spot.get('source', 'unknown'), 0)
        
        if not existing:
            self.seen[key] = spot
            return True
        
        existing_confidence = self.SOURCE_CONFIDENCE.get(existing.get('source', 'unknown'), 0)
        
        if new_confidence > existing_confidence:
            self.seen[key] = spot
            return True
        
        return False
```

**实施计划**：
| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建 `smart_deduplicator.py` 模块 | 0.5 天 |
| 2 | 更新 `spot_parser.py` 集成智能去重 | 0.5 天 |
| 3 | 更新 `app.py` 替换原有去重逻辑 | 0.25 天 |
| 4 | 编写单元测试 | 0.25 天 |
| 5 | 测试验证 | 0.25 天 |

**总计**：1.75 天

---

### 22.2 增强版机会评分引擎（优先级：P0）

**当前问题**：
- 固定规则评分，权重静态
- 无 DXCC 稀有度区分
- 无传播条件动态调整

**改进方案**：

```python
# backend/enhanced_scorer.py
class EnhancedScorer:
    """增强版机会评分器"""
    
    def score(self, spot):
        """计算综合评分（0-100）"""
        score = 0
        
        # 1. DXCC 稀有度（30 分）
        score += self._dxcc_score(spot) * 0.3
        
        # 2. 传播条件（20 分）
        score += self._propagation_score(spot) * 0.2
        
        # 3. 距离评分（20 分）
        score += self._distance_score(spot) * 0.2
        
        # 4. 时间窗口（15 分）
        score += self._recency_score(spot) * 0.15
        
        # 5. 信号质量（15 分）
        score += self._snr_score(spot) * 0.15
        
        return min(100, max(0, score))
```

**评分因素详解**：

| 因素 | 权重 | 数据来源 | 评分规则 |
|------|------|----------|----------|
| DXCC 稀有度 | 30% | cty.dat | 稀有国家/地区加分 |
| 传播条件 | 20% | hamqsl.com | SFI/K 指数动态调整 |
| 距离 | 20% | Grid 计算 | 与用户位置的 Grid 距离 |
| 时间窗口 | 15% | Spot 时间戳 | 近期热点加分 |
| 信号质量 | 15% | Cluster/PSK | SNR 越高越可能成功 |

**实施计划**：
| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建 `enhanced_scorer.py` 模块 | 0.5 天 |
| 2 | 集成 DXCC 稀有度数据库 | 0.25 天 |
| 3 | 集成传播条件计算 | 0.25 天 |
| 4 | 集成距离计算 | 0.25 天 |
| 5 | 更新评分 API 端点 | 0.25 天 |
| 6 | 编写单元测试 | 0.25 天 |
| 7 | 测试验证 | 0.25 天 |

**总计**：2 天

---

### 22.3 预警引擎 V3（优先级：P1）

**当前问题**：
- 固定阈值预警
- 单一条件触发
- 无预警分级

**改进方案**：

```python
# backend/alert_engine_v3.py
class AlertEngineV3:
    """预警引擎 V3（动态阈值）"""
    
    ALERT_LEVELS = {
        'critical': {'score_threshold': 80, 'color': '#ff4444'},
        'high': {'score_threshold': 60, 'color': '#ff8800'},
        'medium': {'score_threshold': 40, 'color': '#ffcc00'},
        'low': {'score_threshold': 20, 'color': '#44cc44'}
    }
    
    def evaluate(self, spot):
        """评估 Spot 是否需要预警"""
        score = self.scorer.score(spot)
        
        # 确定预警级别
        level = None
        for lvl, config in self.ALERT_LEVELS.items():
            if score >= config['score_threshold']:
                level = lvl
                break
        
        if not level:
            return None
        
        # 检查是否在关注列表
        is_watched = spot.get('callsign', '') in self.watchlist
        
        return {
            'callsign': spot.get('callsign', ''),
            'score': score,
            'level': level,
            'color': self.ALERT_LEVELS[level]['color'],
            'is_watched': is_watched,
            'spot': spot,
            'timestamp': time.time()
        }
```

**预警分级**：

| 级别 | 评分阈值 | 颜色 | 触发条件 |
|------|----------|------|----------|
| Critical | ≥80 | 🔴 红色 | 稀有 DX + 良好传播 + 近距离 |
| High | ≥60 | 🟠 橙色 | 稀有 DX + 一般传播 |
| Medium | ≥40 | 🟡 黄色 | 一般 DX + 良好传播 |
| Low | ≥20 | 🟢 绿色 | 普通 DX 活跃 |

**实施计划**：
| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建 `alert_engine_v3.py` 模块 | 0.5 天 |
| 2 | 集成评分引擎 | 0.25 天 |
| 3 | 更新预警 API 端点 | 0.25 天 |
| 4 | 前端预警显示优化 | 0.25 天 |
| 5 | 测试验证 | 0.25 天 |

**总计**：1.5 天

---

### 22.4 可选组件：本地转发代理（优先级：P3）

**说明**：作为可选组件提供，不集成到主应用。

```python
# scripts/wsjtx_forwarder.py（可选组件）
"""
WSJT-X UDP 数据转发代理（可选组件）

使用方法：
    python wsjtx_forwarder.py https://your-dx-guardian.com

功能：
    - 监听本地 WSJT-X UDP 端口 2237
    - 转发 decode 消息到远程 DX Guardian
    - 静默失败，不阻塞 WSJT-X
"""
```

**实施计划**：
| 步骤 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建转发代理脚本 | 0.5 天 |
| 2 | 添加使用说明文档 | 0.25 天 |
| 3 | 测试验证 | 0.25 天 |

**总计**：1 天（可选，不影响核心功能）

---

## 二十三、修改后开发计划

### 优先级排序

| 优先级 | 改进项 | 预计工时 | 说明 |
|--------|--------|----------|------|
| 🔴 P0 | 智能去重算法 | 1.75 天 | 核心功能，数据质量 |
| 🔴 P0 | 评分算法增强 | 2 天 | 核心功能，用户体验 |
| 🟡 P1 | 预警引擎 V3 | 1.5 天 | 核心功能 |
| 🟢 P2 | 数据源融合架构 | 0.5 天 | 架构优化 |
| 🟢 P3 | 本地转发代理脚本 | 1 天 | 可选组件 |

**总计**：6.75 天（不含可选组件）

### 与现有 MVP 计划的整合

| 现有 MVP | 整合改进项 | 影响 |
|----------|------------|------|
| MVP 1（实时 Spot 地图） | 智能去重算法 | 替换原有去重逻辑 |
| MVP 2（预警规则） | 预警引擎 V3 | 替换原有预警引擎 |
| MVP 4（机会评分） | 评分算法增强 | 替换原有评分引擎 |

**建议**：在对应 MVP 阶段实施改进，无需单独阶段。

---

## 二十四、总结

### 架构决策总结

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据源架构 | 方案 C（远程数据源） | 简洁、覆盖足够、符合定位 |
| 系统定位 | 纯分析系统 | 职责分离、降低风险、简化架构 |
| WSJT-X 集成 | 可选组件 | 用户按需部署，非核心功能 |

### 核心改进总结

| 模块 | 改进内容 | 优先级 |
|------|----------|--------|
| 去重算法 | 多源置信度去重 | P0 |
| 评分引擎 | 5 因素加权评分 | P0 |
| 预警引擎 | 动态阈值分级 | P1 |

### 下一步行动

1. **确认架构决策**：ADR-001、ADR-002 已记录
2. **实施 P0 改进**：智能去重 + 评分增强
3. **实施 P1 改进**：预警引擎 V3
4. **可选实施**：本地转发代理脚本

---

*开发计划书 v6.3（含架构决策记录 + PSK Reporter 地图分析）*  
*最后更新：2026-05-06*  
*核心改动：ADR-001 数据源架构决策、ADR-002 系统定位决策、核心模块改进计划*

---

## 二十五、参考网站分析：PSK Reporter 地图

### 25.1 PSK Reporter 地图概述

**网址**：`https://pskreporter.info/pskmap.html`

**定位**：全球 FT8/FT4 接收报告实时地图，展示解码台站位置和监听台分布。

### 25.2 数据来源

| 数据源 | 说明 | 占比 |
|--------|------|------|
| **WSJT-X** | 主要数据源，自动上报 FT8/FT4 解码结果 | ~80% |
| **JTDX** | 支持 PSK Reporter 协议 | ~10% |
| **FLdigi** | 支持 PSK Reporter 协议 | ~5% |
| **其他软件** | 支持协议的解码软件 | ~5% |

### 25.3 地图显示元素

| 元素 | 显示方式 | 说明 | 数据来源 |
|------|----------|------|----------|
| **发送台（被 Spot 的台）** | 彩色圆点 | 地图上显示的主要标记 | `senderCallsign` + `senderLocator` |
| **接收台（监听台）** | 大圆点/特殊图标 | "Large markers are monitors" | `callsign` + `receiverLocator` |
| **时间显示** | 时间戳/颜色渐变 | "Reception reports shown as times" | `flowStartSeconds` |
| **波段区分** | 颜色编码 | 不同波段用不同颜色 | `frequency` → 波段映射 |
| **模式区分** | 图标/颜色 | FT8/FT4/JS8 等 | `mode` |

### 25.4 API 数据字段与地图映射

| XML 字段 | 含义 | 地图用途 | 精度 |
|---------|------|----------|------|
| `senderCallsign` | 发送台呼号 | 标记标签 | - |
| `senderLocator` | 发送台 Grid | **精确坐标来源** | ±5km（4 字符） |
| `frequency` | 频率 (Hz) | 波段统计/颜色 | - |
| `mode` | 模式 | 图标/颜色区分 | - |
| `sNR` | 信噪比 | 可选：标记大小/透明度 | - |
| `callsign` | 接收台呼号 | 监听台标签 | - |
| `receiverLocator` | 接收台 Grid | 监听台位置 | ±5km |
| `flowStartSeconds` | UTC 时间戳 | 时间显示/排序 | - |
| `decoderSoftware` | 解码软件 | 可选：标记样式 | - |
| `rigInformation` | 电台信息 | 可选：tooltip | - |
| `antennaInformation` | 天线信息 | 可选：tooltip | - |

### 25.5 地图功能特点

| 功能 | 说明 | 实现方式 |
|------|------|----------|
| **时间范围选择** | 可设置显示最近 N 小时/天的数据 | 前端筛选 `flowStartSeconds` |
| **波段筛选** | 按波段过滤显示 | 前端按 `frequency` 过滤 |
| **模式筛选** | 按模式（FT8/FT4/JS8 等）过滤 | 前端按 `mode` 过滤 |
| **Grid 显示** | 基于 `senderLocator` 精确显示位置 | Grid → 经纬度转换 |
| **监听台标记** | 大圆点表示接收报告台 | 特殊标记样式 |
| **时间范围选择器** | 1 小时/6 小时/24 小时/7 天 | 前端 UI |
| **Permalink** | 分享当前视图链接 | URL 参数编码 |

### 25.6 与 DX Guardian 对比

| 特性 | PSK Reporter | DX Guardian（计划） |
|------|--------------|---------------------|
| **坐标精度** | Grid 中心点（±5km） | Grid 中心点（±5km） |
| **数据源** | WSJT-X 自动上报 | Cluster + PSK Reporter API |
| **实时性** | 近实时（上报延迟） | 5 分钟轮询 |
| **覆盖范围** | 全球 FT8/FT4 用户 | 全球（Cluster + PSK） |
| **显示元素** | 发送台 + 监听台 | 发送台 + 热力图 + 预警 |
| **筛选功能** | 波段/模式/时间 | 波段/模式/时间 + DXCC |
| **预警功能** | ❌ 无 | ✅ 有（关注列表匹配） |
| **评分功能** | ❌ 无 | ✅ 有（机会评分） |
| **日志集成** | ❌ 无 | ✅ 有（ADIF 上传） |

### 25.7 可借鉴的设计

#### 25.7.1 双标记系统

```javascript
// PSK Reporter 的双标记设计
// 发送台（小圆点）+ 监听台（大圆点）

function renderSpot(spot) {
    // 发送台：小圆点
    L.circle([spot.lat, spot.lon], {
        radius: 5000,  // 5km
        color: getModeColor(spot.mode),
        fillColor: getModeColor(spot.mode),
        fillOpacity: 0.6
    }).addTo(map);
    
    // 监听台：大圆点（如果显示监听台）
    if (showMonitors) {
        L.circle([spot.receiverLat, spot.receiverLon], {
            radius: 10000,  // 10km
            color: '#ff0000',
            fillColor: '#ff0000',
            fillOpacity: 0.3
        }).addTo(map);
    }
}
```

#### 25.7.2 时间可视化

```javascript
// 用颜色表示时间新旧
function getTimeColor(ageSeconds) {
    if (ageSeconds < 60) return '#00ff00';  // 绿色：1 分钟内
    if (ageSeconds < 300) return '#ffff00';  // 黄色：5 分钟内
    if (ageSeconds < 900) return '#ff8800';  // 橙色：15 分钟内
    return '#ff0000';  // 红色：超过 15 分钟
}
```

#### 25.7.3 Grid 精度显示

```javascript
// 直接用 senderLocator 坐标，无需额外解析
function renderWithGrid(spot) {
    if (spot.grid) {
        // 精确显示在 Grid 中心点
        const [lat, lon] = gridToLatLon(spot.grid);
        marker.setLatLng([lat, lon]);
        marker.bindTooltip(`Grid: ${spot.grid}`);
    } else {
        // 降级到 DXCC 中心坐标
        const [lat, lon] = getDXCCCoordinates(spot.callsign);
        marker.setLatLng([lat, lon]);
    }
}
```

### 25.8 DX Guardian 改进建议

基于 PSK Reporter 的设计，DX Guardian 可以借鉴：

| 改进项 | 说明 | 优先级 |
|--------|------|--------|
| **双标记系统** | 显示发送台 + 监听台（如果数据可用） | P2 |
| **时间颜色编码** | 用颜色表示 Spot 新旧 | P1 |
| **Grid 精度标记** | 优先使用 Grid 坐标，降级到 DXCC | P0（已有） |
| **时间范围选择器** | 1 小时/6 小时/24 小时/7 天 | P1 |
| **Permalink 分享** | 分享当前视图链接 | P3 |
| **Tooltip 信息** | 呼号 + Grid + 频率 + 模式 + 时间 | P1 |

### 25.9 数据来源差异说明

| 数据源 | 坐标精度 | 覆盖范围 | 实时性 |
|--------|----------|----------|--------|
| **PSK Reporter API** | ±5km（Grid） | FT8/FT4 用户 | 5 分钟轮询 |
| **DX Cluster** | ±500km（DXCC） | 所有模式 | 实时 |
| **WSJT-X UDP** | ±5km（Grid） | FT8/FT4 本地 | 实时（需本地代理） |

**建议**：优先使用 PSK Reporter 数据（Grid 精度），Cluster 作为补充（覆盖更多模式和区域）。

---

*附录：PSK Reporter 地图分析（2026-05-06）*

---

# DX Guardian - 开发计划书 v6.4（Wavelog 集成版）

> 版本：v6.4
> 日期：2026-05-07
> 更新：新增 Wavelog MySQL 直接调用、用户登录适配、界面主题适配
> 目标：与 Wavelog 深度集成，实现数据互通和界面统一

---

## 一、Wavelog 集成概述

- Wavelog 里有的数据直接调取，不再手动维护
- 用户登录、主题、页面布局与 Wavelog 一致

### 1.1 Wavelog 核心表

| 表名 | 用途 |
|------|------|
| users | 用户账户 |
| stations | 电台 station 配置 |
| qsos | QSO 日志记录 |
| qso_details | QSO 详细（如 RST、QTH） |
| lotw_users | LoTW 用户数据 |
| club_log_qsos | ClubLog 上传记录 |
| dxcc_entities | DXCC 实体表 |

### 1.2 数据同步策略

| 数据类型 | 来源 | 同步策略 |
|----------|------|----------|
| 用户信息 | users.station_callsign | 只读 |
| QSO 日志 | qsos | 只读 + 缓存 |
| DXCC 实体 | dxcc_entities / ClubLog API | 每日增量 |
| LoTW 状态 | lotw_users | 每周同步 |

---

## 二、数据库连接与数据映射

### 2.1 任务清单

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

### 3.2 任务清单

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 3.1 | Wavelog 用户认证集成 | 1天 | OAuth/密码认证 |
| 3.2 | 多 station 支持 | 0.5天 | 电台选择 |
| 3.3 | Session 共享 | 0.5天 | SSO 方案 |

---

## 四、界面主题适配

### 4.1 布局结构

```
┌─────────────────────────────────────────┐
│ Header (Logo + Nav + User)              │
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │      Main Content            │
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

### 4.3 任务清单

| 序号 | 任务 | 预计时间 | 交付物 |
|------|------|----------|--------|
| 4.1 | Wavelog 主题检测 | 0.5天 | 主题检测 |
| 4.2 | 颜色变量映射 | 0.5天 | CSS 变量 |
| 4.3 | 深色/浅色模式适配 | 1天 | 双主题 |
| 4.4 | 页面布局一致性 | 1天 | Header/Footer/Sidebar |

---

## 五、数据调用方式

| 数据类型 | 调用方式 | 用途 |
|----------|----------|------|
| 用户 station | MySQL 直接查询 | 多电台切换 |
| QSO 历史 | MySQL + 缓存 | 日志分析 |
| 已确认 DXCC | MySQL 查询 | 缺失 DXCC 计算 |
| ClubLog 上传 | ClubLog API | DXCC 状态验证 |
| LoTW 确认 | MySQL 查询 | LoTW 徽章显示 |

### 5.1 数据流架构

```
Wavelog MySQL ──→ DX Guardian API ──→ 前端展示
      │
      └─ 每日增量同步 → 本地缓存
```

---

## 六、集成目标

- Wavelog 用户可直接登录
- 界面主题与 Wavelog 一致
- 可直接读取 Wavelog 日志数据
- ClubLog DXCC 状态自动同步
- 不再需要手动维护用户数据

---

## 七、实施计划

| 阶段 | 时间 |
|------|------|
| 数据库连接 + 数据映射 | 4天 |
| 用户登录适配 | 2天 |
| 界面主题适配 | 3天 |
| 总计 | 5-7天 |

---

## 八、部署记录（2026-05-07）

- PHP 8.3.6 + Apache 2.4.58 安装
- Wavelog v2.4.1 源码部署到 /home/jacky/.openclaw/workspace/apps/wavelog
- 连接远程 MySQL 数据库（39.103.65.85:3306）
- 修复 MySQL 5.7 兼容性问题（upper() 函数）
- 配置 Apache 反向代理（/api/ → Flask:5000）
- 修复 assets 静态文件 404 问题

---

## 九、接口清单

| 文件 | 说明 |
|------|------|
| /application/controllers/Dxalert.php | 控制器 |
| /application/views/dxalert/content.php | 视图 |
| /dxalert_config.php | API 配置文件 |
| /application/config/config.php | 添加 api_url 配置 |

---

## 十、后续功能

- 用户告警配置界面
- 台站配置自动从 Wavelog 获取
- ADIF 日志上传功能
- 实时 Spot 推送通知
- 微信/Telegram 通知集成
