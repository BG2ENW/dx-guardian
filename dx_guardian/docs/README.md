# DX Guardian 开发文档

本文档目录包含 DX Guardian 项目的完整开发文档和技术参考。

## 📚 文档结构

### 核心文档
- [`../CHANGELOG.md`](../CHANGELOG.md) - 变更日志（所有版本更新记录）
- [`../REFACTOR_SUMMARY.md`](../REFACTOR_SUMMARY.md) - 后端重构说明
- [`../SECURITY_CONFIG.md`](../SECURITY_CONFIG.md) - 安全配置指南
- [`../THEME_TROUBLESHOOTING.md`](../THEME_TROUBLESHOOTING.md) - 主题故障排查

### 技术文档
- [`DATA_FILES.md`](./DATA_FILES.md) - 数据文件格式说明
- [`EXTERNAL_DATA_FILES.md`](./EXTERNAL_DATA_FILES.md) - 外部数据文件
- [`JTDX_GRID_DATABASE_FORMAT.md`](./JTDX_GRID_DATABASE_FORMAT.md) - JTDX Grid 数据库格式
- [`PSKREPORTER_API_GUIDE.md`](./PSKREPORTER_API_GUIDE.md) - PSKReporter API 指南
- [`THEME_AND_LAYOUT.md`](./THEME_AND_LAYOUT.md) - 主题和布局规范

### 开发日志
- [`DEVELOPMENT_LOG.md`](./DEVELOPMENT_LOG.md) - 详细开发日志（坐标解析、UI 配色重构）

### 归档文档
- [`../docs_archive/`](../docs_archive/) - 旧版文档归档

---

## 🚀 快速开始

### 开发环境设置

```bash
# 1. 克隆项目
cd /workspace/dx_guardian

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
export SECRET_KEY=<your-secret-key>
export WAVELOG_URL=<your-wavelog-url>
export WAVELOG_API_KEY=<your-api-key>

# 4. 运行配置检查
python dx_guardian/check_prod_config.py

# 5. 启动开发服务器
python -m flask run
```

### Docker 部署

```bash
# 快速启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 健康检查
docker-compose exec dx-guardian curl http://localhost:5000/health

# 停止服务
docker-compose down
```

---

## 📖 文档阅读指南

### 按角色分类

#### 新贡献者
1. [CHANGELOG.md](../CHANGELOG.md) - 了解项目演进历史
2. [REFACTOR_SUMMARY.md](../REFACTOR_SUMMARY.md) - 理解后端架构
3. [DATA_FILES.md](./DATA_FILES.md) - 熟悉数据格式

#### 前端开发者
1. [THEME_AND_LAYOUT.md](./THEME_AND_LAYOUT.md) - UI 设计规范
2. [DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md) - 前端重构记录
3. [SECURITY_CONFIG.md](../SECURITY_CONFIG.md) - 环境变量配置

#### 后端开发者
1. [REFACTOR_SUMMARY.md](../REFACTOR_SUMMARY.md) - 路由模块拆分说明
2. [PSKREPORTER_API_GUIDE.md](./PSKREPORTER_API_GUIDE.md) - 第三方 API 集成
3. [JTDX_GRID_DATABASE_FORMAT.md](./JTDX_GRID_DATABASE_FORMAT.md) - 数据协议

#### DevOps 工程师
1. [SECURITY_CONFIG.md](../SECURITY_CONFIG.md) - 生产环境配置
2. [REFACTOR_SUMMARY.md](../REFACTOR_SUMMARY.md) - Docker 部署指南
3. [../check_prod_config.py](../check_prod_config.py) - 配置检查脚本

---

## 🔧 开发工具

### 测试命令

```bash
# 单元测试
python -m unittest discover -s dx_guardian/tests -p "test_*.py"

# 语法检查
python -m py_compile dx_guardian/backend/app.py

# 配置检查
FLASK_ENV=production python dx_guardian/check_prod_config.py
```

### 数据库工具

```bash
# 查看 SQLite 数据库
sqlite3 backend/dx_spots.db

# 常用查询
sqlite3 backend/dx_spots.db "SELECT COUNT(*) FROM spot_history;"
sqlite3 backend/dx_spots.db "SELECT callsign, COUNT(*) FROM spot_history GROUP BY callsign ORDER BY 2 DESC LIMIT 10;"
```

