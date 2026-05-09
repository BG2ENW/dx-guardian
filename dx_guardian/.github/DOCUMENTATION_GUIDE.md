# DX Guardian 文档维护指南

本文档说明如何维护和更新 DX Guardian 的项目文档。

---

## 📁 文档结构

```
dx_guardian/
├── CHANGELOG.md              # ✨ 变更日志（必须更新）
├── WORKLOG_SUMMARY.md        # 📊 工作记录总览
├── BUGFIX_YYYY-MM-DD.md      # 🐛 Bug 修复报告（按需创建）
├── WORKLOG_YYYY-MM-DD.md     # 📝 每日工作记录（按需创建）
├── REFACTOR_SUMMARY.md       # 🔧 重构说明（重大重构时创建）
├── SECURITY_CONFIG.md        # 🔒 安全配置指南
├── THEME_TROUBLESHOOTING.md  # 🎨 主题故障排查
├── docs/                     # 📚 技术文档目录
│   ├── README.md            # 文档导航
│   ├── DATA_FILES.md        # 数据文件格式
│   ├── EXTERNAL_DATA_FILES.md
│   ├── JTDX_GRID_DATABASE_FORMAT.md
│   ├── PSKREPORTER_API_GUIDE.md
│   ├── THEME_AND_LAYOUT.md
│   └── DEVELOPMENT_LOG.md   # 详细开发日志
└── docs_archive/            # 🗄️ 归档文档
```

---

## ✍️ 文档更新规范

### 1. CHANGELOG.md（变更日志）

**何时更新**:
- 每次发布新版本
- 新增功能
- Bug 修复
- 性能优化

**格式要求**:
```markdown
## [版本号] - 日期

### ✨ 新增功能
- 功能 1 描述
- 功能 2 描述

### 🐛 Bug 修复
- Bug 描述（Fixes #Issue 号）

### ⚡ 性能优化
- 优化指标对比
```

**示例**: [../CHANGELOG.md](../CHANGELOG.md)

---

### 2. WORKLOG_YYYY-MM-DD.md（工作记录）

**何时创建**:
- 有重大功能开发时
- 单日工作时间 > 2 小时
- 需要详细记录技术决策

**格式要求**:
```markdown
# DX Guardian 工作记录 - YYYY 年 MM 月 DD 日

## 执行摘要
- 完成的核心功能（3-5 个要点）

## 完成的功能清单
### 1. 功能名称
| API | 方法 | 功能 | 状态 |
|-----|------|------|------|
| /api/xxx | GET | 功能说明 | ✅ |
```

**示例**: [../WORKLOG_2026-05-04.md](../WORKLOG_2026-05-04.md)

---

### 3. BUGFIX_YYYY-MM-DD.md（Bug 修复报告）

**何时创建**:
- 修复中等级别以上 Bug
- 系统审查后
- 性能优化后

**格式要求**:
```markdown
# BUG 修复报告 - YYYY-MM-DD

## 系统审查结果
### ✅ 通过的测试
| 测试项 | 状态 | 说明 |
|--------|------|------|
| 测试 1 | ✅ | 说明 |
```

**示例**: [../BUGFIX_2026-05-05.md](../BUGFIX_2026-05-05.md)

---

## 📅 文档维护周期

- **每日**: 记录工作日志（如有重大开发）
- **每周**: 汇总 WORKLOG_SUMMARY.md
- **每月**: 发布新版本，更新 CHANGELOG.md
- **每季度**: 全面审查技术文档

---

## 🔧 文档工具

- VS Code + Markdown Preview Enhanced
- Typora
- Prettier 格式化

---

**最后更新**: 2026-05-05  
**维护者**: DX Guardian 文档团队
