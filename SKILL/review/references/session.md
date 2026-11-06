# Review session: 一次性状态文件规范

## 固定存放位置

会话根目录：`<workspace>/.ai/sessions/review/`，保存在当前工作区内；不要 git add，不要保存在 Skill 安装目录。`<workspace>` 是本次任务的可写工作区，可以包含多个仓库，不必是 Git 根目录。

使用本 Skill 附带的工具管理目录：`python3 <review-skill-dir>/scripts/session.py ...`。工具使用仓库 `realpath` 的 SHA-256 前 12 位生成 `repo-<key>`，使用 series 标识 SHA-256 前 12 位生成 `series-<key>`；每次单独的 review 可用唯一的自定义 series 标识，避免覆盖。最终结构：

```text
<workspace>/.ai/sessions/review/
  repo-<repo-hash>/
    series-<series-hash>/
      .code-review-session
      state.md
```

脚本默认使用执行命令时的当前目录作为工作区。Agent 应在启动时确定工作区绝对路径，后续 `start`、`list`、`finish` 均使用同一个 `--workspace`，避免切换目录后找不到会话。`--repo` 仅标识被审查的仓库，不决定存储位置。若目录通过符号链接指向工作区外，脚本会拒绝写入。

## 启动/恢复命令

```bash
python3 <skill-dir>/scripts/session.py list --workspace /absolute/workspace --repo /absolute/workspace/repository
python3 <skill-dir>/scripts/session.py start --workspace /absolute/workspace --repo /absolute/workspace/repository --series 'gerrit-topic-or-explicit-series-key'
```

`start` 如果会话已存在**只回显路径，不重置状态**。先 `list`，如果多个候选会话要向用户确认所选；从已有 `state.md` 恢复，绝不能自行覆盖旧内容。series-key 可以是 Gerrit topic / Change-Id 与补丁序列的组合；不可用短暂可变的当前阶段值作为 key。

如果没有 Gerrit，使用本地明确的 range 与稳定的 series-key（例如 `refs/remotes/origin/topic..HEAD`），并记录当时完整 SHA 数组，随时检查变化。

## state.md 建议字段

```markdown
# Review state
Repository: /absolute/path
Series key: ...
Git base/tip: <sha> / <sha>
Gerrit server/project/branch: ...
Commits in order:
- 1/N <sha> <subject> (Gerrit change / patch set / revision SHA)
- ...

Series understanding:
- Final feature and responsibilities per commit
- Later fixes / dependencies (which patch adds what)

Current commit: 1/N <sha>
Current stage: overview | walkthrough | issues | comments | drafts
Walkthrough modules:
- [x] module A ...
- [ ] module B ...

Findings (stable IDs, never reuse):
- R1: P1 | 已确认 | 待评论 | path:line | evidence / fix / subsequent patch relevance
- R2: P2 | 待验证 | 讨论中 | ...
Historical issues detected: yes/no (details not displayed by default)

Final comment candidates:
- R1 | path | side | line | exact message | approved-for-draft-save? no
Gerrit drafts saved:
- R1 | revision SHA | draft ID | verified yes/no
Pending actions / decisions: ...
Last checked Git refs and Gerrit revision: ...
```

- 文档可以自然语言维护，不要保存密码、SSH 私钥、口令或其他认证凭据。
- 每次阶段转换、用户排除问题、评论内容定稿或草稿保存返回后立即更新。
- 被用户排除的问题保留其理由，避免恢复后重复提议。
- 开始下一 commit 时保留 series 信息，重新建立该 commit 对应的问题列表（编号可采用 `C2-R1`，也可全局递增，但必须稳定且不混淆）。
- 如果状态已过期、仓库位置不同、目标 SHA 变化，先重新验证、标明冲突；不能直接沿用旧行号。

## 清理准则

- **单 commit**：所有被批准的草稿已保存并通过读回验证、其他问题处置完毕；或者用户明确决定本 commit 不保存草稿且结束。
- **series**：所有 commit 均由用户明确推进并结束，所需草稿均验证成功，且无待办；不能因为单条 commit 草稿保存成功就删除全部状态。
- **中止**：用户明确要求放弃本次 Review 时可删除；提醒尚未保存的本地记录将丢失，Gerrit 已保存的草稿不受影响。
- 永远不能因一次失败的网络请求而判定完成。

```bash
# 仅在达成上述前置条件后，使用实际存在的绝对会话目录：
python3 <skill-dir>/scripts/session.py finish --workspace /absolute/workspace --session-dir '/absolute/session/dir' --yes
```

脚本只允许删除其管理根目录下、带 `.code-review-session` 标记的特定 session 目录；其他项目/其他 series 不受影响。命令本身不检查 Gerrit 完成条件，**这些条件由 Agent 实际验证并向用户汇报**。严禁把 `<workspace>/.ai/sessions/review/` 作为 `--session-dir`。
