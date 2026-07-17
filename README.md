# Research Agent Skills Collection

面向多 Agent 研究工作的可组合 Skill 集合。仓库采用“分类 / Skill”两级布局，
每个包含 `SKILL.md` 的目录都可以独立安装、测试和发布。

## Skill 分类

| 分类 | Skill | 作用 |
|---|---|---|
| `orchestration` | `security-research-orchestrator` | 管理研究边界、任务图、隔离执行、状态恢复、证据、独立验证与最终汇总 |
| `research-design` | `research-template-compiler` | 将开放研究问题编译为完形槽位、窄接口、资源安全波次和可恢复研究 DAG |
| `writing` | `cs-research-paper`（uArch Writing） | 面向计算机体系结构与微架构研究的中文论文结构、论证、技术一致性和语言修改 |
| `visualization` | `figures-diagram` | 为论文流程图、系统架构图和概念图生成绘图规格 |
| `visualization` | `figures-python` | 使用可复现 Python 脚本生成论文数据图、PNG 和 SVG |

## 组合关系

```text
research-template-compiler
  └─ 生成槽位、依赖、任务接口和验证门
       └─ security-research-orchestrator
            └─ 执行任务、维护状态、收集证据、独立验证和汇总
                 └─ cs-research-paper
                      ├─ figures-diagram
                      └─ figures-python
```

各 Skill 可以独立使用。需要先探索问题空间时，从模板编译器开始；已有明确任务合同、
实验或证据要求时，直接使用研究编排器；进入论文交付阶段后，再按需调用写作与绘图 Skill。

## 目录

```text
skills/
├── orchestration/
│   └── security-research-orchestrator/
├── research-design/
│   └── research-template-compiler/
├── writing/
│   └── cs-research-paper/
└── visualization/
    ├── figures-diagram/
    └── figures-python/
```

`catalog.json` 提供机器可读的分类、入口和标签。新增 Skill 时选择职责最接近的分类；
不要把多个独立 Skill 合并到同一个 `SKILL.md`。

## 安装

克隆仓库后，将所需 Skill 目录复制到 Codex Skill 目录：

```bash
git clone <repository-url>
cp -R <repository-directory>/skills/orchestration/security-research-orchestrator \
  "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -R <repository-directory>/skills/research-design/research-template-compiler \
  "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -R <repository-directory>/skills/writing/cs-research-paper \
  "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -R <repository-directory>/skills/visualization/figures-diagram \
  "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -R <repository-directory>/skills/visualization/figures-python \
  "${CODEX_HOME:-$HOME/.codex}/skills/"
```

仓库名称变化不会影响 Skill 自身名称和目录内的相对资源引用。

## 验证

提交前运行集合校验与各 Skill 测试：

```bash
python3 scripts/validate_collection.py
python3 -m unittest discover \
  -s skills/orchestration/security-research-orchestrator/tests \
  -p "test_*.py"
python3 -m unittest discover \
  -s skills/research-design/research-template-compiler/tests \
  -p "test_*.py"
```

GitHub Actions 会在 push 和 pull request 时执行相同检查。

## 第三方来源

`figures-diagram` 与 `figures-python` 改编自 MIT 许可的
[research-writing-skill](https://github.com/Norman-bury/research-writing-skill)。
版权与许可文本见 `THIRD_PARTY_NOTICES.md` 和
`licenses/research-writing-skill-MIT.txt`。
