# HarnessLab 白話詞彙表：五種決策與四組列舉值

資料來源：`HarnessLab/WORKBOOK.md` 第 2 節「Core Vocabulary & Decision Mechanics」、`HarnessLab/harnesslab/core.py` 開頭的四個 `Enum`，例子取自 `ch00/run-all.json` 每章頂層 `decisions` 的 `reason` 原句（共 201 筆，逐筆搜尋過）。

## 1. Decision（決策）：harness 對每個動作的判決

| 英文值 | 繁中譯名 | 白話解釋 | 真實例子（章號：reason 原句） |
| --- | --- | --- | --- |
| `allow` | 放行 | 檢查過了，沒問題，照做。 | ch02：`read allowed at autonomous` |
| `deny` | 拒絕 | 直接擋下，這個動作不准做。 | ch03：`data class pii is outside contract` |
| `escalate` | 升級（交人工核准） | 機器不自己決定，送去給人看過、按同意才可以做。 | ch01：`privileged_operation requires approval` |
| `warn` | 警告 | 先讓它繼續跑，但亮黃燈、留紀錄，提醒有人要注意。 | ch09：`tenant acme bulkhead is saturated; task acme-followup-004 queued with back-pressure` |
| `rewrite` | 改寫 | 不整個擋掉，而是把危險的部分改掉、刪掉，改成安全版本再放行。 | ch04：`external communication rewritten to internal evidence until purpose-bound authorization exists` |

本次輸出合計：allow 127、deny 40、escalate 14、warn 17、rewrite 3。

## 2. TrustTier（信任等級）：一段內容是從哪裡來的、能信多少

| 英文值 | 繁中譯名 | 白話解釋 | 真實例子（章號：reason 原句） |
| --- | --- | --- | --- |
| `system` | 系統 | 平台自己寫死的規則，最可信。 | ch05：`released 4 fresh trusted context items`（這 4 筆在 artifacts 的 `released_context` 裡，第 1 筆 `ctx_system_policy` 是 system 等級；reason 本身沒寫出 system 這個字） |
| `tenant` | 租戶（客戶公司） | 客戶公司管理員設定的內容，可信，但只在自己公司範圍內有效。 | ch09：`tenant acme capacity quota exceeded` |
| `trusted_tool` | 受信任的工具 | 經過核准的工具回傳的結果，例如公司自己的監控系統。 | ch05：同上那筆 `released 4 fresh trusted context items`（第 4 筆 `ctx_trusted_recent_trace`，來源 `approved_siem`） |
| `user` | 使用者 | 使用者輸入的內容，例如客服工單；可以參考，但不能當成命令照做。 | ch05：同上那筆 `released 4 fresh trusted context items`（第 3 筆 `ctx_user_ticket`，來源 `support_ticket`） |
| `external` | 外部 | 網頁、外部文件這類來路不明的東西，預設不信。 | ch05：`context ctx_external_reference isolated because tier external is not trusted for this profile` |
| `quarantined` | 已隔離 | 被抓到有問題（例如藏了「忽略先前指示」），關起來不給代理看。 | ch05：`context ctx_external_attack quarantined by content firewall` |

## 3. DataClass（資料分級）：這份資料有多敏感

| 英文值 | 繁中譯名 | 白話解釋 | 真實例子（章號：reason 原句） |
| --- | --- | --- | --- |
| `public` | 公開 | 可以給任何人看的資料。 | ch10：`model profile public-saas-analytics accepted public workload` |
| `internal` | 內部 | 只限公司內部看，外流也不至於出大事。 | ch10：`tool call declared internal but persisted label is pii` |
| `confidential` | 機密 | 商業機密，外流會有損失。 | 本次輸出無例子（只出現在 ch08 artifacts 的 `policy_overlay.deny_data` 清單裡，沒有任何一筆 reason 提到它） |
| `pii` | 個人可識別資料 | 能認出是誰的資料，例如姓名、電話、Email，受個資法保護。 | ch08：`blocked PII customer email while temporary policy overlay is active` |
| `secret` | 秘密金鑰 | 密碼、API 金鑰這類東西，一外流就能被拿去冒用，最不能碰。 | ch02：`non-waivable control blocked secret access despite waiver request` |
| `regulated` | 受法規管制 | 法律對存放地點或用途有規定的資料，例如必須留在歐盟。 | ch10：`regulated must stay in eu` |

## 4. ActionRisk（動作風險）：這個動作做下去，影響有多大

| 英文值 | 繁中譯名 | 白話解釋 | 真實例子（章號：reason 原句） |
| --- | --- | --- | --- |
| `read` | 讀取 | 只是看資料，不改任何東西。 | ch02：`read allowed at autonomous` |
| `reversible_write` | 可逆寫入 | 會改東西，但改錯了可以復原（像有上一步）。 | ch02：`reversible_write allowed at autonomous-with-budget` |
| `irreversible_write` | 不可逆寫入 | 改了就回不去，例如刪掉資料。 | ch02：`irreversible_write enters approval-queue` |
| `external_communication` | 對外溝通 | 把東西送到公司外面，例如寄信給客戶、呼叫外部網站。 | ch02：`external_communication requires approval` |
| `privileged_operation` | 特權操作 | 需要很高權限的動作，例如上線部署、改權限設定。 | ch01：`privileged_operation requires approval` |

## ActionRisk 的風險排序

`core.py` 裡 `IntentVerifier.risk_order` 的數字（由低到高）：

| 數字 | 值 | 譯名 |
| --- | --- | --- |
| 0 | `read` | 讀取 |
| 1 | `reversible_write` | 可逆寫入 |
| 2 | `external_communication` | 對外溝通 |
| 3 | `irreversible_write` | 不可逆寫入 |
| 4 | `privileged_operation` | 特權操作 |

這個數字的用途：`verify()` 會比較「這次動作的風險」和「意圖合約允許的最高風險」，超過就回傳 `escalate`（`risk exceeds contract maximum`）。

**為什麼「對外溝通」排在「可逆寫入」之上？** 可逆寫入改的是自己系統裡的東西，出錯了可以復原，影響只在公司內部。對外溝通是把資料送出邊界，一旦送出去，就無法從對方那邊收回：信寄出了就是寄出了，資料外流就是外流了。而且它是 ch05「致命三要素」（私人資料＋工具＋對外管道）裡那個對外管道，是資料外洩真正發生的地方。

**為什麼又排在「不可逆寫入」之下？** 對外溝通的內容通常還能被 harness 處理：可以先改寫（ch04 就把對外信改寫成內部紀錄）、過濾收件人、遮蔽敏感欄位，送出後也還能發更正或道歉。不可逆寫入（例如刪掉資料庫）直接破壞系統自己的狀態，沒有補救的方法。所以順序是：影響範圍（內部 → 外部）決定了它高於可逆寫入，能不能補救（還有補救機會 → 完全無法挽回）決定了它低於不可逆寫入。
