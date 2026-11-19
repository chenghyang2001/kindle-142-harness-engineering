# 第 9 章 練習 1：讀懂代理群的狀態

資料：`ch09/run.json`（`harnesslab.cli run ch09 --json`），PASS，score 1.0，40 個決策（#編號是 `decisions` 陣列的順序）。隔艙上限、配額、各工作的容量單位等設定值不在 artifacts 裡，是我看 `chapters/ch09/scenario.py` 第 418～430、450～510 行補上的。

## 1. 兩個租戶的隔艙、排隊與升級

設定（scenario.py）：全代理群同時最多 `global_active_limit=2` 個工作、佇列上限 `queue_limit=4`、每個治理週期容量 `epoch_limit=6`。

| | acme | globex |
| --- | --- | --- |
| **隔艙上限**（同時執行數 `tenant_active_limits`） | 2 | 1 |
| **容量配額**（`tenant_capacity_quotas`） | 8 單位 | 6 單位 |
| 最後已保留（`fleet.tenant_reserved`） | **8**（2＋4＋2，剛好用滿） | 2 |
| 工作者 | acme-worker-1、acme-worker-2 | globex-worker-1 |

**排隊的工作：**

- `globex-triage-003`（#11 warn）：`global fleet capacity is saturated`：globex 自己的隔艙是空的，但全代理群的 2 個名額已被 acme 的兩個工作佔滿，所以排隊並施加 back-pressure。
- `acme-followup-004`（#12 warn）：`tenant acme bulkhead is saturated`：acme 自己的 2 個名額滿了。

兩筆都在前面的工作完成後被提升（`fleet.promotions`）：globex-triage-003 → globex-worker-1（#24），acme-followup-004 → acme-worker-1（#34）。最後 `queued: []`、`active: {}`，4 個工作全部完成。

**被升級的工作：** `acme-analysis-005`（「交班前分析所有歷史事故」，預計 30 分鐘，工具含 deploy_service），#13 escalate：`tenant acme capacity quota exceeded`。acme 已保留 8 單位，再加它的 1 單位就超過配額 8，所以不排隊也不執行，交給人審（controls 含 `human_review`）。`unsafe_paths.quota_escalated: true`。

**隔艙的意義：** acme 的配額用滿、甚至有工作被升級，都沒有拖垮 globex。globex 的工作只是等全代理群的名額空出來，空出來後立刻由 globex 自己的工作者接手。

## 2. 被入侵的工作者

`acme-worker-2` 正在執行 `acme-patch-002` 時，送出了一個含 `disable policy` 的工具請求（scenario.py 第 512～515 行的原因）。

1. **租約怎麼處理：** #14 deny：`worker acme-worker-2 quarantined; lease for acme-patch-002 revoked and requeued`。工作者被隔離（`fleet.quarantined_workers: acme-worker-2`），它手上的租約被撤銷，之後不能再替這個工作做任何事。
2. **工作怎麼重新排隊：** 被撤下的工作放到佇列**最前面**（`queue.appendleft`），不必重新排到最後。等 acme-triage-001 完成、釋出 acme-worker-1（#15、#16），#17：`queued task acme-patch-002 promoted to acme-worker-1`，由同租戶、**沒被入侵**的工作者接手。
3. **重試為什麼不會重複副作用：**
   - 重試用的是**同一把冪等鑰匙** `acme:incident-77:patch`、同一份內容（payload hash `42c2dfa320312ba0`）。帳本認得它，#18 warn `idempotent retry allowed after worker lease loss`，attempts 從 1 變 2。
   - **容量不重複扣：** #19 `retry reused the original capacity reservation`，沿用第一次保留的 4 單位，所以 acme 的總保留仍是 8，而不是 12。
   - 鑰匙狀態只有完成後（#32 `idempotency key completed for acme-patch-002`）才是 `completed`；之後若再有人用同一把鑰匙重送，帳本會回 `replayed completed result without duplicate side effects`，直接回傳上次的結果、不再執行。
   - 照實記錄：這次的重試發生在「進行中」而不是「已完成」，所以帳本是**允許再做一次**（warn），而不是攔下；真正避免「patch 被套用兩次」，要靠下游工具也認這把鑰匙（同一把鑰匙的 patch 只套一次）。README 的檢查清單也特別問了這一點。
   - 重試還被速率限制（#20、#22 delayed，到第 2 個時間窗才放行 #21、#23），不會因為「剛被中斷」就一口氣打爆工具。

