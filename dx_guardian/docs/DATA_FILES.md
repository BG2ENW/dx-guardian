# DX Guardian 数据文件说明

## Data 目录结构

```
dx_guardian/
├── data/                          # 主要数据目录
│   └── prefix_to_dxcc.json        # DXCC 前缀到国家坐标映射 (62 个前缀)
├── backend/
│   └── data/                      # 后端运行时数据
│       ├── alerts.json            # 预警历史记录
│       └── silenced_callsigns.json # 静默呼号列表
└── frontend/
    └── data/                      # (无数据文件)
```

## 关键数据文件

### prefix_to_dxcc.json

**位置**: `/workspace/dx_guardian/data/prefix_to_dxcc.json`

**用途**: 将呼号前缀映射到 DXCC 实体名称和中心坐标

**数据结构**:
```json
{
  "BG": {"dxcc": "China", "lat": 35.8, "lon": 104.1},
  "JA": {"dxcc": "Japan", "lat": 36.2, "lon": 138.2},
  "DL": {"dxcc": "Germany", "lat": 51.1, "lon": 10.4}
}
```

**当前规模**: 62 个常见前缀

**坐标来源**: 各国地理中心（近似值）

## 电台位置显示精度

### 三级解析策略

电台在地图上的位置通过 `coordinate_resolver.py` 的三级策略解析：

#### 1. Grid 方格 (最精确)
- **精度**: ±5km (6 位 Grid)
- **来源**: Cluster 数据中的 Grid 字段
- **显示**: 绿色小圆点 (10px)

#### 2. 远程呼号查询
- **精度**: ±5km (6 位 Grid)
- **来源**: QRZ.com / HamQTH API
- **显示**: 绿色小圆点 (10px)

#### 3. DXCC 国家中心 (兜底)
- **精度**: ±500km (国家中心 + 随机偏移)
- **来源**: `prefix_to_dxcc.json`
- **显示**: 标准圆点 (14px)

### 位置显示问题排查

如果地图上电台位置不准确，可能原因：

1. **Cluster 未提供 Grid** → 降级到 DXCC 中心坐标
2. **前缀不在数据库中** → 显示 (0, 0) 无坐标
3. **呼号查询超时** → 降级到 DXCC 中心坐标

### 解决方案

1. **扩展前缀数据库**: 编辑 `data/prefix_to_dxcc.json` 添加更多前缀
2. **启用 Grid 显示**: 点击地图上的📐网格按钮，显示 Maidenhead Grid
3. **查看精确 Grid**: 点击电台标记，tooltip 显示 Grid 坐标

## Maidenhead Grid 网格显示

### 功能说明

- **Zoom 2-5**: 显示 Field 网格 (20° × 10°)
- **Zoom 6-9**: 显示 Square 网格 (2° × 1°)  
- **Zoom 10+**: 显示 Enhanced 子网格 (0.5° × 0.5°)

### 网格坐标计算

中心显示的 6 位 Grid 计算公式：
- Field: (经度 +180)/20, (纬度 +90)/10 → 字母 A-X
- Square: 余数/2, 余数/1 → 数字 0-9
- Enhanced: 余数/0.08333, 余数/0.04166 → 字母 a-x

### 使用场景

- 判断传播路径方向
- 估算实际距离
- 识别同一 Grid 内的多个电台
- 规划波段选择

## 数据更新

### 手动更新 DXCC 数据库

1. 访问 DXCC 官方实体列表
2. 获取国家/地区中心坐标
3. 编辑 `data/prefix_to_dxcc.json` 添加前缀映射
4. 重启后端服务

### 自动更新 Grid

- Cluster 数据中的 Grid 字段自动解析
- 无需手动干预

## 相关文件

- `backend/coordinate_resolver.py` - 坐标解析模块
- `backend/spot_parser.py` - Grid 字段提取
- `frontend/js/app.js` - 地图网格渲染
