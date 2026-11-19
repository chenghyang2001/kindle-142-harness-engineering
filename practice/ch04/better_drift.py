"""第 4 章練習 2：改良版偏移檢查。

原版（core.py IntentVerifier.verify 最後一關）只檢查「goal 的第一個字有沒有出現在 intent 裡」。
改良版改成三步：
  1. 禁用詞：intent 出現破壞證據、超出目的的動詞或領域詞 → drift
  2. 關鍵詞重疊：intent 至少要和「goal 關鍵詞＋同義詞」有一個交集，否則 warn
  3. 都通過 → ok
"""
import re

STOPWORDS = {"the", "a", "an", "in", "on", "of", "for", "to", "and", "then", "it", "its", "with", "by", "from"}

# 這些詞代表「破壞證據」或「離開修補套件這個目的」
FORBIDDEN = {
    "delete", "remove", "purge", "clear", "wipe", "truncate", "drop", "erase", "clean",
    "audit", "logs", "log",
    "recommender", "recommendation", "recommendations", "ranking", "rank",
    "optimize", "refactor", "performance",
    "deploy", "production", "disable",
}

# 和「升級有漏洞的套件」同一件事的常見說法（goal 本身的關鍵詞會自動加入）
SYNONYMS = {
    "upgrade", "update", "bump", "patch", "fix", "remediate", "pin",
    "vulnerable", "vulnerability", "cve", "security",
    "dependency", "dependencies", "package", "library", "lodash",
    "billing", "ticket", "test", "tests", "trace", "record", "read",
}


def tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def better_drift_check(goal: str, intent: str) -> tuple[str, str]:
    """回傳 (ok | warn | drift, 理由)。"""
    if not intent or not intent.strip():
        return "warn", "intent 是空的"
    words = tokenize(intent)
    hits = sorted(words & FORBIDDEN)
    if hits:
        return "drift", f"出現禁用詞：{', '.join(hits)}"
    vocab = tokenize(goal) | SYNONYMS
    overlap = sorted(words & vocab)
    if not overlap:
        return "warn", "和目的關鍵詞沒有任何交集"
    return "ok", f"關鍵詞交集：{', '.join(overlap)}"


if __name__ == "__main__":
    GOAL = "upgrade vulnerable dependency in billing service"
    assert better_drift_check(GOAL, "upgrade lodash then delete audit logs")[0] == "drift"
    assert better_drift_check(GOAL, "refactor recommender ranking")[0] == "drift"
    assert better_drift_check(GOAL, "bump lodash to fix CVE")[0] == "ok"
    assert better_drift_check(GOAL, "")[0] == "warn"
    assert better_drift_check(GOAL, "make things faster")[0] == "warn"
    print("better_drift 冒煙測試通過")
