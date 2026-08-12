import os, re, json, glob, csv, math
import statistics as stats

HERE = os.path.dirname(__file__)
BASE = os.path.abspath(os.path.join(HERE, ".."))
RES_DIR = os.path.join(BASE, "results")
OUT_CSV = os.path.join(RES_DIR, "summary_boolean.csv")

PRICE = {
    "qwen/qwen-2.5-72b-instruct": {"prompt_per_tok": 0.07/1e6, "completion_per_tok": 0.26/1e6}
}

def safe_get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def to_float(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().replace("$", "")
    try:
        return float(s)
    except Exception:
        return None

def parse_file(fp):
    with open(fp, "r") as f:
        obj = json.load(f)

    statsd = obj.get("statistics", obj)

    # 指标（多种可能字段名做兼容）
    vr = safe_get(statsd, ["valid_rate", "mean"]) or safe_get(statsd, ["valid", "mean"])
    nr = (safe_get(statsd, ["novelty_rate", "mean"]) or
          safe_get(statsd, ["uniqueness", "mean"]) or
          safe_get(statsd, ["novelty", "mean"]))
    rr = safe_get(statsd, ["recovery_rate", "mean"]) or safe_get(statsd, ["recovery", "mean"])

    # Tokens
    p_tok = (safe_get(obj, ["token_usage", "prompt_tokens"]) or
             safe_get(obj, ["Token Usage", "Prompt tokens"]))
    c_tok = (safe_get(obj, ["token_usage", "completion_tokens"]) or
             safe_get(obj, ["Token Usage", "Completion tokens"]))
    t_tok = (safe_get(obj, ["token_usage", "total_tokens"]) or
             safe_get(obj, ["Token Usage", "Total tokens"]))
    if t_tok is None and (p_tok is not None or c_tok is not None):
        t_tok = (p_tok or 0) + (c_tok or 0)

    # Cost（优先读精确值；缺失时用 tokens 粗略估算）
    cost = (to_float(safe_get(obj, ["cost", "total"])) or
            to_float(safe_get(obj, ["Cost", "Total cost"])))
    if cost is None:
        model = (safe_get(obj, ["llm", "model"]) or
                 safe_get(obj, ["LLM", "Model"]) or
                 "qwen/qwen-2.5-72b-instruct")
        pricing = PRICE.get(model) or PRICE["qwen/qwen-2.5-72b-instruct"]
        if p_tok is not None and c_tok is not None:
            cost = p_tok * pricing["prompt_per_tok"] + c_tok * pricing["completion_per_tok"]
        elif t_tok is not None:
            # 没有拆分 prompt/completion 就不做估算（避免误导）
            cost = None

    return dict(vr=vr, nr=nr, rr=rr,
                prompt_tokens=p_tok, completion_tokens=c_tok, total_tokens=t_tok,
                cost=cost)

def mean_std(xs):
    vals = [x for x in xs if x is not None]
    if not vals:
        return (None, None)
    if len(vals) == 1:
        return (float(vals[0]), 0.0)
    return (float(stats.mean(vals)), float(stats.stdev(vals)))

def main():
    files = glob.glob(os.path.join(RES_DIR, "boolean_2var_qwen-2_*.json"))
    if not files:
        print("No result JSON files found in:", RES_DIR); return

    groups = {}  # tag -> [file paths]
    for fp in files:
        name = os.path.basename(fp)
        tag = re.sub(r"\.json$", "", name)
        # 去掉 _seed12345
        base_tag = re.sub(r"_seed\d+$", "", tag)
        # 提取 'boolean_2var_qwen-2_<TAG>'
        m = re.match(r"boolean_2var_qwen-2_(.+)", base_tag)
        if not m:
            continue
        key = m.group(1)
        groups.setdefault(key, []).append(fp)

    rows_out = []
    print("\n==== Aggregated Summary ====\n")
    print(f"{'Tag':28s}  {'N':>2s}  {'Valid(mean±std)':>20s}  {'Novelty':>12s}  {'Recovery':>12s}  {'AvgTokens':>10s}  {'AvgCost($)':>10s}")

    for key, fps in sorted(groups.items()):
        recs = [parse_file(fp) for fp in fps]
        vr_m, vr_s = mean_std([r["vr"] for r in recs])
        nr_m, nr_s = mean_std([r["nr"] for r in recs])
        rr_m, rr_s = mean_std([r["rr"] for r in recs])
        tok_m, _   = mean_std([r["total_tokens"] for r in recs])
        cost_m, _  = mean_std([r["cost"] for r in recs])

        def fmt(ms):
            return "NA" if ms[0] is None else f"{ms[0]:.3f}±{ms[1]:.3f}"
        def fnum(x):
            return "" if x is None else (f"{int(x)}" if isinstance(x, float) and x.is_integer() else f"{x:.3f}" if isinstance(x, float) else str(x))

        print(f"{key:28s}  {len(fps):2d}  {fmt((vr_m,vr_s)):>20s}  {fmt((nr_m,nr_s)):>12s}  {fmt((rr_m,rr_s)):>12s}  {fnum(tok_m):>10s}  {fnum(cost_m):>10s}")

        rows_out.append({
            "tag": key, "n_files": len(fps),
            "valid_mean": vr_m, "valid_std": vr_s,
            "novelty_mean": nr_m, "novelty_std": nr_s,
            "recovery_mean": rr_m, "recovery_std": rr_s,
            "avg_tokens": tok_m, "avg_cost": cost_m
        })

    os.makedirs(RES_DIR, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader(); w.writerows(rows_out)
    print("\nSaved CSV:", OUT_CSV)

if __name__ == "__main__":
    main()