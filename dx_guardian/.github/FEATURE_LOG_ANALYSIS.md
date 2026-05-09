# DX Guardian 日志分析功能开发计划

**项目定位**: DX Guardian 作为 Wavelog 日志系统的分析模块

**数据源**:
1. 🟢 **主要**: Wavelog 日志系统 API（待对接）
2. 🟡 **测试**: wsjtx_log.adi 本地文件
3. 🟡 **备用**: ADIF 文件导入导出

---

## 一、架构设计

### 1.1 系统定位

```
┌──────────────────────────────────────────────┐
│         Wavelog 日志系统 (主系统)              │
├──────────────────────────────────────────────┤
│  DX Guardian Module (DX 机会分析模块)         │
│  ├─ 实时 Cluster  spotting                   │
│  ├─ 日志分析引擎                             │
│  ├─ DX 机会评分                               │
│  └─ 可视化报告                               │
└──────────────────────────────────────────────┘
```

### 1.2 数据流

```
Wavelog ADIF ──→ DX Guardian ──→ 分析报告
     ↓
wsjtx_log.adi (测试)
     ↓
分析引擎
     ↓
前端可视化
```

---

## 二、接口设计

### 2.1 Wavelog 日志系统接口（预留）

**配置项** (config.py):
```python
# Wavelog 集成配置
WAVELOG_LOG_API_URL = ""  # Wavelog API 端点，获取日志
WAVELOG_LOG_API_KEY = ""  # Wavelog API 密钥
WAVELOG_LOG_CALLSIGN = "" # 操作员呼号
WAVELOG_AUTO_SYNC = False # 自动同步日志
WAVELOG_SYNC_INTERVAL = 3600  # 同步间隔（秒）
```

**API 抽象层**:
```python
class LogSourceInterface:
    """日志源接口 - 支持多种数据源"""
    
    def get_logs(self, start_date, end_date):
        """获取指定日期范围的日志"""
        pass
    
    def get_stats(self):
        """获取统计摘要"""
        pass
    
    def export_adif(self):
        """导出为 ADIF 格式"""
        pass
```

**Wavelog 适配器**:
```python
class WavelogAdapter(LogSourceInterface):
    """Wavelog 适配器"""
    
    def __init__(self, api_url, api_key, callsign):
        self.api_url = api_url
        self.api_key = api_key
        self.callsign = callsign
    
    def get_logs(self, start_date, end_date):
        # 调用 Wavelog API
        response = requests.get(
            f"{self.api_url}/api/contacts",
            params={
                'start': start_date,
                'end': end_date,
                'callsign': self.callsign
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return response.json()
```

### 2.2 本地文件接口（已实现）

**支持格式**:
- wsjtx_log.adi (JTDX/WSJT-X 日志)
- *.adi / *.adif (标准 ADIF)
- CSV (可选)

**文件位置**:
- 测试：/workspace/dx_guardian/wsjtx_log.adi
- 用户导入：/workspace/dx_guardian/backend/user_logs/

**文件监控** (可选功能):
```python
class LocalFileWatcher:
    """监控本地日志文件变化"""
    
    def watch(filepath, callback):
        # 监听文件变化，自动重新分析
        pass
```

### 2.3 数据库接口（已有）

**现有数据库**:
- backend/dx_spots.db (实时 Spot)
- backend/logs/ (用户导入的日志)

**新增缓存表**:
```sql
CREATE TABLE log_analysis_cache (
    log_id TEXT PRIMARY KEY,
    source_type TEXT,  -- 'wavelog' | 'adi_file' | 'wsjtx_log'
    analysis_json TEXT,
    created_at REAL,
    expires_at REAL
);

CREATE TABLE user_log_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    callsign TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    stat_type TEXT NOT NULL,
    stat_data TEXT,
    source_type TEXT,  -- 数据来源
    UNIQUE(callsign, stat_date, stat_type)
);
```

---

## 三、功能模块

### 3.1 数据源管理（新增）

**页面**: `/admin/log-sources`

**功能**:
- [ ] 配置 Wavelog API 连接
- [ ] 测试连接
- [ ] 手动同步按钮
- [ ] 查看同步状态
- [ ] 管理本地 ADIF 文件
- [ ] 监控 wsjtx_log.adi 文件

**API**:
```
GET    /api/admin/log-sources      # 获取数据源列表
POST   /api/admin/log-sources      # 添加数据源
PUT    /api/admin/log-sources/:id  # 更新配置
DELETE /api/admin/log-sources/:id  # 删除数据源
POST   /api/admin/log-sources/sync # 手动同步
GET    /api/admin/log-sources/status # 同步状态
```

### 3.2 日志导入增强（修改现有）

