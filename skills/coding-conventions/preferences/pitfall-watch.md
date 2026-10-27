# Pitfall Watch

本文件保存尚未达到长期工程约定门槛的一次性 pitfall signature。它不是执行规则；agent 仅在后续 audit 命中同一归一化机制时更新 occurrence，不能因为本文件存在就主动加载或约束项目。

每条候选记录 `Signature`、首次与最近证据、独立 session / project occurrence 数，以及下一次命中后的处置。首次命中不进入模板；同一 signature 在独立 session / project 第二次命中后评估 temporary pitfall，跨项目持续复现后才评估长期模板。

## Watch

### text.patch.legacy-eof-whitespace-collateral

- 首次证据：2026-08-05，在 `idp-mgmt-api` 修改 legacy RST scope 文本时，通用 patch 顺带为多个文件补 EOF newline，并改变一个文件的末尾空行；用户在 MR 中指出 whitespace diff 后，才按 merge base 恢复 8 个纯 whitespace hunk。
- 最近证据：2026-08-05。
- 独立 occurrence：1 session / 1 project。
- 下次命中：若来自独立 session 或 project，更新 occurrence 并评估 temporary pitfall；修改保留非标准 EOF/尾空行的 legacy 文本后，先比较普通 diff 与 `--ignore-all-space` diff，避免把格式副作用带入 MR。

### ocr.identifier.ambiguous-glyph-unverified

- 首次证据：2026-08-01，从截图重建的 IDaaS domain ID 把小写 `l` 识别成数字 `1`，导致身份查询持续 404 并误导到备用 ID 语义；列出权威域后复制 exact ID 才恢复，并修正了两份 SQL 中的硬编码。
- 最近证据：2026-08-01。
- 独立 occurrence：1 session / 1 project。
- 下次命中：若来自独立 session 或 project，更新 occurrence 并评估 temporary pitfall；截图 OCR 得到的不透明 ID 在远程调用或持久化前，先与权威列表或接口返回做 exact equality 核对。

### sql.identity-binding.cross-entity-carryover

- 首次证据：2026-07-31，在为 Partner 用户“示例主体”生成飞书绑定 SQL 时沿用了上一轮“示例用户”的 `feishu_user_id`，用户在执行前指出主体不一致后才重新匹配飞书清单。
- 最近证据：2026-07-31。
- 独立 occurrence：1 session / 1 project。
- 下次命中：若来自独立 session 或 project，更新 occurrence 并评估 temporary pitfall；生成外部身份绑定 SQL 前先对目标业务用户与外部身份做同主体最终核对，不沿用上一轮查询值。

### shell.zsh.bash-semantics-assumed

- 机制：Bash 工具实际在 zsh 中执行内联脚本，却按 bash 语义写变量和分词。
- 首次证据：2026-07-21，zsh 内联仓库扫描把命令结果赋给只读特殊参数 `status`。
- 最近证据：2026-10-27，hw:cn-email。循环变量 `path` 覆盖了与 `PATH` 绑定的数组，后续 `tail` 和 `cut` 报 command not found。同一会话中，zsh 不按空白拆分 `set -- $spec`，`$1` 拿到整串，`$2` 为空，请求路径因此出错。
- 独立 occurrence：2 sessions / 2 projects（按 mechanism 合并原 `shell.zsh.readonly-status-variable`）。
- 晋升评估（2026-10-27）：次数已达评估门槛，但暂不晋升。`temporary.md` 不在 `sync-conventions.sh` 的同步列表中，coding-conventions 也只在 SQL 方言场景路由到它，写内联 shell 时不会加载，晋升后不会生效。若要生效，需放到写 shell 时必然加载的位置（全局规则 §3 的 shell 条目），由用户决定。
- 下次命中：更新 occurrence。多行或需要分词的内联脚本写成 `bash` 脚本文件或 `bash -c`；变量名避开 zsh 特殊参数，包括已命中的 `status` 和 `path`。
