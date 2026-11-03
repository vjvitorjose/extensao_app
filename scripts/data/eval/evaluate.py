# -*- coding: utf-8 -*-
"""Calcula as métricas da avaliação a partir dos runs JSONL.

Uso:
    python scripts/data/eval/evaluate.py
    python scripts/data/eval/evaluate.py runs/deepseek_flash_few_shot.jsonl
    python scripts/data/eval/evaluate.py runs/*.jsonl --out-dir reports

Para cada run, compara com `ground_truth.jsonl` e reporta:
  - macro-F1 multiclasse (classes com suporte >= 1);
  - precisão, recall, F1 e suporte por classe;
  - matriz de confusão;
  - acurácia/precisão/recall/F1 binários de `relevante`;
  - tratamento de área (itens fora da área alertados = falso positivo);
  - JSON inválido / fora do schema;
  - acerto de endereço por comparação textual normalizada;
  - latência e custo por item.

Também gera comparação pareada: os modelos são reavaliados apenas nos itens
que todos responderam, para que a diferença de cobertura não distorça a
comparação.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from _eval_common import (
    BASE,
    GROUND_TRUTH,
    TAXONOMY,
    address_match,
    normalize_type,
    read_jsonl,
    safe_model_name,
)

try:  # Python 3.7+
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

RUNS_DIR = BASE / "runs"
REPORTS_DIR = BASE / "reports"
NENHUM = "nenhum"
BOOTSTRAP_SEED = 20261103


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------


def load_ground_truth(path: Path = GROUND_TRUTH) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in read_jsonl(path)}


def latest_records(path: Path) -> dict[str, dict[str, Any]]:
    """Mantém o último registro de cada ID (o run pode ter retries)."""
    latest: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(path):
        item_id = record.get("id")
        if item_id:
            latest[item_id] = record
    return latest


def discover_runs(paths: Iterable[str]) -> list[Path]:
    explicit = [Path(p) for p in paths]
    if explicit:
        files: list[Path] = []
        for path in explicit:
            if path.is_dir():
                files.extend(
                    sorted(
                        candidate
                        for candidate in path.glob("*.jsonl")
                        if not candidate.name.startswith("_")
                    )
                )
            else:
                files.append(path)
        return [path for path in files if path.exists()]

    if not RUNS_DIR.exists():
        return []
    return sorted(
        path
        for path in RUNS_DIR.glob("*.jsonl")
        if not path.name.startswith("_")
    )


# ---------------------------------------------------------------------------
# Métricas básicas
# ---------------------------------------------------------------------------


def safe_div(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    if precision is None or recall is None:
        # Classe com suporte mas sem nenhuma previsão: F1 = 0 (não é
        # indefinido para o macro-F1). Classe sem suporte e sem previsão: None.
        f1 = 0.0 if (recall is not None or precision is not None) else None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "precision": None if precision is None else round(precision, 4),
        "recall": None if recall is None else round(recall, 4),
        "f1": None if f1 is None else round(f1, 4),
    }


def classification_metrics(
    pairs: list[tuple[str, str]],
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """pairs = [(gold, pred)] já normalizados."""
    labels = labels or TAXONOMY
    support = Counter(gold for gold, _ in pairs)
    predicted = Counter(pred for _, pred in pairs)
    matrix = {gold: Counter() for gold in labels}
    for gold, pred in pairs:
        matrix.setdefault(gold, Counter())[pred] += 1

    per_class: dict[str, dict[str, Any]] = {}
    for label in labels:
        tp = matrix.get(label, Counter()).get(label, 0)
        fp = predicted.get(label, 0) - tp
        fn = support.get(label, 0) - tp
        row = prf(tp, fp, fn)
        row.update(
            {
                "support": support.get(label, 0),
                "predicted": predicted.get(label, 0),
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
        per_class[label] = row

    with_support = [label for label in labels if support.get(label, 0) > 0]
    f1_values = [
        per_class[label]["f1"] for label in with_support if per_class[label]["f1"] is not None
    ]
    accuracy = safe_div(sum(1 for gold, pred in pairs if gold == pred), len(pairs))
    matrix_json = {
        gold: {pred: matrix.get(gold, Counter()).get(pred, 0) for pred in labels}
        for gold in labels
        if support.get(gold, 0) > 0
    }
    return {
        "n": len(pairs),
        "accuracy": None if accuracy is None else round(accuracy, 4),
        "macro_f1": round(sum(f1_values) / len(f1_values), 4) if f1_values else None,
        "macro_f1_classes": len(f1_values),
        "classes_sem_suporte": [label for label in labels if support.get(label, 0) == 0],
        "per_class": per_class,
        "confusion_matrix": matrix_json,
        "support": dict(support),
        "predicted": dict(predicted),
    }


def binary_metrics(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    tp = sum(1 for gold, pred in pairs if gold and pred)
    fp = sum(1 for gold, pred in pairs if not gold and pred)
    fn = sum(1 for gold, pred in pairs if gold and not pred)
    tn = sum(1 for gold, pred in pairs if not gold and not pred)
    out = prf(tp, fp, fn)
    out.update(
        {
            "n": len(pairs),
            "accuracy": round((tp + tn) / len(pairs), 4) if pairs else None,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "positives": tp + fn,
            "predicted_positives": tp + fp,
        }
    )
    return out


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * pct
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean_s": round(statistics.fmean(values), 3),
        "median_s": round(statistics.median(values), 3),
        "p90_s": round(percentile(values, 0.90) or 0.0, 3),
        "p95_s": round(percentile(values, 0.95) or 0.0, 3),
        "max_s": round(max(values), 3),
    }


# ---------------------------------------------------------------------------
# Avaliação de um run
# ---------------------------------------------------------------------------


def prediction_type(record: dict[str, Any]) -> tuple[str | None, bool]:
    parsed = record.get("parsed")
    if not isinstance(parsed, dict):
        return None, False
    raw = parsed.get("tipo_perigo")
    if raw is None:
        return None, False
    normalized, alias = normalize_type(raw)
    return normalized, alias


def record_prediction(record: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Extrai os campos comparáveis de um registro, com fallback derivado."""
    parsed = record.get("parsed") if isinstance(record.get("parsed"), dict) else {}
    pred_type, alias = prediction_type(record)

    pred_fora = bool(parsed.get("fora_da_area"))
    if "relevante" in parsed:
        pred_relevante = bool(parsed.get("relevante"))
        relevante_derivado = False
    else:
        pred_relevante = pred_type is not None and pred_type != NENHUM and not pred_fora
        relevante_derivado = True

    # Consistência: relevante=true com nenhum/fora é contraditório e conta
    # como erro na métrica binária e na de área.
    gt_type = gold.get("tipo_perigo")
    gt_fora = bool(gold.get("fora_da_area"))
    gt_relevante = bool(gold.get("relevante"))

    address = address_match(gold.get("endereco"), parsed.get("endereco"))

    return {
        "id": record["id"],
        "gold_type": gt_type,
        "pred_type": pred_type,
        "pred_type_raw": parsed.get("tipo_raw"),
        "type_alias": alias,
        "type_ok": pred_type == gt_type,
        "gold_relevante": gt_relevante,
        "pred_relevante": pred_relevante,
        "relevante_derivado_pelo_avaliador": relevante_derivado,
        "relevante_ok": pred_relevante == gt_relevante,
        "gold_fora": gt_fora,
        "pred_fora": pred_fora,
        "fora_ok": pred_fora == gt_fora,
        "alerta_fora_da_area": bool(pred_relevante and gt_fora),
        "schema_valido": bool(parsed.get("schema_valido")),
        "campos_ausentes": parsed.get("campos_ausentes") or [],
        "endereco": address,
        "confianca": parsed.get("confianca"),
        "error": record.get("error"),
        "parse_error": record.get("parse_error"),
        "latency_s": record.get("latency_s"),
        "cost_usd": record.get("cost_usd"),
        "usage": record.get("usage") or {},
        "raw_response": record.get("raw_response"),
    }


