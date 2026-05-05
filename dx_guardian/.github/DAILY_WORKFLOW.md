# DX Guardian 每日开发工作流

> 规范化的每日工作流程，确保文档和代码同步更新

---

## 每日开始工作前（5 分钟）

### 1. 检查 Git 分支

```bash
git branch
```

如果在 master/main，创建新功能分支：

```bash
git checkout -b YYMMDD-feat-description
# 例：git checkout -b 260505-feat-add-myspots-api
```

### 2. 查看待办事项

```bash
grep -A 20 "待办事项" WORKLOG_SUMMARY.md
```

### 3. 确认今日目标

记录 1-3 个核心任务：
- [ ] 任务 1
- [ ] 任务 2
- [ ] 任务 3

---

## 开发过程中（按需创建文档）

### 场景 1: 新功能开发 → 创建 `WORKLOG_YYYY-MM-DD.md`

**模板**:
```markdown
# DX Guardian 工作记录 - YYYY 年 MM 月 DD 日

## 计划任务
- [ ] 任务 1
- [ ] 任务 2

## 进行中的工作

### 任务 1: 任务名称
**时间**: HH:MM
**状态**: 🔄 进行中

#### 代码改动
文件：path/to/file.py
- 改动 1
- 改动 2

#### 遇到的问题
- 问题：
- 解决：

**状态**: ⬜ 未开始 / 🔄 进行中 / ✅ 完成
```

### 场景 2: Bug 修复 → 创建 `BUGFIX_YYYY-MM-DD.md`

**模板**:
```markdown
# BUG 修复报告 - YYYY-MM-DD

## BUG #1: 问题标题
**问题**: 描述
**影响**: 范围
**修复**: 方案
**文件**: path:line
**状态**: ✅
```

### 场景 3: 重大重构 → 创建 `REFACTOR_YYYY-MM-DD.md`

---

## 提交代码规范

### 提交前检查

```bash
git status          # 查看改动
git diff            # 查看内容
python -m unittest  # 运行测试
```

### 提交信息格式

```
type: 简洁描述

详细说明

Fixes: #42
改动:
- file1.py: 说明
- file2.js: 说明
```

**Type 类型**: feat / fix / docs / refactor / test / chore

### 示例

```bash
git commit -m "feat: Add My Spots API

- Add /api/myspots endpoint
- Add age field calculation

Fixes: #42
改动:
- app.py: API endpoint
- app.js: 前端渲染
"
```

---

## 每日结束工作前（10 分钟）

### 1. 完善工作日志

编辑 `WORKLOG_YYYY-MM-DD.md`:

```markdown
## 执行摘要
- ✅ 完成功能 1
- ✅ 完成功能 2

## 完成的功能清单
### 1. 功能名称
| API | 状态 |
|-----|------|
| /api/xxx | ✅ |

## 技术决策
- 决策 + 原因

## 明日计划
- [ ] 待办 1
```

### 2. 更新汇总

- 更新 `WORKLOG_SUMMARY.md`
- 更新 `CHANGELOG.md`（有新功能时）

### 3. 提交代码

```bash
git add .
git commit -m "chore: 完成今日开发"
git push -u origin branch-name
```

### 4. 清理

```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

---

## 检查清单

### 开始工作
- [ ] 检查分支
- [ ] 创建分支（如需要）
- [ ] 确认今日目标

### 提交代码
- [ ] 运行测试
- [ ] 查看 diff
- [ ] 规范提交信息

### 结束工作
- [ ] 完善日志
- [ ] 更新汇总
- [ ] 提交推送
- [ ] 清理缓存

---

## 自动化脚本

### 开始工作脚本

```bash
#!/bin/bash
# ~/bin/dx-start-work.sh
TODAY=$(date +%Y-%m-%d)
BRANCH=$(date +%y%m%d)-feat-${1// /-}

cd /workspace/dx_guardian
git checkout -b $BRANCH 2>/dev/null || echo "使用现有分支：$BRANCH"

cat > WORKLOG_$TODAY.md << EOF
# 工作记录 - $TODAY
## 计划
- [ ] $1
EOF

echo "开始工作：$BRANCH"
```

**使用**:
```bash
chmod +x ~/bin/dx-start-work.sh
dx-start-work "添加 My Spots 功能"
```

### 结束工作脚本

```bash
#!/bin/bash
# ~/bin/dx-end-work.sh
cd /workspace/dx_guardian
echo "今日改动:"
git status --short
echo "运行测试..."
python -m unittest discover
echo "结束工作！"
```

---

## 最佳实践

### 推荐
- ✅ 立即记录想法和决策
- ✅ 小步提交（每次<100 行）
- ✅ 先写文档再编码
- ✅ 每周五汇总更新

### 避免
- ❌ 补记日志（凭记忆）
- ❌ 大提交（>500 行）
- ❌ 只编码不写文档
- ❌ 从不更新汇总

---

**更新日期**: 2026-05-05
