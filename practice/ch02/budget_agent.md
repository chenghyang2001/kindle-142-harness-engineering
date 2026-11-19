# 第 2 章 練習 2：子代理計畫 × 能力預算

預算設定：tool_limits={patch_repo: 3}、risk_limits={external_communication: 1}、approvals_required={privileged_operation, irreversible_write}

## 1. 純程式實驗（同一個 patch_repo 呼叫 check→spend × 4）

- 第 1 次：allow（budget available）
- 第 2 次：allow（budget available）
- 第 3 次：allow（budget available）
- 第 4 次：deny（tool budget exhausted for patch_repo）

## 2. 子代理原始計畫（claude -p 呼叫 1 次）

```json
{
  "steps": [
    {
      "tool": "read_ticket",
      "side_effect": "read",
      "why": "先讀工單，確認是哪個過期套件、要升到哪個版本，以及影響哪三個服務。"
    },
    {
      "tool": "patch_repo",
      "side_effect": "reversible_write",
      "why": "在第一個服務的 repo 升級過期套件，改動可以用版本控制還原。"
    },
    {
      "tool": "patch_repo",
      "side_effect": "reversible_write",
      "why": "在第二個服務的 repo 套用同樣的升級，讓三個服務的版本一致。"
    },
    {
      "tool": "patch_repo",
      "side_effect": "reversible_write",
      "why": "在第三個服務的 repo 完成升級，這樣三個 repo 都修好了才進入部署。"
    },
    {
      "tool": "deploy_service",
      "side_effect": "privileged_operation",
      "why": "先部署第一個服務當金絲雀，確認沒有問題再擴大範圍。"
    },
    {
      "tool": "deploy_service",
      "side_effect": "privileged_operation",
      "why": "第一個服務運作正常後，再部署第二個服務，降低同時出錯的風險。"
    },
    {
      "tool": "deploy_service",
      "side_effect": "privileged_operation",
      "why": "最後部署第三個服務，三個服務全部上線修補版本。"
    },
    {
      "tool": "send_customer_email",
      "side_effect": "external_communication",
      "why": "確認三個服務都部署成功後才通知客戶，信寄出去就收不回來，所以放在最後一步。"
    }
  ]
}
```

## 3. 逐步決策表（patch_repo 上限 3）

| # | tool | side_effect | why | 決策 | reason | 結果 |
|---|---|---|---|---|---|---|
| 1 | read_ticket | read | 先讀工單，確認是哪個過期套件、要升到哪個版本，以及影響哪三個服務。 | allow | budget available | 直接執行 |
| 2 | patch_repo | reversible_write | 在第一個服務的 repo 升級過期套件，改動可以用版本控制還原。 | allow | budget available | 直接執行 |
| 3 | patch_repo | reversible_write | 在第二個服務的 repo 套用同樣的升級，讓三個服務的版本一致。 | allow | budget available | 直接執行 |
| 4 | patch_repo | reversible_write | 在第三個服務的 repo 完成升級，這樣三個 repo 都修好了才進入部署。 | allow | budget available | 直接執行 |
| 5 | deploy_service | privileged_operation | 先部署第一個服務當金絲雀，確認沒有問題再擴大範圍。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 6 | deploy_service | privileged_operation | 第一個服務運作正常後，再部署第二個服務，降低同時出錯的風險。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 7 | deploy_service | privileged_operation | 最後部署第三個服務，三個服務全部上線修補版本。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 8 | send_customer_email | external_communication | 確認三個服務都部署成功後才通知客戶，信寄出去就收不回來，所以放在最後一步。 | allow | budget available | 直接執行 |

統計：直接執行 5 步，進核准佇列 3 步，被預算擋下 0 步

## 4. 改成 patch_repo 上限 10（同一份計畫，不再呼叫模型）

| # | tool | side_effect | why | 決策 | reason | 結果 |
|---|---|---|---|---|---|---|
| 1 | read_ticket | read | 先讀工單，確認是哪個過期套件、要升到哪個版本，以及影響哪三個服務。 | allow | budget available | 直接執行 |
| 2 | patch_repo | reversible_write | 在第一個服務的 repo 升級過期套件，改動可以用版本控制還原。 | allow | budget available | 直接執行 |
| 3 | patch_repo | reversible_write | 在第二個服務的 repo 套用同樣的升級，讓三個服務的版本一致。 | allow | budget available | 直接執行 |
| 4 | patch_repo | reversible_write | 在第三個服務的 repo 完成升級，這樣三個 repo 都修好了才進入部署。 | allow | budget available | 直接執行 |
| 5 | deploy_service | privileged_operation | 先部署第一個服務當金絲雀，確認沒有問題再擴大範圍。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 6 | deploy_service | privileged_operation | 第一個服務運作正常後，再部署第二個服務，降低同時出錯的風險。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 7 | deploy_service | privileged_operation | 最後部署第三個服務，三個服務全部上線修補版本。 | escalate | privileged_operation requires approval | 進核准佇列 |
| 8 | send_customer_email | external_communication | 確認三個服務都部署成功後才通知客戶，信寄出去就收不回來，所以放在最後一步。 | allow | budget available | 直接執行 |

統計：直接執行 5 步，進核准佇列 3 步，被預算擋下 0 步

上限 3 → 10 有變化的步驟：無

<!-- analysis -->
## 5. 分析

**統計（上限 3）：直接執行 5 步、等人核准 3 步、被預算擋下 0 步。**

**patch_repo 上限改成 10，結果哪裡變了？什麼都沒變。** 兩張表逐步比對，8 步的結果完全一樣。原因是這次子代理很規矩，三個服務剛好各 patch 一次，正好用完上限 3，不會撞到第 4 次。改成 10 只是多了 7 次「備用額度」，這次沒用到。

這不代表上限沒意義，第 1 節的純程式實驗已經示範：第 4 次 patch 一定會被 `tool budget exhausted for patch_repo` 擋下。上限 3 的價值在子代理**不規矩**時才看得出來，例如 patch 失敗後一直重試，或被注入的指令叫它「順便修其他 repo」：上限 3 會在第 4 次擋下，上限 10 會讓它多改 7 次才停。所以上限要貼近任務真正需要的量（三個服務 → 3），不是越大越方便。

**其他觀察（照實記錄）：**

1. **寄信直接執行，沒有經過人。** 這份預算的 `approvals_required` 只有 privileged_operation 和 irreversible_write，external_communication 只設了「最多 1 次」的風險上限。所以第 8 步的通知信是 `budget available` 直接放行。預算只管「次數」，不管「該不該問人」；在 ch02 的實驗室設定裡，對外溝通是要進核准佇列的，這裡的設定少了這一層。
2. **三次部署都進核准佇列，而且不會扣預算。** `check()` 回 escalate 時我們不 spend，所以核准前不佔額度；正式系統要在人核准、真的執行之後才扣。
3. **順序的風險：** 子代理把寄信放在三次部署之後，理由是「確認都部署成功才通知」。但在預算這一層，部署還卡在核准佇列，寄信卻已經被放行，可能出現「還沒部署就先通知客戶修好了」的狀況。預算是逐步獨立判斷的，不知道前一步還在等人；要防這件事，得靠意圖合約或流程控制來確認前置步驟都完成。
4. 子代理的回覆每次可能不同；原始計畫存於 `ch02/agent_plan.json`，可用 `--replay` 重跑判斷、不再呼叫模型（重跑時本分析段會保留）。
