# Codex CLI：交互式 Review + 独立带读 Skills

这是两份独立的 Codex Skills，附带真实的 Gerrit 未发布草稿工作流、临时进度文件规范和安全安装脚本。

## 内容

```text
skills/
├── SKILL/
│   ├── review/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── gerrit.md
│   │   │   └── session.md
│   │   └── scripts/
│   │       └── session.py
│   └── tutor/
│       └── SKILL.md
├── install.sh
└── README.md
```

- `$review`：先通读完整 patch series，然后**一次一条 commit**、你控制阶段与切换；总览审查 → 按需带读 → 问题分析 → 评论确认 → 只有获明确授权才保存未发布的 Gerrit 草稿。每条 commit 必做补丁格式和项目编码规范检查；分析与 Gerrit 评论均使用中文。历史问题默认只提示，不进入当前问题表。使用工作区内一次性会话文件，可恢复、结束后清理。
- `$tutor`：独立阅读文件/函数/commit/patch series；先建立完整逻辑章节地图，一次只讲一章，等你要求继续。进度保留在对话中，不创建独立 session；仅在你明确要求时保存简短进度记录。在 review 中使用时，共用 review 会话状态。

## 安装

**用户级安装（推荐）**：在 Linux / snode5 上执行：

```bash
cd /path/to/skills
./install.sh
```

默认安装到 `~/.agents/skills/`，等同于 `bash install.sh --user`。脚本以自身所在位置定位源目录，可从任意工作目录执行。

安装会扫描仓库 `SKILL/` 的直接子目录，只复制包含 `SKILL.md` 的技能目录及其全部内容（包括 `references/`、`scripts/` 等）。不会复制外层 `SKILL/`、仓库 README 或安装脚本。以后新增技能遵循 `SKILL/<技能名>/SKILL.md` 结构即可，无需修改安装列表。

如果旧的 `~/.agents/skills/review` 已经存在，默认安装不会覆盖。确认要升级后：

```bash
bash install.sh --user --replace
```

旧版本会移至 `~/.codex/skill-backups/`，**不在 Skills 扫描目录内**。

**项目级安装（仅当前仓库）**：

```bash
bash install.sh --project /path/to/repository
```

安装目录分别为 `~/.agents/skills/{review,tutor}/` 或 `<repo>/.agents/skills/...`。重新启动 Codex CLI。若支持 `/skills`，可检查技能是否发现；也可直接输入 `$review`、`$tutor` 调用。此处 `$...` 是 Codex 对话里的技能引用，不是 Linux shell 命令。

如果通过 Windows 下载 ZIP 后上传 Linux：

```powershell
scp .\codex-review-skills.zip snode5:~/
```

## 使用示例

**Review 一整个补丁系列（通读后逐条）**

```text
$review
请 review origin/base..my-feature 的全部 commit。先通读全部 patch 了解整体，再从 1/N 开始总览，不要进入下一条，除非我下指令。
```

**在同一审查过程中自由切阶段**

```text
先带读第 2 个逻辑模块，每次只讲一节。
R2 的锁保护来自后续补丁吗？详细解释并提出解决方案。
排除 R2，R1 先保留。整理所有最终 Gerrit 评论，但暂时不要上传。
```

**草稿保存授权（只允许指定评论）**

```text
我确认最终评论内容和目标 Patch Set。只把 R1、R3 的中文评论保存为 Gerrit 草稿，不要发布、投票或添加 reviewer。
```

**跳到下一条 commit**

```text
这一条完成，开始下一条 commit 的总览。
```

**独立带读，无需 Gerrit**

```text
$tutor
带我阅读 lib/utils/cppc/fdt_cppc_rpmi.c，先规划章节，一次只讲一章。
```

## 状态与清理

Review 会话保存在 `<workspace>/.ai/sessions/review/repo-<hash>/series-<hash>/state.md`。工作区默认是执行命令时的当前目录，也可用 `--workspace` 显式指定；`--repo` 指定审查仓库，不改变保存位置。会话文件不应提交到 Git。Tutor 不创建独立会话，仅在你明确要求保存进度时，在工作区内写一份简短记录（默认 `.ai/tutor-progress.md`）。可在工作区目录查询 Review 会话：

```bash
python3 ~/.agents/skills/review/scripts/session.py list --workspace "$PWD" --repo "$PWD"
```

保存单条 commit 的草稿后，如果系列尚未结束，会话仍然保留；全部完成并验证后，Skill 按 `references/session.md` 清理**本次**会话。Gerrit 未发布草稿不受本地状态删除影响。

## Gerrit 访问前提

- Gerrit 实例、Change / Patch Set 要可确认，且本地 Commit SHA 与 Gerrit Revision SHA 必须一致。
- 默认通过 `ssh -p 29418 gerrit.dc.com`，使用已有 SSH key、agent 或 SSH 配置认证；可按任务指定其他主机、端口和用户名。不要把私钥或口令写入 Skill、状态文件或仓库。
- SSH 仅用 `gerrit query --format=JSON` 做只读查询；保存未发布草稿使用 HTTPS REST Draft 接口，需要实际 Web URL 和已有 HTTP 认证。缺少认证时只保留本地预览。
- 禁止调用 SSH `gerrit review` 或 REST Set Review 发布评论。只保存草稿，不投票、Submit 或添加 reviewer。草稿保存不发送发布通知，也不改变以后人工发布的通知设置。

说明：Skill 是 Agent 工作流程规范，不是额外安装的 Gerrit 插件；实际执行取决于 Codex CLI 可访问的文件系统/网络/认证与执行权限。若权限不足，它应报告阻碍，而非声称成功。
