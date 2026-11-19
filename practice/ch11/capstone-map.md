# 第 11 章 練習 1：Capstone 六道閘門對照全書十章

執行結果：

- `harnesslab.cli capstone --json` → `ch11/capstone.json`：`triage_status: QUARANTINED_PROMPT_INJECTION`、`quarantine_findings: ["possible instruction injection: exfiltrate", "possible instruction injection: system prompt"]`、`patch_status: PATCH_SYNTHESIZED`、`patch_diff_hash: a884ace4…b565`、`deploy_status: DEPLOYED_TO_PRODUCTION`、`evidence_envelope_hash: cc2e2129…1b78`、`total_decisions_recorded: 7`。
- `python -m pytest capstone/test_capstone.py -v` → `ch11/capstone-test.txt`：**2 passed**（`test_end_to_end_remediation_workflow`、`test_clean_report_passes_without_quarantine`）。

六道閘門依 `HarnessLab/WORKBOOK.md` 第 4 節「Mandatory Control Gates」。capstone.json 只輸出 7 個摘要欄位，沒有逐筆決策；我另外在 scratchpad 用 `RemediationFleet` 重跑同一份報告，印出 `fleet.decisions` 的 7 筆（沒有修改原始碼），下表的「決策」欄來自那次輸出。

## 1. 六道閘門對照表

| # | 閘門（WORKBOOK） | remediation_fleet.py 的對應程式 | capstone.json 證據欄位＝實際值 | 對應章 |
| --- | --- | --- | --- | --- |
| 1 | **Audience-Bound Tokens**：分流的憑證不能拿來部署 | `execute_workflow` 部署段（第 147～154 行）：`self.harness.broker.verify(triage_token, "production-deploy")`，並 `assert` 必須是 DENY；再驗 `deploy_token` | 沒有專屬欄位；間接證據是 `total_decisions_recorded: 7`（其中決策 4 = deny `credential audience mismatch`、決策 5 = allow `credential valid`） | 第 3 章（身分、受眾綁定、委派鏈） |
| 2 | **Context Quarantine**：外部報告的注入要先清掉才交給修補代理 | 分流段（第 60～80 行）：`ContextItem(trust_tier=EXTERNAL)` → `self.harness.context.inspect(raw_item)`，被隔離時改用 `sanitized_text` | `triage_status: QUARANTINED_PROMPT_INJECTION`；`quarantine_findings`：`exfiltrate`、`system prompt` | 第 5 章（信任分級、防投毒） |
| 3 | **Intent Contract**：修補代理只能改回報相關的檔案 | 修補段（第 95～118 行）：`IntentContract(goal="patch reported vulnerability in target module", allowed_tools={patch_repo, write_memory, emit_trace}, max_risk=REVERSIBLE_WRITE)` → `self.harness.intent.verify` ＋ `self.harness.gateway.check` | `patch_status: PATCH_SYNTHESIZED`（決策 1 allow `intent contract satisfied`、決策 2 allow `tool gateway accepted call`） | 第 4 章（意圖合約）＋第 1 章（兩層控制） |
| 4 | **Memory Ledger**：成功的修補摘要寫入記憶，失敗的實驗要墓碑化 | 修補段（第 121～129 行）：`self.harness.memory.propose_write(key=f"patch_{target_file}", trust_tier=TENANT)` | 沒有專屬欄位（決策 3 allow `memory record mem_… stored`） | 第 6 章（記憶帳本、墓碑） |
| 5 | **Human Approval Gate**：部署前要有明確的密碼學核准憑證 | 部署段（第 157～175 行）：`self.harness.gateway.check(deploy_call)`，接著 `human_approval_present = True` → ALLOW `deploy authorized by signed human operator token` | `deploy_status: DEPLOYED_TO_PRODUCTION`（決策 6 gateway allow、決策 7 `human_gate` allow） | 第 2 章（核准佇列）＋第 8 章（執行期介入） |
| 6 | **Verifiable Audit Envelope**：封存報告、diff、測試結果、部署收據的 SHA-256 | 第 180～188 行：`self.tracer.envelope(artifacts={target_file, patch_diff_hash, sanitized_report})` → `envelope.tamper_evident_hash()`；三個 span：`triage_agent_ingest`、`patch_agent_generate`、`deploy_agent_release` | `evidence_envelope_hash: cc2e2129601d…1b78`；`patch_diff_hash: a884ace4…b565` | 第 7 章（證據信封） |

全書十章中沒有直接出現在 capstone 的：第 9 章（代理群配額、冪等），只有三個依序執行的代理，沒有並行與重試；第 10 章（資料分級路由、外流管控、刪除證明），只用到 data_class 欄位，沒有 `governance.route`。

## 2. 三個代理的身分、權限與交接

| 代理 | AgentIdentity | 憑證（broker.issue） | 權限 |
| --- | --- | --- | --- |
| 分流 | `triage-agent-01`，role `triage`，tenant `enterprise-secops` | audience `triage-service`，ttl 300 秒，chain `orchestrator → triage-agent-01` | 只讀外部報告；報告以 `EXTERNAL` 信任等級進防火牆 |
| 修補 | `patch-agent-01`，role `coder` | audience `repo-service`，ttl 600 秒，chain `orchestrator → patch-agent-01` | 意圖合約只允許 patch_repo／write_memory／emit_trace，資料 internal／public，風險上限 reversible_write，10 分鐘到期；記憶以 `TENANT` 等級寫入 |
| 部署 | `deploy-agent-01`，role `deployer` | audience `production-deploy`，ttl 300 秒，chain `orchestrator → deploy-agent-01` | deploy_service（privileged_operation），需要人工核准 |

