# Boolean task readme

------

## 1) 概览

- 任务：**Boolean Genetic Interactions（逻辑函数发现）**
- 数据：`datasets/boolean_2var.json`（2 变量、AND/OR、最大深度 2）
- 度量：**Valid / Novelty(=Uniqueness) / Recovery**
- 模型：`qwen/qwen-2.5-72b-instruct`（经 OpenRouter 调用）
- 默认样本数：`n-samples=30`

------

## 2) 环境

```bash
conda create -n hypospace-bool python=3.10 -y
conda activate hypospace-bool
python -m pip install --upgrade pip
pip install numpy matplotlib PyYAML httpx requests tqdm
```

- 可选：`networkx`、`scipy`、`sympy`（若自行扩展解析或后处理）。
- 关于 `requirements.txt` 的用途与可选性，参考 pip 官方文档。

------

## 3) 配置（模板 → 本地）

在 `config/` 下提供三份**模板**（只示例文件名；以仓库实际为准）：

- `config_qwen72b_baseline.template.yaml`（T=0.70, multiplier=1.0）
- `config_qwen72b_t0.85_m2.0.template.yaml`（T=0.85, multiplier=2.0）
- `config_qwen72b_t0.95_m2.0.template.yaml`（T=0.95, multiplier=2.0）

复制为本地文件并替换占位符 `__OPENROUTER_API_KEY__`：

```bash
cp config/config_qwen72b_baseline.template.yaml    config/config_qwen72b_baseline.local.yaml
cp config/config_qwen72b_t0.85_m2.0.template.yaml  config/config_qwen72b_t0.85_m2.0.local.yaml
cp config/config_qwen72b_t0.95_m2.0.template.yaml  config/config_qwen72b_t0.95_m2.0.local.yaml
```

baseline模板片段示例：

```yaml
llm:
  type: openrouter
  models:
    openrouter: "qwen/qwen-2.5-72b-instruct"
  api_keys:
    openrouter: "__OPENROUTER_API_KEY__"  # 仅在 .local.yaml 中替换为真实 key
  temperature: 0.70  # 其他模板为 0.85 / 0.95

benchmark:
  checkpoint: "checkpoints"
  verbose: true
  output_pattern: "results/{dataset_name}_{model}_<tag>.json"
```

> 说明：`output_pattern` 不含 `{seed}`。运行后用 `mv` 把种子写进文件名，避免覆盖。

------

## 4) 单次运行（示例）

在 `_HypoSpace/boolean` 目录下：

```bash
# Baseline（T=0.7, m=1.0）
python boolean_benchmark.py \
  --dataset datasets/boolean_2var.json \
  --config config/config_qwen72b_baseline.local.yaml \
  --n-samples 30 --query-multiplier 1.0 --seed 33550336

# T=0.85, m=2.0
python boolean_benchmark.py \
  --dataset datasets/boolean_2var.json \
  --config config/config_qwen72b_t0.85_m2.0.local.yaml \
  --n-samples 30 --query-multiplier 2.0 --seed 33550336

# T=0.95, m=2.0
python boolean_benchmark.py \
  --dataset datasets/boolean_2var.json \
  --config config/config_qwen72b_t0.95_m2.0.local.yaml \
  --n-samples 30 --query-multiplier 2.0 --seed 33550336
```

------

## 5) 多种子运行（不覆盖）

```bash
# Baseline
for s in 33550336 2024 42; do
  python boolean_benchmark.py \
    --dataset datasets/boolean_2var.json \
    --config config/config_qwen72b_baseline.local.yaml \
    --n-samples 30 --query-multiplier 1.0 --seed $s
  mv -f results/boolean_2var_qwen-2_baseline.json \
        results/boolean_2var_qwen-2_baseline_seed${s}.json
done

# T=0.85, m=2.0
for s in 33550336 2024 42; do
  python boolean_benchmark.py \
    --dataset datasets/boolean_2var.json \
    --config config/config_qwen72b_t0.85_m2.0.local.yaml \
    --n-samples 30 --query-multiplier 2.0 --seed $s
  mv -f results/boolean_2var_qwen-2_t0.85_m2.0.json \
        results/boolean_2var_qwen-2_t0.85_m2.0_seed${s}.json
done

# T=0.95, m=2.0
for s in 33550336 2024 42; do
  python boolean_benchmark.py \
    --dataset datasets/boolean_2var.json \
    --config config/config_qwen72b_t0.95_m2.0.local.yaml \
    --n-samples 30 --query-multiplier 2.0 --seed $s
  mv -f results/boolean_2var_qwen-2_t0.95_m2.0.json \
        results/boolean_2var_qwen-2_t0.95_m2.0_seed${s}.json
done
```

------

## 6) 聚合与作图

```bash
python tools/aggregate_boolean.py   # 产出 results/summary_boolean.csv
python tools/plot_boolean_compare.py  # 产出 figs/boolean_compare.png
```

------

## 