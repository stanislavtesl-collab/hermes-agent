from pathlib import Path
from datetime import datetime
import re
import json

ROOT = Path(r"C:\Users\Administrator\AppData\Local\hermes")
CFG = ROOT / "config.yaml"
MEM_DIR = ROOT / "memories"
ARCH = MEM_DIR / "archive"
LOG = ROOT / "logs" / "memory_housekeeper.log"
DELIM = "\n§\n"


def log(msg: str):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def read_limits():
    mem_limit = 12000
    user_limit = 8000
    if CFG.exists():
        text = CFG.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"(?ms)^memory:\s*\n(.*?)(?:\n\S|\Z)", text)
        if m:
            block = m.group(1)
            ml = re.search(r"(?m)^\s*memory_char_limit:\s*(\d+)", block)
            ul = re.search(r"(?m)^\s*user_char_limit:\s*(\d+)", block)
            if ml:
                mem_limit = int(ml.group(1))
            if ul:
                user_limit = int(ul.group(1))
    return mem_limit, user_limit


def split_entries(raw: str):
    if not raw.strip():
        return []
    if DELIM in raw:
        parts = [p.strip() for p in raw.split(DELIM)]
    else:
        parts = [p.strip() for p in raw.split("§")]
    return [p for p in parts if p]


def normalize(s: str):
    return re.sub(r"\s+", " ", s).strip()


def compact(entries, limit, target_ratio=0.65):
    # Dedup (keep newest occurrence by iterating reverse then restore order)
    seen = set()
    dedup_rev = []
    for e in reversed(entries):
        k = normalize(e).lower()
        if k in seen:
            continue
        seen.add(k)
        dedup_rev.append(e)
    dedup = list(reversed(dedup_rev))

    # Priority scoring: trading-critical / infra-critical first
    kw_hi = ["critical", "крит", "трейд", "gold", "mt5", "daemon", "сервер", "fxpro", "telegram", "owner"]
    scored = []
    for i, e in enumerate(dedup):
        t = normalize(e)
        low = t.lower()
        score = 0
        for k in kw_hi:
            if k in low:
                score += 3
        score += min(len(t), 400) / 400.0
        scored.append((score, i, t))

    # Start from higher score then by recency
    ranked = [x[2] for x in sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)]

    # Build compacted set under target chars
    target = int(limit * target_ratio)
    out = []
    cur = 0
    for e in ranked:
        one = e[:320]  # cap noisy long entries
        cand = (DELIM.join(out + [one])) if out else one
        if len(cand) <= target:
            out.append(one)
            cur = len(cand)

    # Ensure not empty
    if not out and ranked:
        out = [ranked[0][:320]]
        cur = len(out[0])

    # Return in chronological-ish order (original order where possible)
    order = {normalize(e): idx for idx, e in enumerate(dedup)}
    out_sorted = sorted(out, key=lambda x: order.get(normalize(x), 10**9))
    return out_sorted, cur


def process_file(name, limit):
    p = MEM_DIR / name
    if not p.exists():
        return
    raw = p.read_text(encoding="utf-8", errors="ignore")
    entries = split_entries(raw)
    current = len(DELIM.join(entries)) if entries else 0
    usage = (current / limit) if limit else 0.0
    log(f"{name}: usage={current}/{limit} ({usage:.1%}), entries={len(entries)}")

    if usage < 0.85:
        return

    ARCH.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (ARCH / f"{name}.{ts}.raw.txt").write_text(raw, encoding="utf-8")

    compacted, new_cur = compact(entries, limit, target_ratio=0.65)
    new_raw = DELIM.join(compacted)
    p.write_text(new_raw, encoding="utf-8")

    meta = {
        "file": name,
        "timestamp": ts,
        "before_chars": current,
        "after_chars": new_cur,
        "limit": limit,
        "before_entries": len(entries),
        "after_entries": len(compacted),
    }
    (ARCH / f"{name}.{ts}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"{name}: compacted {current}->{new_cur} chars, {len(entries)}->{len(compacted)} entries")


def main():
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    mem_limit, user_limit = read_limits()
    process_file("MEMORY.md", mem_limit)
    process_file("USER.md", user_limit)


if __name__ == "__main__":
    main()
