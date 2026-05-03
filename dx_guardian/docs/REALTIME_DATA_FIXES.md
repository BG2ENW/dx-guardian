# 实时数据接入修复计划

## 当前状态 (2026-05-03 04:54)

| 数据源 | 状态 | 问题 |
|--------|------|------|
| DX Cluster | ✅ 已连接 | 无数据接收？ |
| PSKReporter | ✅ 已启动 | 5 分钟间隔，等待首次拉取 |
| 太阳数据 | ✅ 正常 | SFI=0 SN=0 K=3 A=7 |
| 历史缓存 | ❌ 空 | 0 条 spot |
| DXCC 库 | ❌ 缺失 | `/workspace/dx_guardian/data/prefix_to_dxcc.json` |

| API 端点 | 状态 | 返回数据 |
|---------|------|---------|
| `/api/history` | ⚠️ 空 | 0 条 |
| `/api/stats/solar` | ✅ 正常 | 有数据 |
| `/api/propagation` | ✅ 正常 | 10 波段 |
| `/api/trends` | ⚠️ 空 | 0 波段 |
| `/api/band-opening` | ✅ 正常 | 24 小时 |
| `/api/voacap/best-bands` | ⚠️ 空 | 0 波段 |

## 待修复问题

### 1. DXCC 前缀库缺失
**文件**: `data/prefix_to_dxcc.json`
**影响**: 坐标解析、国家/地区识别
**解决**: 
- 方案 A: 生成最小化前缀库
- 方案 B: 代码降级处理（无 DXCC 时使用默认值）

### 2. Cluster 数据接收
**现象**: 已登录但无数据
**可能原因**:
- Cluster 服务器本身无流量
- 解析逻辑有问题
- 限流/去重过于严格

### 3. 趋势分析无数据
**原因**: 依赖历史缓存数据
**解决**: 先修复数据源接入

### 4. VOACAP 无推荐波段
**原因**: 可能需要台站配置
**解决**: 检查台站配置和 VOACAP 计算逻辑

## 修复步骤

### Phase 1: 基础设施修复
- [ ] 创建 DXCC 前缀库（最小化版本）
- [ ] 验证坐标解析功能
- [ ] 检查 Cluster 限流配置

### Phase 2: 数据源接入
- [ ] 验证 Cluster 数据接收
- [ ] 等待 PSKReporter 首次拉取
- [ ] 检查 spot 去重逻辑

### Phase 3: 数据分析
- [ ] 趋势分析数据填充
- [ ] VOACAP 波段推荐
- [ ] 机会评分生成

### Phase 4: 前端实时
- [ ] WebSocket 实时更新验证
- [ ] 前端数据刷新
- [ ] 地图标记动态更新

## 调试命令

```bash
# 查看后端日志
tail -f /tmp/backend.log | grep -E "Cluster|PSK|spots|spot"

# 检查 API 数据
curl http://localhost:5000/api/history | jq '.spots | length'
curl http://localhost:5000/api/stats/solar | jq '.data'

# 检查 Cluster 连接
ps aux | grep cluster
```