**当前**: `/api/user/logs/import`

**增强后**:
```python
@app.route('/api/user/logs/import', methods=['POST'])
def api_import_logs():
    # 支持多种来源
    source_type = request.form.get('source', 'file')
    
    if source_type == 'wavelog':
        # 从 Wavelog API 导入
        return import_from_wavelog()
    elif source_type == 'wsjtx':
        # 从 wsjtx_log.adi 导入
        return import_wsjtx_log()
    else:
        # 从上传文件导入
        return import_from_file()
```

### 3.3 日志分析引擎（核心）

**文件**: `backend/log_analyzer.py` (新建)

**分析维度**:
1. **基础统计**
   - 总 QSO 数
   - 唯一电台数
   - DXCC 实体数
   - Grid 数

2. **DXCC 分析**
   - 大洲分布
   - 国家排名
   - 稀有度统计
   - 缺失推荐

3. **波段分析**
   - 波段分布
   - 波段效率
   - 最佳 DX 波段
   - 波段建议

4. **模式分析**
   - 模式分布
   - 数字 vs 模拟
   - 模式推荐

5. **时间分析**
   - 24 小时分布
   - 月度趋势
   - 季节分析

**输出格式**:
```json
{
  "source": "wsjtx_log.adi",
  "callsign": "BG2ENW",
  "date_range": {
    "first": "2026-05-04 02:54",
    "last": "2026-05-05 02:54"
  },
  "summary": {
    "total_qso": 10,
    "unique_calls": 10,
    "unique_dxcc": 10,
    "unique_grids": 10
  },
  "dxcc_distribution": {
    "by_continent": {...},
    "top_10": [...],
    "rarity": {...}
  },
  "band_analysis": {...},
  "mode_analysis": {...},
  "time_analysis": {...},
  "recommendations": [...]
}
```

### 3.4 可视化仪表板

**页面**: `/logs/:id/analysis`

**组件**:
1. 概览卡片（4 个关键指标）
2. DXCC 分布饼图
3. 波段使用柱状图
4. 模式分布环形图
5. 24 小时热力图
6. 世界地图标记

**技术栈**:
- Chart.js v4.x（轻量、易用）
- Leaflet（已有，用于地图）
- 原生 HTML/CSS/JS

---

## 四、实施步骤

### Step 1: 数据层（0.5 天）
- [ ] 创建分析缓存表
- [ ] 创建统计表
- [ ] 创建 wsjtx_log.adi 文件（示例数据）

### Step 2: 分析引擎（1 天）
- [ ] 实现 LogSourceInterface 接口
- [ ] 实现 ADIF 适配器
- [ ] 实现 WsjtxLog 适配器
- [ ] 实现基础统计模块
- [ ] 实现 DXCC 分析模块
- [ ] 实现波段分析模块
- [ ] 实现模式分析模块

### Step 3: 分析 API（0.5 天）
- [ ] GET /api/user/logs/:id/analysis
- [ ] GET /api/user/logs/:id/analysis/dxcc
- [ ] GET /api/user/logs/:id/analysis/bands
- [ ] GET /api/user/logs/:id/analysis/modes
- [ ] 增强导入 API 返回分析结果

### Step 4: 前端可视化（1.5 天）
- [ ] 集成 Chart.js
- [ ] 创建分析页面模板
- [ ] 实现概览卡片
- [ ] 实现 DXCC 饼图
- [ ] 实现波段柱状图
- [ ] 实现模式环形图
- [ ] 实现时间热力图

### Step 5: Wavelog 适配器（1 天）
- [ ] 实现 WavelogAdapter
- [ ] 配置 WAVELOG_* 环境变量
- [ ] 测试 API 连接
- [ ] 实现自动同步（可选）

### Step 6: 测试优化（0.5 天）
- [ ] 单元测试
- [ ] 使用 wsjtx_log.adi 测试全流程
- [ ] 性能优化
- [ ] 文档更新

**总计**: 5 个工作日

---

## 五、API 设计

### 5.1 数据源管理 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/admin/log-sources` | GET | 获取数据源列表 |
| `/api/admin/log-sources` | POST | 添加数据源 |
| `/api/admin/log-sources/:id` | PUT | 更新配置 |
| `/api/admin/log-sources/sync` | POST | 手动同步 |

### 5.2 日志分析 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/user/logs/:id/analysis` | GET | 获取完整分析 |
| `/api/user/logs/:id/analysis/dxcc` | GET | DXCC 分析 |
| `/api/user/logs/:id/analysis/bands` | GET | 波段分析 |
| `/api/user/logs/:id/analysis/modes` | GET | 模式分析 |
| `/api/user/logs/:id/analysis/time` | GET | 时间分析 |
| `/api/user/logs/analyze/file` | POST | 上传文件并分析 |