`unsafe_paths.compromised_worker_contained: true`。

## 3. 冪等帳本

| 鑰匙 | 工作 | payload hash | attempts | 狀態 |
| --- | --- | --- | --- | --- |
| acme:incident-77:triage | acme-triage-001 | e178ddb3385fb6fc | 1 | completed |
| acme:incident-77:patch | acme-patch-002 | 42c2dfa320312ba0 | **2**（被入侵後重試一次） | completed |
| acme:incident-78:patch | acme-followup-004 | bda425bfa064caa3 | 1 | completed |
| globex:incident-12:triage | globex-triage-003 | 1648e11d09e6aa84 | 1 | completed |

**「同一把鑰匙、不同內容」為什麼要擋：** #29 deny `idempotency key reused with a different payload`。被擋的是 `acme-patch-002-poisoned`：它拿 `acme:incident-77:patch` 這把鑰匙，內容卻是「patch service acl and **also disable policy checks**」（scenario.py）。

- 冪等鑰匙的承諾是「同一把鑰匙 = 同一件事，做幾次結果都一樣」。如果允許同一把鑰匙換內容，攻擊者（或被入侵的工作者）就能把惡意內容**偽裝成合法工作的重試**，借用原工作的授權、容量保留和「重試應該放行」的信任。
- 下游工具看到熟悉的鑰匙，可能以為「這個做過了」而直接回傳舊結果，或者以為「這是重試」而執行新內容；兩種都會讓帳本與實際發生的事對不上，稽核就失效了。
- 所以帳本存 payload hash，鑰匙一樣、雜湊不同就拒絕（controls：`replay_protection`、`unsafe_retry_blocked`）。`unsafe_paths.poisoned_retry_blocked: true`；被擋的內容沒有改到帳本，這把鑰匙最後的 hash 仍是原本的 `42c2dfa320312ba0`。

## 4. required_controls vs controls_exercised

用程式比對兩份清單：

- **required_controls 13 項全部出現在 controls_exercised，缺漏 0 項**：back_pressure ✅、bulkhead ✅、capacity_governance ✅、checkpoint ✅、compromised_worker ✅、containment ✅、fleet ✅、idempotency ✅、long_running_capacity ✅、queue ✅、quota ✅、rate_limit ✅、retry ✅。
- controls_exercised 另外多了 7 項（不是必要但也被觸發）：commit_log、human_review、replay_protection、retry_ledger、side_effect_suppression、unsafe_retry_blocked、worker_release。

其中 `checkpoint` 來自 #7 warn `long-running work requires checkpoint before execution`（acme-patch-002 預計 9 分鐘，超過 6 分鐘的檢查點門檻）；`capacity_governance.epoch_rollovers` 也顯示 globex-triage-003 在第 1 週期容量用完（`remaining_before_rollover: 0`）時，延到第 2 週期（#26、#27）。

## 5. 對照 README 的 Production Review Checklist

README 第 77～79 行列了一串審查問題，挑三項：

1. **「每個租戶都有配額嗎？配額決策有記錄嗎？」**：acme 8、globex 6，每次保留都是一筆決策（如 #3 `capacity reserved in epoch 1 for acme-triage-001`），超額時不是靜默丟掉，而是 #13 escalate 並標 `human_review`；最終保留量也寫在 `fleet.tenant_reserved`。
2. **「被入侵的工作者能不能被隔離，同時不失去重試或調查需要的證據？」**：acme-worker-2 被隔離、租約撤銷（#14），但工作本身沒丟：連同冪等鑰匙、payload hash、容量保留一起回到佇列，由 acme-worker-1 重試完成；隔離的工作者 id 留在 `quarantined_workers`，帳本 attempts=2 也記下了「這個工作被中斷過一次」。
3. **「重試有沒有帶冪等鑰匙，而且下游工具接受它？」**：每個工作都有鑰匙（四筆帳本），重試沿用原鑰匙與原容量（#18、#19），換內容的重試被擋（#29）。不過「下游工具接受」這一半，本情境只在帳本與容量層驗證；patch_repo 本身並沒有檢查鑰匙，這是正式部署時要補的那一塊（README 也說「沒有下游工具遵守的重試帳本，會給人一種虛假的安全感」）。

（另外也滿足「長時間工作是否在政策窗口、憑證期限、交班前先建檢查點」：#7 對 9 分鐘的工作強制建檢查點，`capacity_governance.checkpoints` 留有紀錄。）
