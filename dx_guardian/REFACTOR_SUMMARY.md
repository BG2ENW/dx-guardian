# DX Guardian 后端重构说明

## 重构概述

本次重构将 `backend/app.py` 从单体架构拆分为多个按领域划分的路由模块，提升代码可维护性和可测试性。

## 拆分前后对比

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| `app.py` 行数 | ~1682 行 | ~850 行 | -50% |
| 路由模块 | 0 个 | 6 个 | +6 |
| 单元测试 | 0 个 | 10 个 | +10 |
| Docker 容器化 | ❌ | ✅ | +Dockerfile |
| CI/CD | ❌ | ✅ | +GitHub Actions |
| 配置检查脚本 | ❌ | ✅ | +check_prod_config.py |

## 新增模块清单

### 1. `wavelog_routes.py`
**职责**：Wavelog 第三方集成  
**接口**：
- `GET /api/wavelog_station` - 获取台站配置
- `GET /api/wavelog_stats` - 获取 QSO 统计
- `GET /api/wavelog_lookup/<callsign>` - 查询呼号通联状态

**注册方式**：
```python
register_wavelog_routes(app, {
    'log': log,
    'external_api_error': _external_api_error,
    'external_failure_payload': _external_failure_payload,
    'my_call': MY_CALL,
    'wavelog_url': WAVELOG_URL,
    'wavelog_api_key': WAVELOG_API_KEY,
})
```

---

### 2. `push_routes.py`
**职责**：Web Push 推送通知  
**接口**：
- `GET /api/push/public_key` - 获取 VAPID 公钥
- `POST /api/push/subscribe` - 订阅推送
- `POST /api/push/unsubscribe` - 取消订阅
- `POST /api/push/test` - 测试推送
- `GET /api/push/status` - 查看推送状态

**注册方式**：
```python
register_push_routes(app, {
    'log': log,
    'external_api_error': _external_api_error,
    'vapid_public_key': VAPID_PUBLIC_KEY,
    'vapid_private_key_pem': VAPID_PRIVATE_KEY_PEM,
    'vapid_email': VAPID_EMAIL,
})
```

---

### 3. `watchlist_routes.py`
**职责**：用户关注列表管理  
**接口**：
- `GET /api/user/watchlist` - 获取关注列表
- `POST /api/user/watchlist` - 添加关注项
- `PUT /DELETE /api/user/watchlist/<item_id>` - 更新/删除关注项
- `POST /api/user/watchlist/import` - 批量导入

**注册方式**：
```python
register_watchlist_routes(app, {'log': log})
```

---

### 4. `station_routes.py`
**职责**：台站配置管理  
**接口**：
- `GET /api/user/station` - 获取台站配置
- `PUT /api/user/station` - 更新台站配置

**注册方式**：
```python
register_station_routes(app, {
    'log': log,
    're_module': re_module,
    'get_scorer': lambda: scorer,
})
```

---

### 5. `log_routes.py`
**职责**：日志上传/解析/验证  
**接口**：
- `POST /api/user/logs/upload` - 上传日志文件
- `GET /api/user/logs` - 获取日志列表
- `DELETE /api/user/logs/<log_id>` - 删除日志
- `GET /api/score/validate` - 验证评分准确性

**注册方式**：
```python
register_log_routes(app, {
    'log': log,
    'get_scorer': lambda: scorer,
    'lock': lock,
    'get_spot_history': lambda: spot_history,
    'get_band_counts': lambda: band_counts,
    'get_total_spots': lambda: total_spots,
    'solar_data_getter': lambda: SOLAR_DATA,
    'get_dxcc_cn': get_dxcc_cn,
})
```

---

### 6. `score_routes.py`
**职责**：机会评分 API  
**接口**：
- `POST /api/score/spot` - 为单个 Spot 计算评分
- `GET /api/score/missing` - 获取缺失 DXCC 评分
- `GET /api/score/top` - 获取评分最高的推荐列表

**注册方式**：
```python
register_score_routes(app, {
    'log': log,
    'get_scorer': lambda: scorer,
    'init_scorer': init_scorer,
    'lock': lock,
    'get_spot_history': lambda: spot_history,
    'get_band_counts': lambda: band_counts,
    'get_total_spots': lambda: total_spots,
    'get_solar_data': lambda: SOLAR_DATA,
    'get_dxcc_cn': get_dxcc_cn,
    'get_logs_dir': lambda: Path(__file__).parent / 'logs',
})
```

---

## 依赖注入约定

