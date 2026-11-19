# K142《Harness Engineering：長時程多代理 AI 系統的安全設計模式》範例程式碼＋提示詞演練

Ken Huang 等著，英文原名 *Harness Engineering: Design Patterns for Securing Long-Horizon Multi-Agent AI Systems*。
全書主張：正式上線的多代理 AI 系統，決定安全的是包在模型外面的控制平面（harness）——身分、意圖、上下文、記憶、可觀測性、執行期操控、擴展性、資料治理。
本 repo 以作者公開的實驗室 [HarnessLab](https://github.com/kenhuangus/HarnessLab)（Apache-2.0，純 Python、零相依、不需 API 金鑰）為基礎，把每章改寫成練習：由「教練」視窗送提示詞給「練習」視窗裡的 Claude，讓它實際執行該章實驗、讀決策與產物、寫小實驗戳邊界，再對照書中觀念解說。
每章另有一個練習用 `claude -p`（Claude Code 無頭模式，走 Max 訂閱、不設任何 API 金鑰）扮演 harness 裡的真實子代理，由 HarnessLab 的控制判斷是否放行。

> 練習內容為依各章重點原創撰寫，不含書籍原文。

## 結構

```
prompts/chNN.md          各章練習：章節重點、作者的例子、提示詞練習、觀察重點、教練解說要點
code/HarnessLab/         書附實驗室原檔（作者公開，Apache-2.0）
teaching/drill.json      章節清單
teaching/DRILL-PROMPT.md 教練開場提示詞
teaching/HANDOFF.md      演練進度表
practice/                練習視窗的工作目錄；產出存在 practice/chNN/，實驗室副本在 practice/HarnessLab/
practice/llm_agent.py    真實子代理轉接腳本（claude -p，timeout 180 秒，移除 API 金鑰與繼承的 Claude Code 變數）
```

| 章 | 主題 | 練習數 |
| --- | --- | --- |
| ch00 | 導論與環境準備：把 HarnessLab 跑起來 | 2 |
| ch01 | Harness 作為長時程多代理系統的控制平面 | 2 |
| ch02 | 自主性：分級控制與人類監督 | 2 |
| ch03 | 身分：每個代理的身分與委派鏈 | 2 |
| ch04 | 意圖：合約、偏移偵測與依目的授權 | 2 |
| ch05 | 上下文：信任分級、來源與防投毒 | 2 |
| ch06 | 記憶：狀態防火牆、帳本與遺忘 | 2 |
| ch07 | 可觀測性、評估與爬坡證據 | 2 |
| ch08 | 執行期操控：介入、政策注入與安全回滾 | 2 |
| ch09 | 擴展性：代理群協調不連鎖崩潰 | 2 |
| ch10 | 資料治理：分級感知工具、外流管控與合規 | 2 |
| ch11 | 全書總複習：Capstone 修補代理群與上線前檢查 | 2 |

共 12 章、24 個練習。

## 怎麼跑實驗室

```bash
cd practice/HarnessLab
PYTHONUTF8=1 python -m harnesslab.cli list
PYTHONUTF8=1 python -m harnesslab.cli run all
PYTHONUTF8=1 python -m harnesslab.cli verify
```

2026-11-19 在 HP1（Python 3.14）實測：run all 十章全部 PASS（ch01 0.98，其餘 1.0），verify 全數通過，capstone 與單元測試皆通過。

## 怎麼演練

HP1 螢幕 3（橫式 1920×1080）左右兩半：左半「K142 教練」、右半「K142 練習-全書」。
由主 Claude 開好兩個視窗並送出 `teaching/DRILL-PROMPT.md`，教練一章一章跑完，每章 commit＋push。