def evaluate_run(
    path: Path,
    ground_truth: dict[str, dict[str, Any]],
    *,
    expected_ids: list[str] | None = None,
) -> dict[str, Any]:
    records = latest_records(path)
    meta_path = path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    evaluated: list[dict[str, Any]] = []
    missing: list[str] = []
    failed: list[str] = []
    invalid_json: list[str] = []
    invalid_schema: list[str] = []

    for item_id in sorted(records):
        gold = ground_truth.get(item_id)
        if gold is None:
            continue
        record = records[item_id]
        if record.get("error"):
            failed.append(item_id)
            continue
        if record.get("parse_error") or not isinstance(record.get("parsed"), dict):
            invalid_json.append(item_id)
            continue
        pred = record_prediction(record, gold)
        if not pred["schema_valido"]:
            invalid_schema.append(item_id)
        evaluated.append(pred)

    if expected_ids is None:
        expected_ids = sorted(ground_truth)
    seen = set(records)
    missing = [item_id for item_id in expected_ids if item_id not in seen]

    type_pairs = [
        (pred["gold_type"], pred["pred_type"])
        for pred in evaluated
        if pred["pred_type"] is not None
    ]
    # Para a matriz, resposta sem tipo é "nenhum"? Não: contamos como erro
    # fora da taxonomia, mas mantemos o par com um rótulo sentinela.
    type_pairs_all = [
        (pred["gold_type"], pred["pred_type"] if pred["pred_type"] is not None else "<invalido>")
        for pred in evaluated
    ]
    labels = TAXONOMY + ["<invalido>"]

    binary_pairs = [(pred["gold_relevante"], pred["pred_relevante"]) for pred in evaluated]
    area_pairs = [(pred["gold_fora"], pred["pred_fora"]) for pred in evaluated]

    gt_address = [pred for pred in evaluated if pred["endereco"]["gt"] is not None]
    both_address = [
        pred
        for pred in gt_address
        if pred["endereco"]["pred"] is not None
    ]
    gt_null_pred_address = [
        pred
        for pred in evaluated
        if pred["endereco"]["gt"] is None and pred["endereco"]["pred"] is not None
    ]

    latencies = [
        float(pred["latency_s"])
        for pred in evaluated
        if isinstance(pred["latency_s"], (int, float))
    ]
    costs = [
        float(pred["cost_usd"])
        for pred in evaluated
        if isinstance(pred["cost_usd"], (int, float))
    ]
    usages = [pred["usage"] for pred in evaluated if pred["usage"]]

    total = len(evaluated)
    address_rate = lambda rows, key: round(  # noqa: E731
        sum(1 for pred in rows if pred["endereco"][key]) / len(rows), 4
    ) if rows else None

    return {
        "run": path.name,
        "key": path.stem,
        "model": meta.get("model") or path.stem,
        "mode": meta.get("mode"),
        "prompt_version": meta.get("prompt_version"),
        "started_at": meta.get("started_at"),
        "finished_at": meta.get("finished_at"),
        "coverage": {
            "expected": len(expected_ids),
            "records_in_file": len(records),
            "evaluated": total,
            "missing": len(missing),
            "failed": len(failed),
            "invalid_json": len(invalid_json),
            "invalid_schema": len(invalid_schema),
            "missing_ids": missing,
            "failed_ids": failed,
            "invalid_json_ids": invalid_json,
            "invalid_schema_ids": invalid_schema,
        },
        "multiclass": classification_metrics(type_pairs_all, labels=labels),
        "multiclass_valid_only": classification_metrics(type_pairs),
        "binary_relevante": binary_metrics(binary_pairs),
        "area": {
            **binary_metrics(area_pairs),
            "gt_fora": sum(1 for pred in evaluated if pred["gold_fora"]),
            "pred_fora": sum(1 for pred in evaluated if pred["pred_fora"]),
            "alertados_fora_da_area": sum(
                1 for pred in evaluated if pred["alerta_fora_da_area"]
            ),
            "alertados_fora_da_area_ids": [
                pred["id"] for pred in evaluated if pred["alerta_fora_da_area"]
            ],
        },
        "address": {
            "gt_com_endereco": len(gt_address),
            "pred_com_endereco": sum(
                1 for pred in evaluated if pred["endereco"]["pred"] is not None
            ),
            "gt_com_endereco_pred_com_endereco": len(both_address),
            "exato": address_rate(gt_address, "exact"),
            "contem": address_rate(gt_address, "contains"),
            "fuzzy": address_rate(gt_address, "fuzzy"),
            "exato_ambos": address_rate(both_address, "exact"),
            "contem_ambos": address_rate(both_address, "contains"),
            "fuzzy_ambos": address_rate(both_address, "fuzzy"),
            "gt_sem_endereco_pred_com_endereco": len(gt_null_pred_address),
            "gt_sem_endereco_pred_com_endereco_ids": [
                pred["id"] for pred in gt_null_pred_address
            ],
        },
        "type_errors": [
            {
                "id": pred["id"],
                "gold": pred["gold_type"],
                "pred": pred["pred_type"],
                "raw": pred["pred_type_raw"],
                "relevante_gold": pred["gold_relevante"],
                "relevante_pred": pred["pred_relevante"],
                "fora_gold": pred["gold_fora"],
                "fora_pred": pred["pred_fora"],
                "confianca": pred["confianca"],
            }
            for pred in evaluated
            if not pred["type_ok"]
        ],
        "binary_errors": [
            {
                "id": pred["id"],
                "gold": pred["gold_relevante"],
                "pred": pred["pred_relevante"],
                "gold_type": pred["gold_type"],
                "pred_type": pred["pred_type"],
            }
            for pred in evaluated
            if not pred["relevante_ok"]
        ],
        "latency": latency_metrics(latencies),
        "cost": {
            "total_usd": round(sum(costs), 8) if costs else 0.0,
            "mean_usd": round(sum(costs) / len(costs), 8) if costs else 0.0,
            "items_with_usage": len(usages),
            "reported": any(value for usage in usages for value in usage.values()),
        },
        "predictions": evaluated,
    }


