# DX Guardian 文档索引

**最后更新**: 2026 年 5 月 4 日  
**文档总数**: 7 个  
**清理记录**: 已删除 12 个重复/过时文档（备份于 `docs_archive/`）

---

## 📚 核心文档

### 📘 开发日志（主文档）
**文件**: `DEVELOPMENT_LOG.md` (65KB, 2186 行)

**内容**:
- ✅ 开发计划书 v6.1（完整版）
- ✅ 坐标解析器修复记录（DXCC 前缀判定 + 中国分区 + 岛屿定位）
- ✅ 太阳数据修复记录（XML 标签名修复）
- ✅ UI 配色全面重构（7 轮迭代历史 + 最终方案）
- ✅ 技术决策与测试报告

**用途**: 了解项目整体架构、开发历程和技术决策

---

## 🔧 技术参考文档

### 数据格式

| 文档 | 说明 |
|------|------|
| `JTDX_GRID_DATABASE_FORMAT.md` | **二进制格式逆向工程** - JTDX Grid 数据库文件结构分析，包含 C 语言解析示例 |
| `EXTERNAL_DATA_FILES.md` | **外部数据源详解** - CTY.DAT、DXCC 前缀库、中国分区等数据文件的格式说明和解析代码 |
| `DATA_FILES.md` | **项目数据文件清单** - 所有数据文件的简要说明和用途 |

### 功能模块

| 文档 | 说明 |
|------|------|
| `PSKREPORTER_API_GUIDE.md` | **PSK Reporter API 集成** - 调用方式、限制、最佳实践和错误处理 |

### 设计规范

| 文档 | 说明 |
|------|------|
| `THEME_AND_LAYOUT.md` | **主题和布局设计** - 6 种配色方案、响应式布局、WCAG 无障碍标准 |

### 文档索引

| 文档 | 说明 |
|------|------|
| `README_DOCS.md` | **本文档** - 文档结构和使用指南 |

---

## 📖 使用指南

### 快速入门

1. **了解项目**: 阅读 `DEVELOPMENT_LOG.md` 第〇部分（项目定位与 MVP 计划）
2. **查看进展**: 查看 `DEVELOPMENT_LOG.md` 当前实现状态章节
3. **技术细节**: 参考对应的专题文档

### 开发参考

| 需求 | 参考文档 |
|------|---------|
| 新增功能 | `DEVELOPMENT_LOG.md` 中的 MVP 计划 |
| 坐标解析 | `DEVELOPMENT_LOG.md` 第 1 部分 + `JTDX_GRID_DATABASE_FORMAT.md` |
| 数据格式 | `EXTERNAL_DATA_FILES.md` + `JTDX_GRID_DATABASE_FORMAT.md` |
| 主题配色 | `DEVELOPMENT_LOG.md` 第 3 部分 + `THEME_AND_LAYOUT.md` |
| API 集成 | `PSKREPORTER_API_GUIDE.md` |

### 维护指南

- **更新开发日志**: 在 `DEVELOPMENT_LOG.md` 中追加新记录
- **创建专题文档**: 复杂功能单独创建文档并在本索引登记
- **版本管理**: 文档版本号与项目版本号保持一致
- **清理原则**: 迭代过程文档应整合到主日志，仅保留最终方案

---

## 🗂️ 文档结构

```
docs/
├── DEVELOPMENT_LOG.md          # 主开发日志（65KB）
├── JTDX_GRID_DATABASE_FORMAT.md # Grid 二进制格式（技术深度）
├── EXTERNAL_DATA_FILES.md      # 外部数据源说明
├── PSKREPORTER_API_GUIDE.md    # PSK API 使用指南
├── THEME_AND_LAYOUT.md         # 主题布局设计
├── DATA_FILES.md               # 数据文件清单
└── README_DOCS.md              # 文档索引（本文档）
```

---

## 📦 归档文档

已删除的 12 个文档备份于 `docs_archive/` 目录：

**迭代过程文档（7 个）**:
- `LIGHT_MODE_COLOR_IMPROVEMENTS.md`
- `LIGHT_MODE_COMPLETE_REWRITE.md`
- `LIGHT_MODE_WATCHLIST_FIX.md`
- `UI_COLOR_OPTIMIZATION.md`
- `UI_COLOR_FIX_V2.md`
- `WATCHLIST_FINAL_FIX.md`
- `WATCHLIST_JS_FIX.md`

**已整合/过时文档（5 个）**:
- `GRID_COORDINATE_FIX_LOG.md`
- `CTY_INTEGRATION_COMPLETE.md`
- `REALTIME_DATA_FIXES.md`
- `REALTIME_DATA_STATUS.md`
- `SYSTEM_STATUS_FIX.md`

---

**文档维护**: DX Guardian 开发团队  
**清理记录**: 2026 年 5 月 4 日 - 删除 12 个重复文档，保留 7 个核心文档
