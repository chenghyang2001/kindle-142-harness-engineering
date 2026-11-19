# 第 0 章：HarnessLab 全書總覽表

資料來源：`ch00/run-all.json`（`harnesslab.cli run all --json`），由 `ch00/summarize.py` 統計（輸出存於 `ch00/summary.txt`）。決策數只算每章頂層 `decisions` 清單，不含 artifacts 內的巢狀紀錄。10 章全部 PASS。

| 章 | 英文章名 | 繁中章名 | score | allow | deny | escalate | warn | rewrite |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ch01 | Harness as the Control Plane for Long-Horizon Multi-Agent Systems | Harness：長時程多代理系統的控制平面 | 0.98 | 6 | 4 | 1 | 2 | 0 |
| ch02 | Autonomy: Graduated Control and Human Oversight | 自主性：分級管控與人工監督 | 1.0 | 15 | 4 | 8 | 0 | 0 |
| ch03 | Identity: Per-Agent Identity and Delegation Chains | 身分：每個代理一個身分與委派鏈 | 1.0 | 16 | 9 | 1 | 1 | 0 |
| ch04 | Intent: Contracts, Drift Detection, and Authorization by Purpose | 意圖：合約、偏移偵測與依目的授權 | 1.0 | 11 | 3 | 1 | 1 | 1 |
| ch05 | Context: Trust Tiers, Provenance, and Context-Poisoning Containment | 上下文：信任分級、來源追溯與上下文污染圍堵 | 1.0 | 5 | 6 | 0 | 2 | 1 |
| ch06 | Memory: State Firewall, Ledger, and Forgetting | 記憶：狀態防火牆、帳本與遺忘 | 1.0 | 8 | 3 | 0 | 0 | 0 |
| ch07 | Observability, Evals, and Hill-Climbing Evidence | 可觀測性、評測與爬山式改進證據 | 1.0 | 5 | 1 | 1 | 0 | 1 |
| ch08 | Runtime Steering: Intervention, Policy Injection, and Safe Rollback | 執行期導引：介入、政策注入與安全回滾 | 1.0 | 9 | 2 | 0 | 3 | 0 |
| ch09 | Scalability: Fleet Coordination Without Cascading Failure | 擴展性：不連鎖崩潰的代理群協調 | 1.0 | 29 | 2 | 1 | 8 | 0 |
| ch10 | Data Governance: Classification-Aware Tools, Egress, and Compliance | 資料治理：依分級的工具、外送管控與合規 | 1.0 | 23 | 6 | 1 | 0 | 0 |

合計 201 個決策：allow 127、deny 40、escalate 14、warn 17、rewrite 3。

**觀察：**

1. 非 allow 比例最高的是 **ch05（0.643，14 個決策裡 9 個非 allow）**：上下文章的實驗刻意餵入外部、過期、帶注入指令的內容，大部分都該被攔下或隔離，只有新鮮且可信的上下文能放行。
2. ch01 次高（0.538），因為它是「把不安全專案對映到安全 harness」的總覽，展示的多半是被擋或升級的危險路徑。
3. 唯一分數不是 1.0 的是 **ch01（0.98）**。看 `chapters/ch01/scenario.py:187`，分數 = (決策分數 + 爬山治理的 final_score) ÷ 2；爬山路徑的最後一步只到 0.96，所以 (1.0 + 0.96) ÷ 2 = 0.98。
4. 我猜作者故意不讓它到 1.0：書裡想表達的是「改進迴圈永遠可以繼續」，不是「已經完美」。所以 0.98 不是 bug，是設計出來的訊號。

## 子代理連線測試

指令：`echo "用一句繁體中文說明什麼是 AI 代理的控制平面" | PYTHONUTF8=1 python llm_agent.py`（呼叫 1 次，回覆原文照錄）

> AI 代理的控制平面，指的是一層放在模型外面、由程式而不是模型決定的管控機制，負責在代理執行任何動作之前，檢查權限、預算和政策，再決定放行、攔截還是要求人工核准。