# ---------------------------------------------------------------------------
# Bootstrap e comparação pareada
# ---------------------------------------------------------------------------


def _bootstrap_stat(
    rows: list[dict[str, Any]],
    stat: str,
    *,
    iterations: int,
    rng: random.Random,
) -> dict[str, float] | None:
    if not rows or iterations <= 0:
        return None
    values: list[float] = []
    n = len(rows)
    for _ in range(iterations):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        if stat == "binary_accuracy":
            values.append(sum(1 for row in sample if row["relevante_ok"]) / n)
        elif stat == "type_accuracy":
            values.append(sum(1 for row in sample if row["type_ok"]) / n)
        elif stat == "macro_f1":
            pairs = [
                (row["gold_type"], row["pred_type"] if row["pred_type"] else "<invalido>")
                for row in sample
            ]
            labels = TAXONOMY + ["<invalido>"]
            metrics = classification_metrics(pairs, labels=labels)
            if metrics["macro_f1"] is None:
                continue
            values.append(metrics["macro_f1"])
    if not values:
        return None
    values.sort()

    def pick(pct: float) -> float:
        index = min(len(values) - 1, max(0, round((len(values) - 1) * pct)))
        return round(values[index], 4)

    return {"low": pick(0.025), "high": pick(0.975), "iterations": len(values)}


