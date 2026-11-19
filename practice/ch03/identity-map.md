# 第 3 章 練習 1：委派樹與拒絕對照

資料：`ch03/run.json`（`harnesslab.cli run ch03 --json`），PASS，score 1.0，27 個決策（以下 #編號是決策在 `decisions` 陣列的順序）。租戶都是 `acme`。

## 1. 委派樹

依 `artifacts.agents`（parent_id）、`tasks`、`credential_audiences`、`delegation_chains`：

```
agent-planner（incident_planner，根，parent_id = null）
├── agent-reader（ticket_reader）
│     read_task：task_ead8109e555fbbc4
│     憑證主體 agent-reader:task_ead8109e555fbbc4:g1
│     受眾 → internal-ticketing
│     委派鏈 planner → reader
│
├── agent-patcher（repo_remediator）
│     patch_task：task_bbebede7be25ca6f
│     憑證主體 agent-patcher:task_bbebede7be25ca6f:g1   ✗ 已撤銷
│     受眾 → internal-repo
│     委派鏈 planner → patcher
│     │
│     └── （audit_task 的委派鏈經過 patcher）
│
└── agent-auditor（security_auditor）
      audit_task：task_f3df20ae1bdd2ad1
      憑證主體 agent-auditor:task_f3df20ae1bdd2ad1:g1   ✗ 已撤銷（暫停時輪換）→ 恢復後發 g2
      受眾 → training-console
      委派鏈 planner → patcher → auditor
```

觀察：`agents` 裡 auditor 的 `parent_id` 是 `agent-planner`，但 `delegation_chains.audit_task` 是 `planner → patcher → auditor`。兩者不矛盾：parent_id 是「誰建立了這個代理」（組織結構），委派鏈是「這次任務的權限經過誰轉手」。稽核任務是從 patcher 那邊交接過來的，所以鏈多了一層。調查時要看的是委派鏈，不是 parent。

`revoked_subjects`：`agent-patcher:task_bbebede7be25ca6f:g1`、`agent-auditor:task_f3df20ae1bdd2ad1:g1`。

## 2. 所有 deny 回答了哪個問題

四個問題：**誰在做**（代理身分）／**為哪個任務**（任務身分、目的、時效）／**誰委派的**（委派鏈、可撤銷）／**能用在哪裡**（受眾、資源、資料邊界）。

| # | reason | controls | 回答的問題 | 白話 |
| --- | --- | --- | --- | --- |
| 4 | credential audience mismatch | identity, audience_binding | **能用在哪裡** | reader 拿工單系統的憑證去開程式庫，憑證只對 internal-ticketing 有效。 |
| 5 | credential expired | identity, short_lived_credential | **為哪個任務** | 憑證綁的是一個有時效的任務身分，時間到了，這個任務的授權就結束。 |
| 9 | credential revoked | identity, revocation | **誰委派的** | planner 把交給 patcher 的委派收回了；patcher 嘴上說「我有授權」也沒用，broker 只認撤銷名單。 |
| 13 | credential revoked | identity, revocation | **為哪個任務** | 暫停前那一代（g1）的憑證在恢復前被撤銷，舊世代不能拿來接續恢復後的任務。 |
| 19 | ticket:globex/SEC-999 is outside resource scope for task_ead8109e555fbbc4 | identity, resource_scope | **能用在哪裡** | reader 的任務只能看 `ticket:acme/SEC-203`，想讀另一個租戶 globex 的工單。 |
| 20 | tool query_vault is outside approved purpose | intent, tool_scope | **為哪個任務** | 這個任務的目的不需要讀金庫，工具不在合約清單上。 |
| 24 | data class pii is outside contract | intent, data_scope | **為哪個任務** | 修補任務的合約只准碰 internal 資料，這次 patch 夾帶了個資。 |
| 25 | tool is not approved for this data class | tool_gateway, data_boundary | **能用在哪裡** | 同一筆 PII patch，工具閘道也擋：patch_repo 本來就不能處理 pii。 |
| 26 | repo:acme/customer-export is outside resource scope for task_bbebede7be25ca6f | identity, resource_scope | **能用在哪裡** | patcher 的任務只能改 `repo:acme/checkout-service`，想去碰存客戶匯出資料的 repo。 |

「誰在做」這題沒有對應的 deny，它由 #1 `distinct per-agent identities and parent links established` 和 #2 `each task has a separate actor-bound task identity` 兩筆 allow 先建立起來；後面每一筆 deny 能說出「是 reader 還是 patcher 被擋」，都靠這兩筆。另外 #27 `risk exceeds contract maximum` 是 escalate 不是 deny（部署工具雖然在清單上，風險超過上限，交人決定）。

## 3. 暫停再恢復時，為什麼要輪換憑證

依 #11 `run paused: rotate task credentials before continuing long-running audit` → #12 `revoked 1 paused-run credential before resume` → #13 舊憑證 `credential revoked` → #14／#15 `resumed from checkpoint with a fresh credential generation`（g1 → g2）：

- **暫停期間是最容易外洩的時候。** 程序被暫停，記憶體、checkpoint、log、trace 裡可能都留著那把憑證，放著沒人看的時間越長，被複製走的機會越大。沿用舊憑證，等於承認「這段時間裡任何拿到它的人都還能用」。
- **恢復前先撤銷、恢復後發新的一代**，舊的就算外流也立刻失效；而且世代編號（g1／g2）讓證據能分辨「這個動作是暫停前做的，還是恢復後做的」。
- **恢復是一個重新確認的時機。** 重新發憑證時，harness 可以重新檢查這個任務現在還該不該有這些權限，而不是讓三天前的授權無聲無息地延續下去。

## 4. 最小權限：工具、資料類別、資源各擋了哪一筆

README 的 Least Privilege 段落說：reader 只能用 `read_ticket` 讀一張 acme 工單；patcher 只能對 `repo:acme/checkout-service` 用 `patch_repo` 處理 internal 資料；部署工具雖然放進合約，風險仍超過上限，所以「有工具不代表能用」。對照 `least_privilege` 與決策：

| 範圍 | 擋了哪一筆 | 我的說明 |
| --- | --- | --- |
| **工具** | #20 `tool query_vault is outside approved purpose`（blocked_examples：`tool:query-vault`） | 任務被允許用哪幾樣工具是列清單的（reader：emit_trace、read_ticket；patcher：emit_trace、patch_repo），清單外的直接拒絕。延伸例子是 #27：deploy_service 在 `deployment_review` 的清單裡，但風險超過上限，還是要升級給人；工具範圍只是第一道。 |
| **資料類別** | #24 `data class pii is outside contract` ＋ #25 `tool is not approved for this data class`（`data:pii-repo-patch`） | 就算工具、repo 都對，夾帶的資料等級不對也不行。這筆被意圖合約和工具閘道**兩層同時擋下**：一層說「這次任務不准碰個資」，一層說「這個工具本來就不處理個資」。 |
| **資源** | #19 `ticket:globex/SEC-999 ...`（`resource:cross-tenant-ticket`）＋ #26 `repo:acme/customer-export ...` | 同一個工具、同一種資料，換一個目標就不行。範圍精確到「哪一張工單、哪一個 repo」（`resource_scopes`），擋住跨租戶讀取，也擋住在自己租戶內越界改到別的 repo。 |

三層合起來，一個任務能做的事 = 清單上的工具 × 准許的資料等級 × 指定的資源，三個條件都要符合才放行。
