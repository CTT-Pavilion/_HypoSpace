import os, re, json, glob, math
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
BASE = os.path.abspath(os.path.join(HERE, ".."))
RES_DIR = os.path.join(BASE, "results")
FIG_DIR = os.path.join(BASE, "figs")
os.makedirs(FIG_DIR, exist_ok=True)

TAGS = [
    ("baseline",   "Baseline (T=0.7, m=1.0)"),
    ("t0.85_m2.0", "T=0.85, m=2.0"),
    ("t0.95_m2.0", "T=0.95, m=2.0"),
]

PRICE = {"prompt_per_tok": 0.07/1e6, "completion_per_tok": 0.26/1e6}

def safe_get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = d[k] if k in d else cur[k]
            d = cur if isinstance(cur, dict) else {}
        else:
            return default
    return cur

def find_files(tag):
    return sorted(glob.glob(os.path.join(RES_DIR, f"boolean_2var_qwen-2_{tag}_seed*.json")))

def read_one(fp):
    with open(fp, "r") as f:
        obj = json.load(f)
    statsd = obj.get("statistics", obj)
    vr = (safe_get(statsd, ["valid_rate","mean"]) or safe_get(statsd, ["valid","mean"]))
    nr = (safe_get(statsd, ["novelty_rate","mean"]) or
          safe_get(statsd, ["uniqueness","mean"]) or
          safe_get(statsd, ["novelty","mean"]))
    rr = (safe_get(statsd, ["recovery_rate","mean"]) or safe_get(statsd, ["recovery","mean"]))

    p_tok = (safe_get(obj, ["token_usage","prompt_tokens"]) or
             safe_get(obj, ["Token Usage","Prompt tokens"]))
    c_tok = (safe_get(obj, ["token_usage","completion_tokens"]) or
             safe_get(obj, ["Token Usage","Completion tokens"]))
    t_tok = (safe_get(obj, ["token_usage","total_tokens"]) or
             safe_get(obj, ["Token Usage","Total tokens"]))
    if t_tok is None and (p_tok is not None or c_tok is not None):
        t_tok = (p_tok or 0) + (c_tok or 0)

    # cost：先尝试精确字段；否则估算；实在不行就 None
    cost = (safe_get(obj, ["cost","total"]) or safe_get(obj, ["Cost","Total cost"]))
    if isinstance(cost, str):
        try: cost = float(cost.strip().replace("$",""))
        except: cost = None
    if cost is None:
        if p_tok is not None and c_tok is not None:
            cost = p_tok*PRICE["prompt_per_tok"] + c_tok*PRICE["completion_per_tok"]

    return {"vr":vr, "nr":nr, "rr":rr, "tokens":t_tok, "cost":cost}

def agg_for(tag):
    files = find_files(tag)
    rows = [read_one(fp) for fp in files]
    def ms(key):
        vals = [r[key] for r in rows if r[key] is not None]
        if not vals: return (np.nan, np.nan)
        return (float(np.mean(vals)), float(np.std(vals)))
    mvr, svr = ms("vr")
    mnr, snr = ms("nr")
    mrr, srr = ms("rr")
    mtok, _   = ms("tokens")
    mcost, _  = ms("cost")
    return dict(vr=(mvr,svr), nr=(mnr,snr), rr=(mrr,srr), tokens=mtok, cost=mcost)

aggs = [agg_for(tag) for tag,_ in TAGS]

plt.figure(figsize=(14,9))
x = np.arange(len(TAGS))
labels = [lbl for _,lbl in TAGS]

ax1 = plt.subplot(2,3,1); vals=[a["vr"][0] for a in aggs]; errs=[a["vr"][1] for a in aggs]
ax1.bar(x, vals, yerr=errs, capsize=4); ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=12)
ax1.set_ylim(0,1.05); ax1.set_title("Valid Rate Comparison"); ax1.set_ylabel("Valid")
for i,v in enumerate(vals):
    if not np.isnan(v): ax1.text(i, v+0.02, f"{v:.3f}", ha="center", fontsize=9)

ax2 = plt.subplot(2,3,2); vals=[a["nr"][0] for a in aggs]; errs=[a["nr"][1] for a in aggs]
ax2.bar(x, vals, yerr=errs, capsize=4); ax2.set_xticks(x); ax2.set_xticklabels(labels, rotation=12)
ax2.set_ylim(0,1.05); ax2.set_title("Novelty (Uniqueness) Rate"); ax2.set_ylabel("Novelty")
for i,v in enumerate(vals):
    if not np.isnan(v): ax2.text(i, v+0.02, f"{v:.3f}", ha="center", fontsize=9)

ax3 = plt.subplot(2,3,3); vals=[a["rr"][0] for a in aggs]; errs=[a["rr"][1] for a in aggs]
ax3.bar(x, vals, yerr=errs, capsize=4); ax3.set_xticks(x); ax3.set_xticklabels(labels, rotation=12)
ax3.set_ylim(0,1.05); ax3.set_title("Recovery Rate"); ax3.set_ylabel("Recovery")
for i,v in enumerate(vals):
    if not np.isnan(v): ax3.text(i, v+0.02, f"{v:.3f}", ha="center", fontsize=9)

ax4 = plt.subplot(2,3,4); vals=[(0 if (a['cost'] is None or np.isnan(a['cost'])) else a['cost']) for a in aggs]
ax4.bar(x, vals); ax4.set_xticks(x); ax4.set_xticklabels(labels, rotation=12)
title4 = "Total Cost (USD)"
if any(a["cost"] is None or np.isnan(a["cost"]) for a in aggs): title4 += "  (some estimated/missing)"
ax4.set_title(title4); ax4.set_ylabel("USD")
for i,v in enumerate(vals): ax4.text(i, v+(max(vals)+1e-9)*0.02, f"${v:.3f}", ha="center", fontsize=9)

ax5 = plt.subplot(2,3,5); vals=[(0 if (a['tokens'] is None or np.isnan(a['tokens'])) else a['tokens']) for a in aggs]
ax5.bar(x, vals); ax5.set_xticks(x); ax5.set_xticklabels(labels, rotation=12)
ax5.set_title("Average Tokens per Run"); ax5.set_ylabel("Tokens")
for i,v in enumerate(vals): ax5.text(i, v+(max(vals)+1e-9)*0.02, f"{int(v)}", ha="center", fontsize=9)

ax6 = plt.subplot(2,3,6)
base = aggs[0]; metrics = ["vr","nr","rr"]; names=["Valid","Novelty","Recovery"]
width=0.25; x2=np.arange(len(aggs)-1)
for i,k in enumerate(metrics):
    b = base[k][0]; arr=[]
    for a in aggs[1:]:
        v = a[k][0]
        imp = ((v - b)/b*100) if (b is not None and not np.isnan(b)) else np.nan
        arr.append(imp)
    ax6.bar(x2 + i*width, arr, width=width, label=names[i])
ax6.set_xticks(x2 + width); ax6.set_xticklabels(labels[1:], rotation=12)
ax6.set_title("Improvement over Baseline (%)"); ax6.set_ylabel("Δ% vs Baseline"); ax6.legend()

plt.tight_layout()
out = os.path.join(FIG_DIR, "boolean_compare.png")
plt.savefig(out, dpi=220)
print("Saved:", out)