"""第 8 章練習 2：真實退款代理跑到一半，主管注入臨時政策（RuntimeController 模擬，不會真的撥款）。

用法（在 practice 目錄）：
  PYTHONUTF8=1 PYTHONPATH="HarnessLab;." python ch08/refund_steering.py           # 呼叫 claude -p 一次
  PYTHONUTF8=1 PYTHONPATH="HarnessLab;." python ch08/refund_steering.py --replay  # 重用 ch08/agent_refunds.json
輸出寫到 ch08/refund_steering.md；ANALYSIS_MARKER 之後的手寫分析會保留。
"""
import json
import sys
import time
from pathlib import Path

from harnesslab.core import RuntimeController

HERE = Path(__file__).resolve().parent
RAW_PATH = HERE / "agent_refunds.json"
MD_PATH = HERE / "refund_steering.md"
ANALYSIS_MARKER = "<!-- analysis -->"
RUN_ID = "run-ch08-refunds"
OVERLAY = {"block_categories": ["gift_card"], "expires_after_step": 5}

PROMPT = """你是客服退款代理。請處理 6 筆虛構的退款申請（訂單號、金額、類別都由你自己編，金額用新台幣整數）。
其中至少 2 筆的 category 必須是 "gift_card"，其他類別例如 electronics、apparel、books、grocery。
每筆的 action 都填 "refund"。
輸出格式：{"refunds":[{"order":"...","amount":0,"category":"...","action":"refund"}]}"""


def get_refunds(replay: bool) -> tuple[dict | None, str | None]:
    if replay:
        return json.loads(RAW_PATH.read_text(encoding="utf-8")), None
    from llm_agent import ask_json
    try:
        raw = ask_json(PROMPT)
    except (RuntimeError, ValueError) as e:
        return None, f"{type(e).__name__}: {e}"
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return raw, None


def overlay_active(rt: RuntimeController, run_id: str, step: int) -> bool:
    """仿 chapters/ch08/scenario.py 的 _overlay_active：只用步數判斷；沒有 overlay 或沒設到期步數都視為不生效。"""
    item = rt.policy_overlays.get(run_id)
    if item is None:
        return False
    return step <= int(item["overlay"].get("expires_after_step", -1))


def process(rt: RuntimeController, state: dict, refund: dict, step_label: str, step: int, ledger: list) -> None:
    """處理一筆退款：暫停中拒絕 → 冪等跳過 → overlay 阻擋 → 執行（只記在 ledger／state，不撥款）。"""
    order = str(refund.get("order"))
    row = {"step": step_label, "order": order, "amount": refund.get("amount"), "category": refund.get("category")}
    if RUN_ID in rt.paused:
        row.update(result="拒絕", reason="run 暫停中，不處理任何退款")
    elif order in state["refunded"]:
        row.update(result="跳過", reason="冪等保護：此訂單已退款，不重複撥款")
    elif overlay_active(rt, RUN_ID, step) and refund.get("category") in OVERLAY["block_categories"]:
        row.update(result="阻擋", reason=f"臨時政策生效中（step {step} ≤ {OVERLAY['expires_after_step']}），{refund.get('category')} 退款暫停")
    else:
        state["refunded"].append(order)
        state["paid_total"] += int(refund.get("amount") or 0)
        active = overlay_active(rt, RUN_ID, step)
        row.update(result="執行", reason="臨時政策生效中但類別不在封鎖清單" if active else
                   ("臨時政策已到期，恢復正常" if rt.policy_overlays.get(RUN_ID) else "尚無臨時政策"))
    state["step"] = step
    ledger.append(row)