### 性能分析

```bash
# 内存使用
ps aux | grep python

# API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/api/myspots?call=<YOUR_CALL>
```

---

## 📊 项目统计

### 代码统计（截至 v2.1.0）

| 模块 | 文件数 | 代码行数 | 测试覆盖 |
|------|--------|----------|---------|
| 后端核心 | 8 | 4,200 | - |
| 路由模块 | 6 | 2,850 | 10 个用例 |
| 前端核心 | 4 | 3,500 | - |
| 文档 | 12 | 5,000+ | - |
| 测试 | 6 | 800 | 65% |
| **总计** | **36** | **16,350** | **65%** |

### API 端点

| 模块 | 端点数 | 说明 |
|------|--------|------|
| My Spots | 3 | `/api/myspots`, `/api/spot/submit`, `/api/history` |
| Wavelog | 3 | 台站配置、统计、呼号查询 |
| Web Push | 5 | 订阅、取消订阅、测试、状态 |
| Watchlist | 4 | 关注列表 CRUD + 批量导入 |
| Station | 2 | 台站配置管理 |
| Logs | 4 | 日志上传、列表、删除、验证 |
| Score | 3 | 机会评分、缺失 DXCC、推荐 |
| **总计** | **24** | - |

### 数据源

| 类型 | 数量 | 更新频率 |
|------|------|----------|
| DX Cluster | 8 | 实时 |
| PSK Reporter | 1 | 每 5 分钟 |
| Solar Data | 1 | 每日 |
| External APIs | 4 | 按需 |
| **总计** | **14** | - |

---

## 🛠️ 故障排查

### 常见问题

| 问题 | 解决方案 | 参考文档 |
|------|----------|----------|
| 环境变量缺失 | 运行 `check_prod_config.py` | SECURITY_CONFIG.md |
| 数据库锁定 | 检查 spot_database.py 锁机制 | spot_database.py |
| API 返回 404 | 检查路由注册 | REFACTOR_SUMMARY.md |
| 前端不刷新 | 清除浏览器缓存 | THEME_AND_LAYOUT.md |
| 坐标解析错误 | 更新 coordinate_resolver.py | DEVELOPMENT_LOG.md |

### 调试技巧

```bash
# 查看详细日志
export FLASK_DEBUG=1
python -m flask run

# 监控数据库操作
sqlite3 backend/dx_spots.db ".trace on"

# 网络抓包分析 API
curl -v http://localhost:5000/api/myspots?call=<YOUR_CALL>
```

---

## 📅 更新记录

### 2026-05-05
- ✅ 创建统一 CHANGELOG.md
- ✅ 整理开发文档目录结构
- ✅ 规范文档命名和格式
- ✅ 清理归档文档

### 2026-05-04
- ✅ SQLite 持久化存储实现
- ✅ My Spots 模块完整数据接入
- ✅ Age 字段显示优化
- ✅ 定时器优化（5s + 45s → 45s）

### 2026-05-02
- ✅ 后端模块拆分（6 个路由模块）
- ✅ Docker 容器化
- ✅ GitHub Actions CI/CD
- ✅ 10 个单元测试

---

## 🤝 贡献指南

### 提交代码

1. 创建功能分支
   ```bash
   git checkout -b YYMMDD-feat-description
   ```

2. 开发完成后运行测试
   ```bash
   python -m unittest discover
   ````

3. 提交改动
   ```bash
   git add .
   git commit -m "feat: description"
   ```

### 文档维护

- 所有新功能必须更新 CHANGELOG.md
- 重大改动必须更新对应技术文档
- Bug 修复记录到 BUGFIX_YYYY-MM-DD.md
- 工作日志记录到 WORKLOG_YYYY-MM-DD.md

---

## 📞 联系方式

- 项目仓库：[GitHub](https://github.com/your-repo/dx-guardian)
- 问题反馈：[Issues](https://github.com/your-repo/dx-guardian/issues)
- 文档问题：更新本文档或提交 PR

---

**最后更新**: 2026-05-05  
**维护者**: DX Guardian 开发团队  
**版本**: v2.1.0
