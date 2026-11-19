# CLAUDE.md

K142《Harness Engineering：長時程多代理 AI 系統的安全設計模式》範例程式碼＋提示詞演練 repo（見 README.md）。

- 這是 Kindle 書籍教學 demo（kindle-drill 快速模式），不是正式專案。
- `prompts/chNN.md` 是教材本體；格式：這章在講什麼／作者做過的實驗／例子／演練／教練解說要點。
- 不可貼入書籍原文；引用每章最多一句、15 字內。
- `code/HarnessLab/` 是書附實驗室（作者公開，Apache-2.0）；`practice/HarnessLab/` 是練習用副本；練習產出放 `practice/chNN/`。
- 真實子代理一律走 `practice/llm_agent.py`（`claude -p`，Max 訂閱）；不可設定任何 API 金鑰；每個練習呼叫 ≤3 次。

## 本專案例外

本專案是 Kindle 書籍教學 demo（kindle-drill 快速模式），豁免全域「程式碼三 agent 鐵律」：主 Claude 直接寫檔，不派 code-writer／code-qa／code-reviewer；不需詢問複雜度，也不需詢問是否使用快速模式（已選快速模式）。
所有選擇題一律採用推薦選項、不要停下來問使用者；不可修改全域 `~/.claude/settings.json`，設定一律寫在本專案的 `.claude/settings.local.json`。