def run_scenario(refunds: list) -> tuple[list, dict, dict]:
    rt, ledger = RuntimeController(), []
    state = {"step": 0, "refunded": [], "paid_total": 0}
    ck0 = rt.checkpoint(RUN_ID, json.loads(json.dumps(state)), "refund-policy-v1", "evidence_before_first_refund")
    for i in (1, 2):
        process(rt, state, refunds[i - 1], str(i), i, ledger)
    pause = rt.pause(RUN_ID, "fraud alert")
    inject = rt.inject_policy(RUN_ID, dict(OVERLAY), ttl_seconds=60)
    ck2 = rt.checkpoint(RUN_ID, json.loads(json.dumps(state)), "refund-policy-v1", "evidence_after_step_2")
    if len(refunds) >= 3:
        process(rt, state, refunds[2], "3（暫停中嘗試）", 3, ledger)  # 證明暫停期間不會被處理
    state = rt.resume_from(ck2.checkpoint_id)
    process(rt, state, refunds[1], "2（恢復後故意重送）", 2, ledger)  # 冪等測試
    for i in range(3, len(refunds) + 1):
        process(rt, state, refunds[i - 1], str(i), i, ledger)
    paid_orders = [r["order"] for r in ledger if r["result"] == "執行"]
    info = {"ck0": ck0.checkpoint_id, "ck2": ck2.checkpoint_id, "pause": pause.reason, "inject": inject.reason,
            "paid_orders": paid_orders, "duplicate_payouts": len(paid_orders) - len(set(paid_orders)),
            "paid_total": state["paid_total"]}
    return ledger, state, info


def ttl_probe() -> dict:
    rt = RuntimeController()
    rt.inject_policy("ttl-probe", dict(OVERLAY), ttl_seconds=0)
    expires_at, now = rt.policy_overlays["ttl-probe"]["expires_at"], time.time()
    return {"expires_at": round(expires_at, 6), "now": round(now, 6), "expired_by_clock": now >= expires_at,
            "still_stored": "ttl-probe" in rt.policy_overlays,
            "overlay_active_step_1": overlay_active(rt, "ttl-probe", 1)}


def render(raw, error, ledger, info, ttl) -> str:
    lines = ["# 第 8 章 練習 2：退款代理 × 暫停 × 臨時政策 × 冪等", "",
             f"run_id `{RUN_ID}`；臨時政策 `{json.dumps(OVERLAY)}`（ttl_seconds=60）。所有退款只記在 list，不會真的撥款。", "",
             "## 子代理原始退款清單（claude -p 呼叫 1 次）", ""]
    lines += [f"呼叫失敗：`{error}`", ""] if error else ["```json", json.dumps(raw, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## 流程", "", f"- 第 1 筆前 checkpoint：`{info.get('ck0')}`",
              f"- 第 2 筆後：`{info.get('pause')}` → `{info.get('inject')}` → checkpoint `{info.get('ck2')}` → resume_from 該檢查點", "",
              "## 逐筆結果", "", "| 步數 | 訂單 | 金額 | 類別 | 結果 | 原因 |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['step']} | {r['order']} | {r['amount']} | {r['category']} | {r['result']} | {r['reason']} |" for r in ledger]
    lines += ["", "## 重複撥款測試", "",
              f"- 實際執行的訂單：`{info.get('paid_orders')}`",
              f"- 重複撥款筆數：**{info.get('duplicate_payouts')}**；累計撥款 NT${info.get('paid_total')}", "",
              "## ttl 觀察（另外 inject_policy(..., ttl_seconds=0)）", "",
              f"- expires_at = `{ttl['expires_at']}`，time.time() = `{ttl['now']}`，以時鐘看已過期？**{ttl['expired_by_clock']}**",
              f"- 過期後 overlay 仍存在 `policy_overlays` 裡？**{ttl['still_stored']}**",
              f"- 用步數判斷的 overlay_active(step=1)：**{ttl['overlay_active_step_1']}**", ""]
    return "\n".join(lines)


def main() -> None:
    raw, error = get_refunds("--replay" in sys.argv)
    refunds = (raw or {}).get("refunds", [])
    if raw is not None and (not isinstance(refunds, list) or len(refunds) < 3):
        error, refunds = "子代理 JSON 的 refunds 不是陣列或少於 3 筆", []
    ledger, info = [], {}
    if refunds:
        ledger, _, info = run_scenario(refunds)
    ttl = ttl_probe()
    kept = ""
    if MD_PATH.exists():
        old = MD_PATH.read_text(encoding="utf-8")
        if ANALYSIS_MARKER in old:
            kept = old[old.index(ANALYSIS_MARKER):]
    MD_PATH.write_text(render(raw, error, ledger, info, ttl) + ("\n" + kept if kept else ""), encoding="utf-8")
    for r in ledger:
        print(f"step {r['step']:<12} {r['order']:<14} {str(r['category']):<12} {r['result']}：{r['reason']}")
    print(f"duplicate_payouts={info.get('duplicate_payouts')} ttl={ttl}")
    if error:
        print(f"錯誤：{error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
