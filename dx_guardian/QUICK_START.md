# DX Guardian 快速参考卡片

> 📌 每日开发必备命令和检查清单

---

## 🌅 开始工作（30 秒）

```bash
cd /workspace/dx_guardian
git branch                              # 查看分支
git checkout -b $(date +%y%m%d)-feat-x  # 创建分支
vim WORKLOG_$(date +%Y-%m-%d).md        # 创建工作日志
```

---

## 📝 文档创建速查

| 场景 | 命令 | 文件 |
|------|------|------|
| 新功能 | `vim WORKLOG_$(date +%Y-%m-%d).md` | 工作日志 |
| Bug 修复 | `vim BUGFIX_$(date +%Y-%m-%d).md` | Bug 报告 |
| 重构 | `vim REFACTOR_$(date +%Y-%m-%d).md` | 重构说明 |

---

## 💻 开发命令

```bash
# 运行测试
python -m unittest discover -s backend/tests

# 语法检查
python -m py_compile backend/app.py

# 配置检查
python dx_guardian/check_prod_config.py

# 启动服务
python -m flask run
```

---

## 📤 提交代码

```bash
git status                            # 查看改动
git diff                              # 查看内容
git add .                             # 添加文件
git commit -m "type: description"     # 提交
git push -u origin branch-name        # 推送
```

**提交类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档
- `refactor`: 重构
- `chore`: 杂项

---

## 🌆 结束工作（2 分钟）

```bash
# 1. 完善 WORKLOG_YYYY-MM-DD.md
vim WORKLOG_$(date +%Y-%m-%d).md

# 2. 提交
git add . && git commit -m "chore: 今日完成"

# 3. 推送
git push

# 4. 清理
find . -name "*.pyc" -delete
```

---

## 🔗 快速链接

| 文档 | 用途 |
|------|------|
| [CHANGELOG.md](./CHANGELOG.md) | 变更记录 |
| [WORKLOG_SUMMARY.md](./WORKLOG_SUMMARY.md) | 工作总结 |
| [DOCS_INDEX.md](./DOCS_INDEX.md) | 文档导航 |
| [.github/DAILY_WORKFLOW.md](./.github/DAILY_WORKFLOW.md) | 详细工作流 |

---

**打印建议**: 此卡片适合打印贴在工位