def bootstrap_metrics(
    evaluation: dict[str, Any], *, iterations: int
) -> dict[str, Any]:
    rng = random.Random(BOOTSTRAP_SEED)
    rows = evaluation["predictions"]
    return {
        "iterations_requested": iterations,
        "binary_accuracy": _bootstrap_stat(
            rows, "binary_accuracy", iterations=iterations, rng=rng
        ),
        "type_accuracy": _bootstrap_stat(
            rows, "type_accuracy", iterations=iterations, rng=rng
        ),
        "macro_f1": _bootstrap_stat(rows, "macro_f1", iterations=iterations, rng=rng),
    }


def evaluate_subset(
    evaluation: dict[str, Any], ids: set[str]
) -> dict[str, Any]:
    rows = [pred for pred in evaluation["predictions"] if pred["id"] in ids]
    type_pairs = [
        (row["gold_type"], row["pred_type"] if row["pred_type"] else "<invalido>")
        for row in rows
    ]
    return {
        "n": len(rows),
        "multiclass": classification_metrics(type_pairs, labels=TAXONOMY + ["<invalido>"]),
        "binary_relevante": binary_metrics(
            [(row["gold_relevante"], row["pred_relevante"]) for row in rows]
        ),
        "type_accuracy": round(
            sum(1 for row in rows if row["type_ok"]) / len(rows), 4
        )
        if rows
        else None,
    }


