# DX Guardian 📻

> **实时 DX Spot 活动监控 + 机会评分系统**
> 
> 基于 Web 的业余无线电 DX 活动实时监控工具，提供地理可视化、机会评分、规则预警功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-red.svg)

---

## ✨ 核心功能

### 实时监控
- 🌍 **DX Spot 地图** - Leaflet 实时展示全球 Spot 活动
- 📊 **波段统计** - 各波段活跃台站数、区域分布
- 🔔 **规则预警** - 满足关注条件时即时通知

### 智能评分
- 🎯 **机会评分** - 基于传播条件、历史活动、稀有度的 DX 机会评估
- 📈 **缺失统计** - 根据你的日志自动计算缺失 DXCC/波段
- 🏆 **推荐列表** - 按评分排序的高价值目标推荐

### 数据集成
- 📡 **Cluster 数据源** - 多服务器实时 DX Spot
- 🗺️ **PSKReporter** - RBN 逆向信标网络补充
- 📒 **Wavelog** - QSO 日志同步与验证

---

## 🚀 快速开始

### 开发环境

```bash
# 克隆项目
git clone https://github.com/BG2ENW/dx-guardian.git
cd dx-guardian

# 安装依赖
pip install -r dx_guardian/requirements.txt

# 配置环境变量
cp dx_guardian/.env.example .env
# 编辑 .env 填入必要配置

# 启动服务
python -m flask run
```

访问 http://localhost:5000

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 📁 项目结构

```
dx_guardian/
├── backend/
│   ├── app.py                 # 主应用入口
│   ├── config.py              # 配置管理
│   ├── wavelog_routes.py      # Wavelog 集成
│   ├── push_routes.py         # Web Push 推送
│   ├── watchlist_routes.py    # 关注列表
│   ├── station_routes.py      # 台站配置
│   ├── log_routes.py          # 日志管理
│   └── score_routes.py        # 评分 API
├── frontend/
│   ├── index.html             # 主页面
│   ├── js/
│   │   ├── map.js             # 地图模块
│   │   ├── socket.js          # WebSocket
│   │   └── ui.js              # UI 交互
│   └── css/
│       └── style.css          # 样式
├── tests/                     # 单元测试
├── docs/                      # 文档
├── Dockerfile                 # Docker 镜像
└── docker-compose.yml         # 容器编排
```

---

## ⚙️ 配置说明

### 必需环境变量

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | Flask 会话密钥（生成：`python -c "import secrets; print(secrets.token_hex(32))"`） |
| `WAVELOG_URL` | Wavelog QSO 系统地址 |
| `WAVELOG_API_KEY` | Wavelog API 密钥 |
| `CLUBLOG_APP_PASSWORD` | ClubLog 密码 |
| `QRZ_USERNAME` / `QRZ_PASSWORD` | QRZ.com 凭据 |
| `HAMQTH_USERNAME` / `HAMQTH_PASSWORD` | HamQTH 凭据 |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY_PEM` / `VAPID_EMAIL` | Web Push 配置 |

详见：[SECURITY_CONFIG.md](dx_guardian/SECURITY_CONFIG.md)

### 生产环境检查

```bash
# 运行配置检查
python dx_guardian/check_prod_config.py

# 生产模式检查
FLASK_ENV=production python dx_guardian/check_prod_config.py
```

---

## 🧪 测试

```bash
# 运行单元测试
python -m unittest discover -s dx_guardian/tests -p "test_*.py"

# 运行配置检查 + 测试
python dx_guardian/check_prod_config.py && python -m pytest
```

---

## 📚 文档

- [安全配置指南](dx_guardian/SECURITY_CONFIG.md) - 环境变量与密钥管理
- [重构说明](dx_guardian/REFACTOR_SUMMARY.md) - 模块化架构说明
- [开发计划书](DX_ALERT_DEVELOPMENT_PLAN_v5.md) - 完整技术设计

---

## 🔧 CI/CD

项目使用 GitHub Actions 进行持续集成：

- **Test** - 语法检查 + 单元测试
- **Build** - Docker 镜像构建
- **Deploy** - 生产部署通知

配置文件：`.github/workflows/ci.yml`

---

## 📊 后端重构概览

| 模块 | 接口数 | 职责 |
|------|--------|------|
| `wavelog_routes.py` | 3 | Wavelog 第三方集成 |
| `push_routes.py` | 5 | Web Push 推送通知 |
| `watchlist_routes.py` | 4 | 用户关注列表管理 |
| `station_routes.py` | 2 | 台站配置管理 |
| `log_routes.py` | 4 | 日志上传/解析/验证 |
| `score_routes.py` | 3 | 机会评分 API |

**代码质量**: 
- `app.py` 从 1682 行降至 955 行 (-43%)
- 10 个单元测试全部通过
- 依赖注入模式，便于测试和维护

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交改动 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 📧 联系方式

- **呼号**: BG2ENW
- **位置**: PN35HS（中国哈尔滨）
- **项目地址**: https://github.com/BG2ENW/dx-guardian

---

## 🙏 致谢

- DX Summit - Cluster 数据源
- PSKReporter - RBN 数据源
- ClubLog - 呼号查询
- QRZ.com / HamQTH - Grid 查询
- Wavelog - QSO 日志系统
