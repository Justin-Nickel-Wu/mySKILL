# Gerrit 未发布行内草稿工作流

本技能只保存未发布草稿。SSH 仅用于只读查询；保存使用 Gerrit REST Draft 接口。禁止使用 SSH `gerrit review` 或 REST Set Review 提交 comments，它们会发布评论；`notify: NONE`、`notify: ALL` 和 `drafts: KEEP` 都不能将新评论变成未发布草稿。

官方参考：https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#create-draft

## 1. 查询和认证

### 减少重复权限申请

- 区分“允许执行网络命令”和“允许保存指定草稿”。环境权限可复用，但不扩大评论内容或目标范围的授权。
- 首次 SSH 查询需要提权时，若运行环境支持可复用命令规则，申请限定前缀 `["ssh", "-p", "29418", "gerrit.dc.com", "gerrit", "query"]`，供用户选择保存规则。后续查询保持相同命令前缀，避免重复审批。不申请宽泛的 `ssh`、`bash`、`python3` 或 `curl` 通用权限，不把 `gerrit review` 纳入规则。
- 优先通过一次查询取得所需 Patch Set 信息；已有 HTTPS 认证和完整查询能力时，可直接用 REST 查询，减少 SSH 与 HTTPS 来回请求。
- 先准备完整的本次草稿清单、目标、请求文件和可审阅的执行代码，再申请一次执行权限。在这次获批执行中依次完成远端复核、查重、逐条保存、读回验证；任一身份或目标校验失败就停止，不写远端。依赖请求仍按顺序执行，不因合并执行而省略校验。
- 执行代码只能处理本次获批目标与草稿，不增加发布、评分、reviewer 或其他外部操作；不要通过通用解释器的永久规则扩大权限。文案或目标变化后，重新确认变化部分。
- 审批次数由宿主策略决定，技能不能自行授予权限或保证始终只审批一次。规则不可复用或环境仍要求逐次审批时遵守要求，不绕过；不要因已取得环境权限而反复询问已经获得的草稿内容授权。

可沿用已有 SSH 认证查询目标：

```bash
ssh -p 29418 gerrit.dc.com gerrit query --format=JSON --patch-sets --current-patch-set 'commit:<full-commit-sha>'
```

查询结果是逐行 JSON，末尾统计对象不是 Change。核对 project、branch、Change、Patch Set 和完整 revision SHA；必须与本地 `git rev-parse <target>` 一致。旧 Patch Set 需确认目标版本。

草稿接口需要实例实际的 HTTPS base URL 和 HTTP 认证。SSH 主机及端口不能直接推出 Web URL，SSH key 也不等同于 HTTP 凭据；使用用户已有配置，例如受保护的 `.netrc`（权限 600）中的 Gerrit HTTP 密码。不要输出、复制或写入凭据。缺少 URL 或认证时保留本地预览，报告所缺信息，不执行发布命令作为替代。

以下命令假定 `GERRIT_BASE_URL` 是已核实的 HTTPS base URL，`CHANGE_ID` 是已核实并正确 URL 编码的 Change 标识，`REVISION_SHA` 是已核实的完整 SHA；变量必须实际赋值，不将占位符发送到服务器。通过 HTTPS 查询 detail 再次核对实例、账号和目标：

```bash
curl --fail-with-body --silent --show-error --netrc "${GERRIT_BASE_URL}/a/changes/${CHANGE_ID}/detail?o=ALL_REVISIONS"
```

## 2. 预览与位置核对

展示 R#、Change、Patch Set、完整 SHA、path、side、line 和完整中文正文；得到保存指定草稿的明确授权后才写远端。

`path` 为目标文件仓库相对路径，`line` 为从 1 开始的物理行号。新增和修改用 REVISION，删除用 PARENT；用匹配 SHA 的文件内容核对。重命名、合并提交的父侧及 range 需额外核实。正文日常、简短、直接，技术条件和影响不能省略到失真。

## 3. 先查重，再逐条保存

先查询当前账号在目标 revision 上的草稿，按 revision、path、side、line、message 查重。网络或认证失败不能当作空列表。Gerrit JSON 可能带首行 XSSI 前缀，解析时先核对并移除该前缀，不将错误页当成 JSON。

```bash
curl --fail-with-body --silent --show-error --netrc "${GERRIT_BASE_URL}/a/changes/${CHANGE_ID}/revisions/${REVISION_SHA}/drafts/"
```

每条草稿使用一个 DraftInput。将本次获批内容保存为当前工作区内、本次任务专用临时 JSON，以下仅为虚构示例：

```json
{
  "path": "subsys/ras/ras_queue.c",
  "side": "REVISION",
  "line": 169,
  "message": "这里先检查一下索引范围，超过队列容量会越界访问。"
}
```

```bash
curl --fail-with-body --silent --show-error --netrc -X PUT \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --data-binary @.ai/review-draft.json \
  "${GERRIT_BASE_URL}/a/changes/${CHANGE_ID}/revisions/${REVISION_SHA}/drafts"
```

此处不发送 `notify`：创建 Draft 不触发评论发布通知，也不修改以后人工发布时的通知设置。不得附带 labels、reviewers、submit 或发布操作，不批量向未获授权的其他 commit 写入。

## 4. 读回与失败处理

- 成功响应后记录 draft ID，再 GET 目标 revision 的 drafts，核对 id、path、side、line 和完整 message。只报告实际保存并核实的草稿，不称“已发布”。
- 超时或断线可能发生在服务器已保存之后；先查询查重再决定重试。无法确认时保留会话和未确认项，不盲目重试。
- 已经公开发布的评论不能通过创建草稿恢复为未发布；本流程不自动删除或修改历史评论。
- 按 session 规范仅清理本次本地记录和临时 JSON，不删除服务端草稿或其他任务文件。不调用 Publish、Set Review、投票或 Submit。
