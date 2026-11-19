"""讀 ch00/run-all.json，統計每章 score 與五種決策數量（只算每章頂層 decisions 清單）。"""
import json
import sys
from collections import Counter
from pathlib import Path

KINDS = ["allow", "deny", "escalate", "warn", "rewrite"]
DEFAULT_PATH = Path(__file__).resolve().parent / "run-all.json"


def load_results(path: Path) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到 {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"錯誤：{path} 不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(1)


def summarize(results: list) -> list:
    rows = []
    for ch in results:
        counts = Counter(d.get("decision") for d in ch.get("decisions", []))
        total = sum(counts.values())
        non_allow = total - counts.get("allow", 0)
        other = total - sum(counts.get(k, 0) for k in KINDS)
        rows.append({
            "chapter": ch.get("chapter"),
            "title": ch.get("title"),
            "score": ch.get("score"),
            "passed": ch.get("passed"),
            **{k: counts.get(k, 0) for k in KINDS},
            "other": other,
            "total": total,
            "non_allow_ratio": round(non_allow / total, 3) if total else 0.0,
        })
    return rows


def print_table(rows: list) -> None:
    header = ["chapter", "score", *KINDS, "other", "total", "non_allow_ratio"]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in rows:
        print("| " + " | ".join(str(r[h]) for h in header) + " |")
    totals = {k: sum(r[k] for r in rows) for k in [*KINDS, "other", "total"]}
    print("\n合計：" + "，".join(f"{k}={v}" for k, v in totals.items()))
    top = max(rows, key=lambda r: r["non_allow_ratio"])
    print(f"非 allow 比例最高：{top['chapter']}（{top['non_allow_ratio']}）")
    not_full = [f"{r['chapter']}={r['score']}" for r in rows if r["score"] != 1.0]
    print("分數不是 1.0：" + ("、".join(not_full) if not_full else "無"))


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    rows = summarize(load_results(path))
    if not rows:
        print("錯誤：JSON 內沒有任何章節", file=sys.stderr)
        sys.exit(1)
    print_table(rows)


if __name__ == "__main__":
    main()