**交接方式：**

- 三張憑證的委派鏈都是 `orchestrator → 自己`，代理之間**沒有直接委派**，由 orchestrator 逐一發憑證（星狀，不是鏈狀）。
- 分流 → 修補：交接的是**資料**，不是權限。被隔離時交出固定的 `sanitized_text`（「Sanitized report: SQL injection vulnerability in search query parameter.」），沒被隔離就交原文。
- 修補 → 部署：交接的是 `patch_diff_hash`，部署代理拿這個雜湊去部署 `search-api v1.4.2-patch`。
- 憑證的受眾互不相通：決策 4 證明分流憑證拿去 `production-deploy` 會被拒。

照實記錄：`triage_token` 與 `patch_token` 在各自的工作中**從來沒被驗證過**，只有部署段用到 broker.verify；修補代理也沒有出示憑證就做了意圖檢查。

## 3. 單元測試涵蓋了哪些閘門

`capstone/test_capstone.py` 有 2 個測試：

| 閘門 | 有沒有被測到 | 怎麼測的 |
| --- | --- | --- |
| 1 受眾綁定 | **間接**：測試沒有斷言它，但 `execute_workflow` 內的 `assert triage_cross_call.decision == Decision.DENY` 若失敗會讓測試報錯 | 程式內 assert，不是測試斷言 |
| 2 上下文隔離 | **有** | 注入報告 → `triage_status == QUARANTINED_PROMPT_INJECTION` 且 findings 非空；乾淨報告 → `CLEAN` |
| 3 意圖合約 | **形式上有，實際沒有** | 只斷言 `patch_status == PATCH_SYNTHESIZED` 與雜湊長度 64；但 `patch_status` 是**無條件**設定的，不看 `d_intent` 的結果 |
| 4 記憶帳本 | **沒有** | 沒有任何斷言檢查記憶寫入、晉升或墓碑 |
| 5 人工核准 | **只測了「核准後會部署」** | `deploy_status == DEPLOYED_TO_PRODUCTION`；沒有測「沒有核准時要停在 PENDING_APPROVAL」，因為 `human_approval_present` 寫死成 True，測不到另一條路 |
| 6 證據信封 | **只測了存在** | 雜湊長度 64、決策數 ≥ 6；沒有測竄改後雜湊會變，或內容是否涵蓋 WORKBOOK 要求的四樣東西 |

**沒有被測試涵蓋的：閘門 4（記憶帳本）完全沒有。** 閘門 3 和閘門 5 也只測到「正常路徑通過」，沒有任何負向測試。

我另外做了一個小實驗（scratchpad，沒有修改原始碼）：把目標檔案換成 `auth/login.py`，結果仍是 `PATCH_SYNTHESIZED`，7 筆決策和原本一樣（6 allow＋1 deny）。WORKBOOK 說「修改 authentication 或 billing 檔案要立刻觸發偏移警告」，參考實作**沒有做到**：合約沒有檔案範圍，`target_file` 也沒有被任何控制檢查。

## 4. 離正式上線還差哪三件事

1. **核准是寫死的，不是簽章。** `human_approval_present = True` 加上一句 reason「signed human operator token」，實際上沒有任何憑證、簽章或核准人身分。正式版需要：核准請求進第 2 章的核准佇列，由有權限的人用自己的身分簽一張**綁定這次 diff 雜湊、服務、版本、到期時間**的核准憑證；部署前驗簽，並把核准憑證的雜湊放進證據信封。缺核准就停在 `PENDING_APPROVAL`，而且要有測試證明這條路會停。
2. **閘門的結果沒有真的擋住流程。** 意圖檢查、閘道檢查、記憶寫入的決策只被 `append` 進清單，沒有任何 `if not allowed: stop`：`patch_status`、`deploy_status` 不管前面判什麼都照樣設定，部署代理也沒有意圖合約或預算。正式版要讓每一道閘門都是**硬性前置條件**（deny 就中止、escalate 就排隊），合約要加上檔案範圍（只准改回報的模組，碰 auth／billing 就偏移警告），並為每道閘門補上負向測試。
3. **隔離只靠關鍵字，而且「清理」是一句寫死的摘要。** 防火牆只抓到 `exfiltrate` 和 `system prompt`，`Ignore previous rules` 沒有被抓（標記清單是 `ignore previous instructions`）；第 5 章練習 2 已經示範換句話說就能 0/6 全部繞過。被隔離後交給修補代理的 `sanitized_text` 是固定字串，不是從報告萃取出來的。正式版要以**信任等級限制能力**：外部報告只能產生結構化欄位（端點、漏洞類型、重現步驟），由程式驗證格式，不能成為指令；讀過外部內容的代理不能直接觸發寫入或部署工具。

（另外，證據信封只封了 `target_file`、一個由**固定字串**算出的 `patch_diff_hash` 和清理後摘要。WORKBOOK 要求的「原始報告、git diff、測試結果、部署收據」四個雜湊都沒有，`self.decisions` 這 7 筆決策也沒有被封進信封。這也是上線前要補的。）
