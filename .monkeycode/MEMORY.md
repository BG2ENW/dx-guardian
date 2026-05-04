# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[按上述格式记录的记忆条目]

[后端敏感配置管理方式]
- Date: 2026-05-02
- Context: Agent 在执行安全收敛改造时发现
- Category: 环境配置
- Instructions:
  - 后端敏感配置统一由 `dx_guardian/backend/config.py` 通过环境变量读取，不应在代码中硬编码。
  - 生产环境通过 `FLASK_ENV=production` 或 `APP_ENV=production` 触发必填校验，缺失关键变量时启动即失败。
  - 开发环境使用 `dx_guardian/.env.example` 作为变量模板，不保存真实凭据到仓库。

[后端路由模块拆分约定]
- Date: 2026-05-02
- Context: Agent 在执行 app.py 结构化拆分时发现
- Category: 代码结构
- Instructions:
  - 外部系统相关路由按领域拆分为独立模块，并通过 `register_*_routes(app, deps)` 注册到主应用。
  - 当前已拆分 `dx_guardian/backend/wavelog_routes.py` 与 `dx_guardian/backend/push_routes.py`，`app.py` 负责依赖注入与统一日志策略。

[后端最小测试执行方式]
- Date: 2026-05-02
- Context: Agent 在执行路由模块回归验证时发现
- Category: 测试方法
- Instructions:
  - 使用标准库 `unittest` 进行最小回归验证，测试目录为 `dx_guardian/tests/`。
  - 统一执行命令：`python3 -m unittest discover -s dx_guardian/tests -p "test_*.py"`。

[app.py 拆分完成状态]
- Date: 2026-05-02
- Context: Agent 在执行 app.py 模块化重构时完成
- Category: 代码结构
- Instructions:
  - 已拆分模块：
    - `wavelog_routes.py`（Wavelog 第三方集成）
    - `push_routes.py`（Web Push 推送）
    - `watchlist_routes.py`（用户关注列表）
    - `station_routes.py`（台站配置）
    - `log_routes.py`（日志上传/解析/验证）
  - 测试覆盖：每个拆出模块都有 `test_*.py` 最小回归测试（共 10 个用例）。
  - 当前 `app.py` 行数已从 1682 行降至约 900 行，核心职责为：
    - 静态文件服务
    - WebSocket 连接处理
    - Cluster 连接线程
    - PSKReporter 数据轮询
    - 评分相关 API（score/spot, score/missing, score/top）

[PSKReporter Grid 字段兼容性]
- Date: 2026-05-04
- Context: Agent 在执行 Grid 问题修复时发现
- Category: 代码模式
- Instructions:
  - PSKReporter 的 `senderLocator` 可能出现 4/6/8 位 Maidenhead（如 `JN18dr12`），入库前需统一 `trim + uppercase`。
  - Grid 校验建议使用正则 `^[A-R]{2}[0-9]{2}([A-X]{2})?([0-9]{2})?$`，无效值应置空避免污染坐标解析和去重键。

[PSK Grid 持久缓存机制]
- Date: 2026-05-04
- Context: Agent 在执行 CTY 精度优化时发现
- Category: 代码模式
- Instructions:
  - 呼号到 Grid 的快速索引需要落盘到 `dx_guardian/backend/data/psk_grid_cache.json`，避免服务重启后丢失并再次回退 CTY。
  - 启动时先加载缓存，运行中仅在 Grid 变更时批量保存，可降低 I/O 并保持地图定位连续性。