def paired_comparison(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    if len(evaluations) < 2:
        return {"models": [], "common_ids": 0}
    common = {pred["id"] for pred in evaluations[0]["predictions"]}
    for evaluation in evaluations[1:]:
        common &= {pred["id"] for pred in evaluation["predictions"]}
    common = set(sorted(common))
    return {
        "models": [evaluation["model"] for evaluation in evaluations],
        "keys": [evaluation["key"] for evaluation in evaluations],
        "common_ids": len(common),
        "ids": sorted(common),
        "per_model": {
            evaluation["key"]: evaluate_subset(evaluation, common)
            for evaluation in evaluations
        },
    }


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_report(
    evaluations: list[dict[str, Any]],
    paired: dict[str, Any],
    *,
    bootstrap: dict[str, Any],
    generated_at: str,
) -> str:
    lines: list[str] = []
    lines.append("# Relatório de avaliação dos LLMs")
    lines.append("")
    lines.append(f"Gerado em {generated_at}.")
    lines.append("")
    lines.append(
        "Gabarito: 120 posts anotados manualmente (`ground_truth.jsonl`). "
        "Métricas multiclasse sobre `tipo_perigo`; métricas binárias sobre "
        "`relevante`. `iluminacao_ruim` tem suporte 0 no gabarito e fica fora "
        "do macro-F1."
    )
    lines.append("")

    lines.append("## Visão geral")
    lines.append("")
    lines.append(
        "| Modelo | Modo | Avaliados | Cobertura | Acurácia tipo | Macro-F1 | "
        "Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta | JSON inválido | Schema inválido |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for evaluation in evaluations:
        multi = evaluation["multiclass"]
        binary = evaluation["binary_relevante"]
        coverage = evaluation["coverage"]
        lines.append(
            "| {model} | {mode} | {n} | {cov} | {acc} | {f1} | {bacc} | {bprec} | {brec} | {bf1} | {inv} | {schema} |".format(
                model=evaluation["model"],
                mode=evaluation.get("mode") or "—",
                n=evaluation["coverage"]["evaluated"],
                cov=f"{evaluation['coverage']['evaluated']}/{evaluation['coverage']['expected']}",
                acc=fmt(multi["accuracy"]),
                f1=fmt(multi["macro_f1"]),
                bacc=fmt(binary["accuracy"]),
                bprec=fmt(binary["precision"]),
                brec=fmt(binary["recall"]),
                bf1=fmt(binary["f1"]),
                inv=coverage["invalid_json"],
                schema=coverage["invalid_schema"],
            )
        )
    lines.append("")

    lines.append("## Custo e latência")
    lines.append("")
    lines.append("| Modelo | Latência média | Mediana | p95 | Máx. | Custo total | Custo/item |")
    lines.append("|---|---|---|---|---|---|---|")
    for evaluation in evaluations:
        latency = evaluation["latency"]
        cost = evaluation["cost"]
        lines.append(
            "| {model} | {mean} s | {median} s | {p95} s | {max} s | US$ {total} | US$ {per_item} |".format(
                model=evaluation["model"],
                mean=fmt(latency.get("mean_s")),
                median=fmt(latency.get("median_s")),
                p95=fmt(latency.get("p95_s")),
                max=fmt(latency.get("max_s")),
                total=fmt(cost["total_usd"], 6),
                per_item=fmt(cost["mean_usd"], 6),
            )
        )
    lines.append("")
    if any(not evaluation["cost"]["reported"] for evaluation in evaluations):
        lines.append(
            "> Custo 0,000000 indica que o provedor não reportou tokens/custo "
            "(a API local de sessões do OpenCode devolve apenas o texto). "
            "Não interprete como gratuito."
        )
        lines.append("")

    lines.append("## Métricas por classe")
    lines.append("")
    for evaluation in evaluations:
        multi = evaluation["multiclass"]
        lines.append(f"### {evaluation['model']}")
        lines.append("")
        lines.append(
            f"Macro-F1 = {fmt(multi['macro_f1'])} em "
            f"{multi['macro_f1_classes']} classes com suporte ≥ 1. "
            f"`iluminacao_ruim` tem suporte 0 e não entra no macro-F1."
        )
        lines.append("")
        lines.append("| Classe | Suporte | Previsto | Precisão | Recall | F1 | TP | FP | FN |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for label in TAXONOMY:
            row = multi["per_class"][label]
            lines.append(
                f"| `{label}` | {row['support']} | {row['predicted']} | "
                f"{fmt(row['precision'])} | {fmt(row['recall'])} | {fmt(row['f1'])} | "
                f"{row['tp']} | {row['fp']} | {row['fn']} |"
            )
        lines.append("")

    lines.append("## Matriz de confusão")
    lines.append("")
    for evaluation in evaluations:
        multi = evaluation["multiclass"]
        matrix = multi["confusion_matrix"]
        possible = TAXONOMY + ["<invalido>"]
        rows = [label for label in possible if label in matrix]
        columns = [
            label
            for label in possible
            if any(row.get(label, 0) for row in matrix.values())
        ]
        lines.append(f"### {evaluation['model']}")
        lines.append("")
        lines.append("Linhas = gabarito; colunas = previsto. Só linhas/colunas com ocorrência.")
        lines.append("")
        lines.append("| gabarito \\ previsto | " + " | ".join(f"`{c}`" for c in columns) + " |")
        lines.append("|" + "---|" * (len(columns) + 1))
        for gold in rows:
            cells = [str(matrix.get(gold, {}).get(column, 0)) for column in columns]
            lines.append(f"| `{gold}` | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Área de cobertura")
    lines.append("")
    lines.append(
        "O gabarito tem 6 itens fora da área (1 com tipo de evento). "
        "Alertar um item fora da área é falso positivo operacional."
    )
    lines.append("")
    lines.append("| Modelo | Fora no gabarito | Fora previsto | Acerto fora | Alertados fora | IDs |")
    lines.append("|---|---|---|---|---|---|")
    for evaluation in evaluations:
        area = evaluation["area"]
        ids = ", ".join(area["alertados_fora_da_area_ids"]) or "—"
        lines.append(
            f"| {evaluation['model']} | {area['gt_fora']} | {area['pred_fora']} | "
            f"{fmt(area['accuracy'])} | {area['alertados_fora_da_area']} | {ids} |"
        )
    lines.append("")

    lines.append("## Endereço")
    lines.append("")
    lines.append(
        "Comparação textual normalizada (sem geocodificação), restrita aos itens "
        "com endereço no gabarito. `exato`/`contém`/`fuzzy` contam falta de "
        "endereço previsto como erro."
    )
    lines.append("")
    lines.append(
        "| Modelo | Itens com endereço no gabarito | Exato | Contém | Fuzzy | Fuzzy (ambos) | Endereço previsto sem GT |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for evaluation in evaluations:
        address = evaluation["address"]
        lines.append(
            f"| {evaluation['model']} | {address['gt_com_endereco']} | "
            f"{fmt(address['exato'])} | {fmt(address['contem'])} | {fmt(address['fuzzy'])} | "
            f"{fmt(address['fuzzy_ambos'])} | {address['gt_sem_endereco_pred_com_endereco']} |"
        )
    lines.append("")

    if bootstrap.get("iterations_requested"):
        lines.append("## Intervalo de confiança (bootstrap)")
        lines.append("")
        lines.append(
            f"{bootstrap['iterations_requested']} reamostragens por modelo, "
            "IC de 95%. Útil para não superinterpretar diferenças pequenas em 120 itens."
        )
        lines.append("")
        lines.append("| Modelo | Acurácia tipo (IC 95%) | Macro-F1 (IC 95%) | Acurácia alerta (IC 95%) |")
        lines.append("|---|---|---|---|")
        for evaluation in evaluations:
            item = bootstrap["per_model"][evaluation["key"]]

            def interval(name: str) -> str:
                value = item.get(name)
                if not value:
                    return "—"
                return f"{value['low']:.3f}–{value['high']:.3f}"

            lines.append(
                f"| {evaluation['model']} | {interval('type_accuracy')} | "
                f"{interval('macro_f1')} | {interval('binary_accuracy')} |"
            )
        lines.append("")

    if paired.get("common_ids"):
        lines.append("## Comparação pareada")
        lines.append("")
        lines.append(
            f"Modelos reavaliados nos {paired['common_ids']} itens respondidos por todos. "
            "É a comparação mais justa quando a cobertura difere."
        )
        lines.append("")
        lines.append("| Modelo | N | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for evaluation in evaluations:
            model = evaluation["model"]
            subset = paired["per_model"][evaluation["key"]]
            lines.append(
                f"| {model} | {subset['n']} | {fmt(subset['type_accuracy'])} | "
                f"{fmt(subset['multiclass']['macro_f1'])} | "
                f"{fmt(subset['binary_relevante']['accuracy'])} | "
                f"{fmt(subset['binary_relevante']['precision'])} | "
                f"{fmt(subset['binary_relevante']['recall'])} | "
                f"{fmt(subset['binary_relevante']['f1'])} |"
            )
        lines.append("")

    lines.append("## Erros por modelo")
    lines.append("")
    for evaluation in evaluations:
        lines.append(f"### {evaluation['model']}")
        lines.append("")
        lines.append(
            f"- Erros de tipo: {len(evaluation['type_errors'])}; "
            f"erros de alerta: {len(evaluation['binary_errors'])}; "
            f"falhas: {evaluation['coverage']['failed']}; "
            f"JSON inválido: {evaluation['coverage']['invalid_json']}; "
            f"schema inválido: {evaluation['coverage']['invalid_schema']}."
        )
        if evaluation["coverage"]["missing"]:
            lines.append(
                f"- Sem registro: {evaluation['coverage']['missing']} itens "
                f"({', '.join(evaluation['coverage']['missing_ids'][:20])}"
                + ("…" if evaluation["coverage"]["missing"] > 20 else "")
                + ")."
            )
        if evaluation["type_errors"]:
            lines.append("")
            lines.append("| ID | Gabarito | Previsto | Confiança | Alerta gabarito | Alerta previsto |")
            lines.append("|---|---|---|---|---|---|")
            for error in evaluation["type_errors"]:
                lines.append(
                    f"| {error['id']} | `{error['gold']}` | `{fmt(error['pred'])}` | "
                    f"{fmt(error['confianca'])} | {error['relevante_gold']} | "
                    f"{error['relevante_pred']} |"
                )
        lines.append("")

    lines.append("## Arquivos avaliados")
    lines.append("")
    for evaluation in evaluations:
        lines.append(f"- `{evaluation['run']}` — modelo `{evaluation['model']}`, modo `{evaluation.get('mode')}`.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "runs",
        nargs="*",
        help="arquivos JSONL ou diretórios; padrão: runs/*.jsonl (ignora _*)",
    )
    parser.add_argument("--out-dir", default=str(REPORTS_DIR), help="diretório dos relatórios")
    parser.add_argument("--name", default="comparison", help="nome base dos arquivos de saída")
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=1000,
        help="reamostragens bootstrap para IC 95%% (0 desliga)",
    )
    parser.add_argument("--no-json", action="store_true", help="não gravar o JSON detalhado")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ground_truth = load_ground_truth()
    paths = discover_runs(args.runs)
    if not paths:
        print(
            "Nenhum run encontrado. Rode run_eval.py primeiro ou passe um arquivo.",
            file=sys.stderr,
        )
        return 2

    evaluations = [evaluate_run(path, ground_truth) for path in paths]
    evaluations = [evaluation for evaluation in evaluations if evaluation["coverage"]["evaluated"]]
    if not evaluations:
        print("Nenhum run tinha itens avaliáveis.", file=sys.stderr)
        return 2

    paired = paired_comparison(evaluations)
    bootstrap = {"iterations_requested": args.bootstrap, "per_model": {}}
    if args.bootstrap > 0:
        for evaluation in evaluations:
            bootstrap["per_model"][evaluation["key"]] = bootstrap_metrics(
                evaluation, iterations=args.bootstrap
            )

    generated_at = datetime.now(timezone.utc).isoformat()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = markdown_report(
        evaluations,
        paired,
        bootstrap=bootstrap,
        generated_at=generated_at,
    )
    markdown_path = out_dir / f"{args.name}.md"
    markdown_path.write_text(report, encoding="utf-8")

    summary = {
        "generated_at": generated_at,
        "ground_truth": str(GROUND_TRUTH),
        "ground_truth_items": len(ground_truth),
        "models": [],
        "paired": paired,
        "bootstrap": bootstrap,
    }
    for evaluation in evaluations:
        summary["models"].append(evaluation)
    json_path = out_dir / f"{args.name}.json"
    if not args.no_json:
        json_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(report)
    print(f"relatório: {markdown_path}")
    if not args.no_json:
        print(f"json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
