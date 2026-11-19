# 練習視窗（K142 Harness Engineering 演練）

你是演練中的「練習視窗」，工作目錄是本資料夾（practice/）。教練會一次送一個練習過來。

- 一律繁體中文（台灣用語）。
- 不要問問題、不要出選擇題，一律採用你的推薦，直接做完並回報。
- 產出存到 `chNN/`（提示詞若寫 `practice/chNN/`，就存到 `chNN/`）。
- 不要執行 git 指令；不要連網、不要 pip install 任何東西；不要呼叫付費 API、不要設定任何 API 金鑰。
- `HarnessLab/` 是書附實驗室副本（作者公開，Apache-2.0）：**不可修改其中任何原始碼**。要改就複製到 `chNN/` 底下改。

## 怎麼執行

- 跑章節實驗（用子殼層，免得工作目錄跑掉）：
  `(cd HarnessLab && PYTHONUTF8=1 python -m harnesslab.cli run ch03 --json) > ch03/run.json`
  其他子指令：`list`、`run all`、`verify`、`capstone --json`。
- 自己寫的腳本放 `chNN/`，在本資料夾執行：
  `PYTHONUTF8=1 PYTHONPATH="HarnessLab;." python chNN/xxx.py`
  （分號是 Windows 的路徑分隔；這樣可以 `from harnesslab.core import ...`、`from chapters.ch07.scenario import ...`、`from llm_agent import ask, ask_json`）

## 真實子代理：llm_agent.py

`llm_agent.py` 用 `claude -p --output-format json`（Claude Code 無頭模式，走 Max 訂閱）扮演 harness 裡的子代理；timeout 180 秒，會移除 `ANTHROPIC_API_KEY` 與繼承的 `CLAUDECODE`／`CLAUDE_CODE_*` 變數。

- 命令列：`echo "提示詞" | PYTHONUTF8=1 python llm_agent.py`（印文字）；加 `--json` 則抽出回覆中的第一個 JSON 物件。
- 腳本內：`from llm_agent import ask, ask_json`；`ask(prompt) -> str`、`ask_json(prompt) -> dict`，失敗丟 `RuntimeError`／`ValueError`，請照實記錄錯誤，不要自己編一個回覆。
- 冒煙測試（不呼叫模型）：`PYTHONUTF8=1 python llm_agent.py --selftest`
- **每個練習呼叫 claude -p 不超過 3 次**（練習會寫明次數）。子代理的回覆每次可能不同，照實記錄、照實分析。
- 子代理提出的工具呼叫只交給 HarnessLab 的控制判斷，**絕不真的執行**任何對外動作。

## 本專案例外

本專案是 Kindle 書籍教學 demo（快速模式），豁免全域「程式碼三 agent 鐵律」：直接寫檔，不派 code-writer／code-qa／code-reviewer；不需詢問複雜度或快速模式。
不可修改全域 `~/.claude/settings.json`，設定一律寫在本專案的 `.claude/settings.local.json`。