所有路由模块通过 `register_*_routes(app, deps)` 函数注册，`deps` 字典包含：

| 依赖类型 | 说明 | 示例 |
|---------|------|------|
| 日志函数 | 统一日志输出 | `log` |
| 错误处理 | 外部 API 错误封装 | `external_api_error` |
| 全局状态访问器 | 安全读取全局变量 | `get_spot_history` |
| 业务组件 | 评分器等可插拔组件 | `get_scorer` |

**优势**：
- 模块不直接依赖全局变量，便于测试
- 依赖关系在 `app.py` 集中配置，易于追踪
- 可轻松替换/mock 依赖进行单元测试

---

## 安全配置变更

敏感配置迁移到环境变量，详见 `SECURITY_CONFIG.md`：

| 变量名 | 用途 |必填（生产） |
|-------|------|-----------|
| `SECRET_KEY` | Flask 会话密钥 | ✅ |
| `WAVELOG_URL` | Wavelog 地址 | ✅ |
| `WAVELOG_API_KEY` | Wavelog API 密钥 | ✅ |
| `CLUBLOG_APP_PASSWORD` | ClubLog 密码 | ✅ |
| `QRZ_USERNAME` / `QRZ_PASSWORD` | QRZ 查询凭据 | ✅ |
| `HAMQTH_USERNAME` / `HAMQTH_PASSWORD` | HamQTH 凭据 | ✅ |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY_PEM` / `VAPID_EMAIL` | Web Push 配置 | ✅ |
| `SOCKETIO_CORS_ALLOWED_ORIGINS` | SocketIO CORS 配置 | ❌（默认 `*`） |

开发环境可省略（使用默认值），生产环境通过 `FLASK_ENV=production` 强制校验。

---

## 运维能力

### Docker 容器化

**文件**：
- `Dockerfile` - 基于 Python 3.11-slim 的容器镜像
- `docker-compose.yml` - 服务编排和持久化配置

**快速启动**：
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 健康检查
docker-compose exec dx-guardian curl http://localhost:5000/health
```

---

### GitHub Actions CI/CD

**文件**：`.github/workflows/ci.yml`

**流水线阶段**：
1. **Test** - 语法检查 + 单元测试
2. **Build** - 构建 Docker 镜像 + 容器测试
3. **Deploy** - 生产部署通知（master 分支推送时触发）

**运行测试**：
```bash
# 本地模拟 CI
python -m py_compile backend/app.py
python -m unittest discover -s tests -p "test_*.py"
```

---

### 生产环境配置检查

**文件**：`dx_guardian/check_prod_config.py`

**用途**：
- 验证所有必需环境变量已设置
- 检测弱密钥配置（如默认 SECRET_KEY）
- 生产模式强制校验，开发模式警告提示

**使用方法**：
```bash
# 开发模式检查
python dx_guardian/check_prod_config.py

# 生产模式检查
FLASK_ENV=production python dx_guardian/check_prod_config.py

# 配置检查通过后再启动服务
python dx_guardian/check_prod_config.py && python -m flask run
```

**退出码**：
- `0` - 检查通过，可安全启动
- `1` - 存在错误，必须修复

---

## 测试说明

### 运行全部测试
```bash
python3 -m unittest discover -s "dx_guardian/tests" -p "test_*.py"
```

### 测试覆盖
| 模块 | 测试文件 | 用例数 |
|------|---------|--------|
| `wavelog_routes` | `test_wavelog_routes.py` | 2 |
| `push_routes` | `test_push_routes.py` | 2 |
| `watchlist_routes` | `test_watchlist_routes.py` | 2 |
| `station_routes` | `test_station_routes.py` | 2 |
| `log_routes` | `test_log_routes.py` | 2 |
| **总计** | | **10** |

---

## 前端兼容性

所有 API 路径和返回结构保持不变，前端无需修改。

已验证的前端调用文件：
- `frontend/js/app.js` - 主逻辑
- `frontend/js/alerts.js` - 预警逻辑

---

## 后续可选拆分

如果 `app.py` 仍需进一步瘦身，可考虑：

1. **评分相关 API**（约 200 行）
   - `/api/score/spot`
   - `/api/score/missing`
   - `/api/score/top`

2. **数据源轮询**（Cluster + PSKReporter）
   - 抽离为 `data_sources.py`
   - 包含 `cluster_thread()` 和 `pskreporter_thread()`

3. **WebSocket 事件处理**
   - 抽离为 `websocket_events.py`

---

## 重构日期
- 完成时间：2026-05-02
- 分支：`260502-chore-secure-config-secrets`