### 5.3 导入导出 API（增强）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/user/logs/import` | POST | 导入（支持多来源） |
| `/api/user/logs/export` | GET | 导出 ADIF |
| `/api/user/logs/wsjtx/sync` | POST | 同步 wsjtx_log.adi |

---

## 六、测试计划

### 6.1 测试数据源

**wsjtx_log.adi** (主要测试文件):
- 位置：/workspace/dx_guardian/wsjtx_log.adi
- 内容：10 条示例 QSO
- 覆盖：8 个波段，5 种模式，10 个 DXCC

**测试场景**:
1. 导入 wsjtx_log.adi → 验证解析正确
2. 分析数据 → 验证统计准确
3. 生成报告 → 验证可视化正常
4. 导出 ADIF → 验证格式标准

### 6.2 单元测试

```python
# tests/test_log_analyzer.py
class TestLogAnalyzer(unittest.TestCase):
    
    def test_parse_wsjtx_log(self):
        """测试 WSJTX 日志解析"""
        parser = WSJTXLogParser('wsjtx_log.adi')
        qso_list = parser.parse()
        self.assertEqual(len(qso_list), 10)
    
    def test_dxcc_analysis(self):
        """测试 DXCC 分析"""
        analyzer = LogAnalyzer()
        analysis = analyzer.analyze_dxcc(qso_list)
        self.assertEqual(analysis['total_dxcc'], 10)
    
    def test_band_analysis(self):
        """测试波段分析"""
        # ...
```

### 6.3 集成测试

1. **完整流程测试**
   ```
   wsjtx_log.adi → 导入 → 分析 → 可视化 → 导出
   ```

2. **Wavelog 集成测试**（预留）
   ```
   Wavelog API → 同步 → 分析 → 对比 → 报告
   ```

---

## 七、验收标准

### 功能验收
- [ ] wsjtx_log.adi 正确解析
- [ ] 导入后 3 秒内显示统计
- [ ] 分析数据准确
- [ ] 图表正确渲染
- [ ] 报告可打印

### 性能验收
- [ ] 1 万条 QSO 分析 < 5 秒
- [ ] 缓存命中率 > 80%
- [ ] 页面加载 < 2 秒

### 接口验收
- [ ] Wavelog 接口预留正确
- [ ] 适配器模式易于扩展
- [ ] 配置项完整

---

## 八、文件结构

```
backend/
├── log_analyzer.py          # 日志分析引擎（新建）
├── adapters/                # 数据源适配器（新建）
│   ├── __init__.py
│   ├── base.py             # LogSourceInterface
│   ├── wsjtx.py            # WSJTX 适配器
│   ├── adif.py             # ADIF 适配器
│   └── wavelog.py          # Wavelog 适配器（预留）
├── analysis_cache.py        # 分析缓存（新建）
└── app.py                   # 增强导入 API

frontend/
├── js/
│   ├── log_analysis.js     # 日志分析逻辑（新建）
│   └── charts/             # 图表组件（新建）
│       ├── dxcc_chart.js
│       ├── band_chart.js
│       └── mode_chart.js
└── pages/
    └── log_analysis.html   # 分析页面（新建）

tests/
├── test_log_analyzer.py    # 分析引擎测试
├── test_adapters.py        # 适配器测试
└── test_integration.py     # 集成测试

docs/
└── LOG_ANALYSIS.md         # 本文档
```

---

## 九、立即可做

### 优先级 P0（今天可完成）

1. ✅ **wsjtx_log.adi 示例数据** - 已创建
2. 📝 **LogSourceInterface 接口** - 1 小时
3. 📝 **WSJTX 适配器** - 2 小时
4. 📝 **基础统计分析** - 2 小时
5. 📝 **导入 API 增强** - 1 小时
6. 📝 **简单前端展示** - 2 小时

**总计**: 8 小时（1 个工作日）

**产出**:
- 可以上传 wsjtx_log.adi
- 导入后立即显示统计摘要
- 简单的数字展示（QSO 数、DXCC 数等）

### 优先级 P1（明天）

1. DXCC/波段/模式分析
2. Chart.js 集成
3. 可视化图表

### 优先级 P2（后天）

1. 完整仪表板
2. 时间热力图
3. 世界地图

### 优先级 P3（后续）

1. Wavelog 适配器实现
2. 自动同步
3. 日志对比

---

**文档版本**: v2.0  
**创建日期**: 2026-05-05  
**项目定位**: Wavelog 日志系统分析模块  
**测试数据**: wsjtx_log.adi  
**下一步**: 开始实施 P0 功能

