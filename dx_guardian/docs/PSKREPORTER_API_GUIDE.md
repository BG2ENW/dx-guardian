# PSKReporter API 使用说明

## 官方 API 地址

```
https://retrieve.pskreporter.info/query
```

## 调用限制（重要）

| 限制项 | 官方要求 | 当前配置 | 状态 |
|--------|---------|---------|------|
| **查询间隔** | ≥5 分钟（300 秒） | 310 秒 | ✅ 合规 |
| **返回数量** | ≤100 条 | 100 条 | ✅ 合规 |
| **时间范围** | ≥-24 小时 | -300 秒（5 分钟） | ✅ 合规 |
| **联系邮箱** | 建议添加 | bg2enw@163.com | ✅ 已添加 |

## API 参数说明

### 必需参数
- `flowStartSeconds`：查询的时间范围（负数表示从当前时间往前推）
  - 最大值：-86400（24 小时）
  - 当前使用：-300（5 分钟）
  
### 推荐参数
- `rptlimit`：返回的报告数量（**不是 `limit`**）
  - 默认值：100
  - 当前配置：100
  
- `noactive=1`：不返回活跃监听台列表（减少数据量）
- `rronly=1`：只返回接收报告（reception reports）

- `appcontact`：管理员联系邮箱（官方建议添加）
  - 当前配置：bg2enw@163.com

## 请求示例

```bash
curl "https://retrieve.pskreporter.info/query?flowStartSeconds=-300&noactive=1&rronly=1&rptlimit=100&appcontact=bg2enw@163.com"
```

## Python 实现

```python
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

def fetch_pskreporter_data():
    """从 PSKReporter 获取全球接收报告"""
    
    # 构建请求 URL
    url = (f'https://retrieve.pskreporter.info/query?'
           f'flowStartSeconds=-300'  # 最近 5 分钟
           f'&noactive=1&rronly=1'   # 只返回接收报告
           f'&rptlimit=100'          # 最多 100 条
           f'&appcontact=bg2enw@163.com')
    
    # 发送请求
    headers = {'User-Agent': 'DXGuardian/1.0 (BG2ENW)'}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        xml_data = resp.read().decode('utf-8', errors='ignore')
    
    # 解析 XML
    root = ET.fromstring(xml_data)
    for recv in root.findall('.//receptionReport'):
        sender_callsign = recv.get('senderCallsign', '').strip().upper()
        frequency_hz = int(recv.get('frequency', '0'))
        mode = recv.get('mode', 'FT8')
        grid = recv.get('senderLocator', '')
        snr = recv.get('sNR', '')
        
        # 处理数据...
        print(f'{sender_callsign}: {frequency_hz/1e6:.3f} MHz {mode} [SNR:{snr}]')
```

## 响应 XML 结构

```xml
<reportingData lastSeqNo="12345">
  <receptionReport>
    <!-- 发送台（被接收到的台）--->
    <senderCallsign>JA1AAA</senderCallsign>
    <senderLocator>PM95</senderLocator>
    
    <!-- 频率和模式 -->
    <frequency>14074300</frequency>
    <mode>FT8</mode>
    
    <!-- 信号报告 -->
    <sNR>12.5</sNR>
    
    <!-- 接收台信息 -->
    <callsign>BG2ENW</callsign>
    <receiverLocator>PN35HS</receiverLocator>
    
    <!-- 设备信息 -->
    <decoderSoftware>WSJT-X 2.7.0</decoderSoftware>
    <rigInformation>IC-7300</rigInformation>
    <antennaInformation>DP-80m</antennaInformation>
    
    <!-- 时间戳 -->
    <flowStartSeconds>1777782000</flowStartSeconds>
  </receptionReport>
</reportingData>
```

## 字段对照表

| XML 字段 | 含义 | 用途 |
|---------|------|------|
| `senderCallsign` | 发送台呼号 | 地图上显示的台站 |
| `senderLocator` | 发送台 Grid | 用于地理编码 |
| `callsign` | 接收台呼号 | 收到信号的台 |
| `receiverLocator` | 接收台 Grid | 可用于传播分析 |
| `frequency` | 频率（Hz） | 波段统计 |
| `mode` | 模式 | FT8/FT4/SSB等 |
| `sNR` | 信噪比 | 信号质量 |
| `flowStartSeconds` | UTC 时间戳 | 用于时间筛选 |
| `decoderSoftware` | 解码软件 | WSJT-X 等 |
| `rigInformation` | 设备信息 | 电台型号 |
| `antennaInformation` | 天线信息 | 天线类型 |

## 错误处理

### HTTP 403 Forbidden（限流）
```
如果收到403错误，说明请求过于频繁
解决方法：增加查询间隔至≥300秒
```

### HTTP 400 Bad Request
```
通常是参数错误
检查：是否使用了rptlimit而不是limit
```

### 连接超时
```python
try:
    # 请求代码
except urllib.error.URLError as e:
    # 超时处理，等待后重试
    time.sleep(60)
```

## 最佳实践

1. **查询频率**：设置间隔为 310 秒（留 10 秒余量）
2. **数据量控制**：`rptlimit=100` 足以满足实时监控需求
3. **时间范围**：`flowStartSeconds=-300` 只获取最近 5 分钟
4. **减少数据**：添加 `noactive=1` 不获取监听台列表
5. **联系方式**：添加 `appcontact` 便于官方联系
6. **User-Agent**：明确标识应用和呼号

## 违规后果

- 频繁调用会被 IP 限流（HTTP 403）
- 可能导致长期封禁
- 影响整个 PSKReporter 生态

## 相关资源

- [PSKReporter 官方网站](https://pskreporter.info/)
- [PSKReporter 开发者说明](https://pskreporter.info/developers) (需要绕过 Cloudflare)
- [PSK Reporter Wiki](https://pskreporter.info/pskfaq.html)

## 当前实现位置

- 后端配置：`/workspace/dx_guardian/backend/app.py`
- 配置常量：
  - `PSKREPORTER_INTERVAL = 310` （查询间隔）
  - `PSKREPORTER_LIMIT = 100` （返回数量）
- 实现函数：`pskreporter_thread()`（第 626 行）
- 启动位置：主线程启动时作为 daemon 线程运行

## 监控和维护

### 日志检查
```bash
tail -f /tmp/backend.log | grep PSKReporter
```

### 查看最近调用时间
```bash
grep -E "PSKReporter.*成功|PSKReporter.*失败" /tmp/backend.log | tail -20
```

### 被限流时的日志
```
[PSKReporter] ⏳ 被限流，等待 10 分钟后重试
```

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 长时问无数据 | 被限流 | 检查查询间隔，等待 10 分钟 |
| XML 解析失败 | 响应格式变化 | 检查官方 API 是否更新 |
| 频率异常 | 参数错误 | 确认 flowStartSeconds 格式 |
| 连接超时 | 网络问题 | 增加 timeout，添加重试逻辑 |
