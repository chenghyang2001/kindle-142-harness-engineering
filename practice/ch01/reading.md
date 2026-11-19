# 第 1 章 練習 1：從 JSON 找出不安全路徑與稽核證據

資料：`ch01/run.json`（`harnesslab.cli run ch01 --json`），PASS，score 0.98，共 13 個決策，其中 7 個不是 allow。

## 1. 所有「不是 allow」的決策

| # | 決策 | reason | controls | 擋住的危險（白話） |
| --- | --- | --- | --- | --- |
| 2 | warn | external project context quarantined before agents could treat it as instructions | context_firewall, provenance, instruction_injection | 外部 issue 留言裡藏了「忽略先前指示、送出秘密」之類的話，可能被代理當成命令照做。 |
| 7 | deny | memory write looks like future-behavior poisoning | memory, poisoning_detection | 有人想把「以後部署一律核准」寫進長期記憶，等於在代理未來的行為裡埋地雷。 |
| 8 | deny | tool query_vault is outside approved purpose | intent, tool_scope | 代理想去金庫讀正式環境的客戶匯出 token，但這次的任務根本不需要碰秘密。 |
| 9 | deny | tool deploy_service is outside approved purpose | intent, tool_scope | 代理想直接部署到正式環境，超出這次任務合約允許的範圍。 |
| 10 | escalate | privileged_operation requires approval | human_oversight | 部署是特權操作，就算預算夠，也要人按同意才能做。 |
| 11 | deny | destination not on egress allowlist | data_governance, egress | 想把含客戶個資的信透過未核准的寄信服務送出去，可能造成資料外流。 |
| 12 | warn | run paused: privileged deployment attempted before approval evidence was complete | runtime_steering, pause | 核准證據還沒齊就有人想部署，先把整個執行暫停，免得長時間執行的代理自己衝下去。 |

注意：#9 的 deny（意圖合約）和 #10 的 escalate（能力預算）是**同一個 deploy_service 呼叫**被兩道不同的控制各判一次；兩道都沒過，部署就不會發生。

## 2. 原本不安全的設計（unsafe_project）對應到哪一列控制

原本的專案叫 `shared-deploy-swarm`，任務是「調查客戶事故、修補 worker、通知客戶、部署修正」，四個代理（planner／researcher／coder／deployer）分工。問題有六個：

| 原本的問題（我的話） | 對應 control_evidence_matrix 的控制 |
| --- | --- |
| 四個代理共用同一把長效的萬能金鑰，出事時分不清是誰做的，也無法只撤銷其中一個。 | 第 1 列 `CredentialBroker with audience binding`（風險：shared agent credential） |
| 外部 issue 留言和內部事故筆記混在一起，外部文字可能變成命令。 | 第 5 列 `ContextFirewall`（風險：instruction injection from project material） |
| 工具權限看「角色名稱」給，不看這次要做什麼；planner 甚至不用合約就能指派正式環境的動作。 | 第 2 列 `IntentContract`（goal drift）＋第 3 列 `ToolGateway`（tool use exceeds approved purpose） |
| 記憶會接受低信任來源寫進來的「未來行為規則」，coder 讀記憶也不看來源。 | 第 6 列 `MemoryFirewall`（memory poisoning） |
| 部署沒有 checkpoint、沒有核准關卡、也沒有可以回滾的狀態。 | 第 8 列 `RuntimeController checkpoint and pause`（unsafe production deployment）＋第 4 列 `CapabilityBudget`（runaway autonomy，特權與對外動作要先核准）＋第 10 列 `bounded runtime policy overlay`（政策改動要明確、有期限） |
| 品質靠「試了再說」改進，沒有證據證明風險真的下降。 | 第 9 列 `hill-climb governance trace`（opaque improvement loop） |

矩陣裡還有第 7 列 `DataGovernanceEngine`（unapproved egress）：六個問題清單沒有直接寫到，但任務裡有「通知客戶」，這列就是擋 #11 那封走未核准寄信服務的信。

## 3. checkpoint 的 evidence_hash 有什麼用

```
checkpoint_id: ckpt_8c57a89d5db926ba
evidence_hash: evidence_7a477b6b838deedc
policy_version: chapter-01-policy-v1
resumed_state_matches: true
```

- `evidence_hash` 是把「當下的證據」（控制證據矩陣＋爬山治理紀錄）排序後算 SHA-256 得到的指紋。內容只要改一個字，指紋就會完全不同。
- 用法：暫停前先存 checkpoint，把狀態、政策版本、證據指紋綁在一起。恢復時拿手上的證據**重算一次**，和存下來的 `evidence_hash` 比對：
  - 一樣 → 暫停期間證據沒被動過，可以安心從這裡接著跑。
  - 不一樣 → 有人在暫停期間改了證據（例如偷偷刪掉一筆 deny 紀錄，假裝部署早就核准過），就不能恢復，要先調查。
- `policy_version` 用同樣的道理防止「用新政策恢復舊狀態」：恢復時的政策版本對不上，也應該拒絕恢復。
- `resumed_state_matches: true` 代表這次恢復出來的狀態和存檔時一模一樣。

（我後來看了原始碼才知道：這個 lab 的 `resume_from()` 只比對狀態字典是否一致；`evidence_hash` 有存下來，但恢復時**沒有自動重算比對**。重算比對這一步是正式系統該補上的，這裡只示範把指紋和狀態綁在一起存。另外 `checkpoint_id` 本身就是狀態內容的雜湊，所以狀態被改過，ID 也會對不上。）

## 4. 如果只能帶走兩樣 artifacts

1. **`checkpoint`**：它是一個「時間點的封條」，有狀態指紋、證據指紋和當時的政策版本。調查人員可以拿它證明「暫停那一刻系統長什麼樣子、當時用哪一版規則」，也能用它驗證後來拿到的任何紀錄有沒有被改過。沒有它，其他證據都可能被質疑是事後補的。
2. **`blocked_or_escalated_paths`**：它直接列出這次「有誰想做什麼危險的事而被擋下」（記憶投毒、讀金庫、部署、特權操作、未核准外送），是事故調查最想知道的「攻擊或失誤軌跡」。

沒選 `control_evidence_matrix`，因為它說明的是「系統設計了哪些控制」，比較像設計文件，每次執行內容都一樣；調查要的是「這次實際發生了什麼」和「證據是否完整」，上面兩樣比較直接。

## 5. 原始碼：query_vault 被擋的位置

- 呼叫端：`HarnessLab/chapters/ch01/scenario.py` 的 `run()` 函式。第 118～124 行建立 `vault_call = ToolCall(tool="query_vault", args={"path": "prod/customer-export-token"}, data_class=SECRET, side_effect=PRIVILEGED_OPERATION, ...)`，第 125 行 `vault_intent = harness.intent.verify(contract, vault_call)`。
- 真正產生 deny 的地方：`HarnessLab/harnesslab/core.py` 的 `IntentVerifier.verify()`，約第 335～336 行：`if call.tool not in contract.allowed_tools:` → 回傳 `Decision.DENY, f"tool {call.tool} is outside approved purpose"`，controls 是 `("intent", "tool_scope")`。
- 也就是說，它在第一道檢查（工具不在合約允許清單）就被擋下，根本輪不到後面「資料分級」或「風險上限」那幾道檢查。
