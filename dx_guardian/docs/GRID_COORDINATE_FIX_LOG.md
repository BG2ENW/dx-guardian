# Grid 坐标解析修复日志

**日期**: 2026-05-03  
**分支**: 260502-chore-secure-config-secrets

## 问题背景

用户报告电台位置显示错误，多个电台坐标显示在错误的位置（如海里、错误国家）。

## 发现的问题

### 1. CTY.DAT 数据库损坏
- **问题**: `/workspace/dx_guardian/data/cty.dat` 仅 14 字节（损坏）
- **修复**: 从 `/workspace/cty.dat` 恢复完整文件（347KB，317 个实体，21,326 个前缀）

### 2. CTY 前缀解析错误
- **问题**: 操作员前缀含 `/` 时（如 `EA/FT5YK`），错误提取 `EA` 导致西班牙被覆盖为福克兰群岛
- **修复**: `cty_parser.py` 中忽略含 `/` 的前缀
- **效果**: 前缀数量从 26,895 减少到 21,326（移除无效操作员前缀）

### 3. Grid 中心点计算错误
- **问题**: Grid 坐标显示在角落而不是中心点
- **修复**: `_grid_to_latlon()` 添加半格偏移量
  - Square: +1°纬度，+0.5°经度
  - Subsquare: +2.5'纬度，+1.25'经度

### 4. Spot 正则表达式不区分大小写
- **问题**: Grid 正则 `[A-R]{2}` 不匹配小写 `ol62wx`
- **修复**: `spot_parser.py` 中添加 `re.IGNORECASE` 标志

### 5. Spot comment 提取失败
- **问题**: 正则未正确捕获 timestamp 前的完整 comment
- **修复**: 修改 regex pattern 捕获 `\d{4}Z` 前的所有内容

### 6. CTY/DXCC 反推假 Grid
- **问题**: 无真实 Grid 时，用 lat/lon 反推 Grid（偏差几十公里）
- **修复**: CTY/DXCC 分支不再反推 Grid，保持 `grid=None`
- **效果**: 只显示真实 Grid（来自 Spot comment、JTDX DB、PSK Reporter）

### 7. PSK Reporter 历史 Grid 查询
- **新增**: `find_psk_grid_for_callsign()` 函数
- **功能**: Cluster Spot 无 Grid 时，查询历史缓存中的 PSK Reporter Grid
- **优先级**: Spot Grid → PSK Reporter 历史 → JTDX DB → CTY

### 8. Grid 显示逻辑
- **修改**: `coordinate_resolver.py` 中 CTY/DXCC 不返回反推 Grid
- **前端**: 只有真实 Grid 才显示 `📍 Grid: XXXX`
- **效果**: 避免显示不准确的估算 Grid

## 修改的文件

### 后端
1. `dx_guardian/backend/spot_parser.py`
   - Grid 正则添加 `re.IGNORECASE`
   - comment 捕获完整内容

2. `dx_guardian/backend/coordinate_resolver.py`
   - `_grid_to_latlon()` 添加半格偏移
   - CTY 分支不反推 Grid
   - DXCC 分支不反推 Grid
   - 中国省份中心点优化

3. `dx_guardian/backend/cty_parser.py`
   - 忽略含 `/` 的操作员前缀

4. `dx_guardian/backend/app.py`
   - `find_psk_grid_for_callsign()` 新函数
   - `process_spot()` 优先查询 PSK Reporter 历史 Grid
   - 坐标解析调试日志

5. `dx_guardian/backend/grid_database.py` (新建)
   - JTDX Grid 数据库加载和查询

6. `dx_guardian/backend/data/china_callsign_grid_map.json` (新建)
   - 67 条中国常见呼号 Grid 映射

7. `dx_guardian/backend/data/grid_callsign_map_extracted.json` (新建)
   - 29,950 条 JTDX 呼号-Grid 映射

### 前端
1. `dx_guardian/frontend/js/app.js`
   - Grid 显示逻辑调试日志
   - 版本号 v=1.7

2. `dx_guardian/frontend/index.html`
   - 版本号 v=1.7

### 数据文件
1. `dx_guardian/data/cty.dat` - 恢复完整版（347KB）
2. `dx_guardian/data/lotw-user-activity.csv` - LoTW 活跃用户数据库

## 坐标解析优先级

1. **Spot Grid**（来自 Cluster comment 或 PSK Reporter）→ precision=grid
2. **JTDX 数据库**（29,950 条历史 Grid）→ precision=grid_db
3. **中国常见呼号 Grid**（67 条）→ precision=china_grid
4. **CTY.DAT**（前缀查询，不反推 Grid）→ precision=cty, grid=None
5. **DXCC 兜底**（62 个前缀）→ precision=dxcc, grid=None

## 已知限制

### PSK Reporter API 阻挡
- **问题**: PSK Reporter API 使用 Cloudflare 保护，Python urllib 无法通过 JavaScript 验证
- **影响**: 无法实时获取 PSK Reporter Grid 数据
- **现状**: 依赖 Cluster Spot comment 中的 Grid（约 50% 的 Spot 带 Grid）

### Cluster Spot 无 Grid
- **原因**: DX Cluster 发射台自行决定是否发送 Grid
- **示例**: `US1EA -3 dB CQ`（无 Grid）vs `R9CA -22 dB LO97 CQ`（有 Grid）
- **解决**: 仅显示真实 Grid，不反推估算值

## 验证结果

### 正确的 Grid 显示
```
R9CA    Grid=LO97  precision=grid  lat=57.50 lon=59.00  ✅
UA3LKM  Grid=KO65  precision=grid  lat=55.50 lon=33.00  ✅
IK4LZH  Grid=JN54  precision=grid  lat=44.50 lon=11.00  ✅
ZL1VAH  Grid=RF72  precision=grid  lat=-37.50 lon=175.00 ✅
```

### 无 Grid 的情况
```
US1EA   Grid=None  precision=cty   Cluster comment 无 Grid
JH1QQN  Grid=None  precision=cty   JTDX DB 无此呼号
JR6CSY  Grid=None  precision=cty   PSK Reporter 还没收到
```

## 测试命令

```bash
# 查看 Grid 提取日志
grep "坐标" /tmp/backend.log | grep "precision=grid"

# 检查 API 返回数据
curl -s http://localhost:5000/api/history | python3 -c "
import sys,json
d=json.load(sys.stdin)
ft8_with_grid=[s for s in d.get('spots',[]) if 'FT8' in s.get('mode','') and s.get('grid')]
print(f'FT8 带 Grid: {len(ft8_with_grid)} 个')
"

# 查看前端调试日志
浏览器 F12 控制台搜索 "DEBUG"
```

## 后续优化

1. **PSK Reporter 绕过 Cloudflare**: 考虑使用 Selenium 或 requests-html
2. **增加 Grid 来源标注**: 前端显示 `Grid来源: Spot/PSK/JTDX`
3. **Grid 数据库更新**: 定期同步 JTDX grid_data.bin

