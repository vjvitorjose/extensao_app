# -*- coding: utf-8 -*-
"""Gera o relatório narrativo em Markdown a partir da comparação JSON.

Pré-requisito:
    python scripts/data/eval/evaluate.py \
        scripts/data/eval/runs/deepseek_flash_compact.jsonl \
        scripts/data/eval/runs/gemini_3_1_flash_lite_compact.jsonl \
        scripts/data/eval/runs/ollama_qwen3_8b_compact.jsonl \
        --out-dir scripts/data/eval/reports --name comparison --bootstrap 1000

Uso:
    python scripts/data/eval/make_report.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
REPORTS = BASE / "reports"
COMPARISON = REPORTS / "comparison.json"
GROUND_TRUTH = BASE / "ground_truth.jsonl"
OUTPUT = REPORTS / "RELATORIO_AVALIACAO.md"

DISPLAY = {
    "deepseek/deepseek-flash": "DeepSeek Flash",
    "gemini/gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "ollama/qwen3:8b": "Qwen3 8B (local)",
}
ORDER = [
    "deepseek/deepseek-flash",
    "gemini/gemini-3.1-flash-lite",
    "ollama/qwen3:8b",
]
TYPES = [
    "assedio",
    "iluminacao_ruim",
    "perseguicao",
    "local_suspeito",
    "acidente_transito",
    "assalto",
    "furto",
    "violencia_fisica",
    "presenca_arma",
    "incendio_fumaca",
    "via_bloqueada",
    "emergencia_medica",
    "nenhum",
]
RARE = {"assedio", "perseguicao", "local_suspeito", "via_bloqueada", "iluminacao_ruim"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}".replace(".", ",")
    return str(value)


def pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%".replace(".", ",")


def cell(text: Any) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def title_for(item_id: str, truth: dict[str, dict[str, Any]]) -> str:
    title = (truth.get(item_id) or {}).get("titulo") or ""
    title = " ".join(title.split())
    return title[:88] + ("…" if len(title) > 88 else "")


def make_chart(models: list[dict[str, Any]], display: dict[str, str]) -> str | None:
    """Gera um gráfico de barras agrupadas; ignora falhas de matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    names = [display[model["model"]] for model in models]
    metrics = [
        ("Acurácia do tipo", [model["multiclass"]["accuracy"] or 0 for model in models]),
        ("Macro-F1", [model["multiclass"]["macro_f1"] or 0 for model in models]),
        ("F1 de alerta", [model["binary_relevante"]["f1"] or 0 for model in models]),
    ]
    colors = ["#2563eb", "#16a34a", "#f59e0b"]
    x = range(len(names))
    width = 0.26
    fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=160)
    for index, (label, values) in enumerate(metrics):
        offsets = [position + (index - 1) * width for position in x]
        bars = ax.bar(offsets, values, width, label=label, color=colors[index])
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.015,
                f"{value:.2f}".replace(".", ","),
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Valor (0–1)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=8.5)
    ax.set_title("Comparação dos modelos — 120 posts", fontsize=11, pad=10)
    ax.legend(fontsize=8, ncol=3, loc="lower center", frameon=False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    path = REPORTS / "model_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def main() -> int:
    comparison = json.loads(COMPARISON.read_text(encoding="utf-8"))
    truth = {item["id"]: item for item in load_jsonl(GROUND_TRUTH)}

    models_by_name = {model["model"]: model for model in comparison["models"]}
    models = [models_by_name[name] for name in ORDER if name in models_by_name]
    if not models:
        raise SystemExit("Nenhum modelo esperado encontrado em comparison.json")
    display = {model["model"]: DISPLAY.get(model["model"], model["model"]) for model in models}
    chart_name = make_chart(models, display)

    alertable = [item for item in truth.values() if item["relevante"]]
    outside = [item for item in truth.values() if item.get("fora_da_area")]
    review = [item for item in truth.values() if item.get("revisar")]
    support = Counter(item["tipo_perigo"] for item in truth.values())

    best = max(models, key=lambda m: m["multiclass"]["macro_f1"] or 0)
    local = next((m for m in models if m["model"].startswith("ollama/")), None)
    gemini = next((m for m in models if m["model"].startswith("gemini/")), None)
    gap_local = None
    if local and best is not local:
        gap_local = (best["multiclass"]["macro_f1"] or 0) - (
            local["multiclass"]["macro_f1"] or 0
        )

    lines: list[str] = []
    lines.append("# Avaliação de LLMs para alertas de segurança em São João del-Rei")
    lines.append("")
    lines.append(
        f"**Data:** {datetime.now().strftime('%d/%m/%Y')}  \n"
        f"**Amostra:** {len(truth)} posts anotados manualmente  \n"
        f"**Modelos:** {', '.join(display[m['model']] for m in models)}  \n"
        f"**Prompt:** few-shot com 26 exemplos, temperatura 0 e saída JSON  \n"
        f"**Gabarito:** anotação manual cega, sem usar pré-rótulos do Gemini"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 1. Resumo executivo")
    lines.append("")
    lines.append(
        "Os três modelos foram avaliados nos mesmos 120 posts, com o mesmo prompt "
        "e o mesmo gabarito. A tarefa tem duas decisões: **qual é o tipo do evento** "
        "(`tipo_perigo`) e **se o item deve gerar alerta** (`relevante`)."
    )
    lines.append("")
    lines.append(
        "| Modelo | Cobertura | Acurácia do tipo | Macro-F1 | Acurácia de alerta | Precisão de alerta | Recall de alerta | F1 de alerta |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for model in models:
        multi = model["multiclass"]
        binary = model["binary_relevante"]
        lines.append(
            f"| **{display[model['model']]}** | {model['coverage']['evaluated']}/{model['coverage']['expected']} | "
            f"{fmt(multi['accuracy'])} | {fmt(multi['macro_f1'])} | {fmt(binary['accuracy'])} | "
            f"{fmt(binary['precision'])} | {fmt(binary['recall'])} | {fmt(binary['f1'])} |"
        )
    lines.append("")

    lines.append("**Leitura rápida**")
    lines.append("")
    lines.append(
        f"- **Melhor qualidade geral:** {display[best['model']]}, com macro-F1 "
        f"{fmt(best['multiclass']['macro_f1'])} e acurácia de alerta "
        f"{fmt(best['binary_relevante']['accuracy'])}."
    )
    if local:
        local_bin = local["binary_relevante"]
        relative = (
            f"{gap_local * 100:.2f} pontos percentuais abaixo do melhor".replace(".", ",")
            if gap_local is not None
            else "empatado com o melhor"
        )
        lines.append(
            f"- **Melhor relação custo-benefício:** {display[local['model']]}, rodando "
            f"localmente e sem custo por requisição. Fica {relative} em macro-F1, "
            f"com precisão de alerta {fmt(local_bin['precision'])} e recall "
            f"{fmt(local_bin['recall'])}."
        )
    if gemini:
        gemini_bin = gemini["binary_relevante"]
        lines.append(
            f"- **Comportamento do Gemini:** recall de alerta {fmt(gemini_bin['recall'])} "
            f"e precisão {fmt(gemini_bin['precision'])}; ele alerta quase todos os casos "
            "relevantes, mas erra mais por excesso (falsos positivos)."
        )
    lines.append("")
    lines.append(
        "A recomendação prática está na seção 8. Em resumo: **DeepSeek** se a prioridade "
        "for máxima qualidade; **Qwen3 local** se a prioridade for custo zero, "
        "privacidade e independência de API; **Gemini** como opção intermediária, "
        "com ajuste de limiar para reduzir falsos positivos."
    )
    lines.append("")

    lines.append("## 2. Objetivo e pergunta de avaliação")
    lines.append("")
    lines.append(
        "O objetivo é escolher o modelo que transforma posts da página **SJDD Oficial** "
        "em alertas de segurança confiáveis para São João del-Rei e o Campo das Vertentes. "
        "A pergunta não é apenas “qual acerta mais a classe”, mas também:"
    )
    lines.append("")
    lines.append("1. Ele evita alertar o que não é perigo?")
    lines.append("2. Ele deixa passar eventos que deveriam alertar?")
    lines.append("3. Ele reconhece itens fora da área de cobertura?")
    lines.append("4. O custo e a latência são compatíveis com a operação?")
    lines.append("5. É possível rodar sem enviar dados para terceiros?")
    lines.append("")

    lines.append("## 3. Base de avaliação")
    lines.append("")
    lines.append(
        f"A amostra tem **{len(truth)} posts únicos**, selecionados com seed fixa e "
        "estratificados para incluir classes raras, itens de baixa confiança do "
        "classificador antigo e posts fora do pool pré-classificado com termos de perigo. "
        "A anotação foi feita manualmente e às cegas, sem consultar os pré-rótulos do Gemini."
    )
    lines.append("")
    lines.append(
        f"- **{len(alertable)} itens alertáveis** e {len(truth) - len(alertable)} não alertáveis."
    )
    lines.append(
        f"- **{len(outside)} itens fora da área** de cobertura; alertar esses itens conta como falso positivo."
    )
    lines.append(
        f"- **{len(review)} itens marcados para revisão** por ambiguidade, truncamento ou informação insuficiente."
    )
    lines.append(
        "- A classe `iluminacao_ruim` tem **suporte 0** e não entra no macro-F1; isso é reportado explicitamente."
    )
    lines.append("")
    lines.append(
        "A regra de relevância é: **`relevante = (tipo_perigo != \"nenhum\") e "
        "(fora_da_area == false)`**. A geografia não muda o tipo do evento; um incêndio "
        "em Belo Horizonte continua `incendio_fumaca`, mas recebe `fora_da_area=true` e "
        "`relevante=false`. Por isso a métrica binária é sobre `relevante`, e não sobre "
        "“o modelo citou algum perigo”."
    )
    lines.append("")
    lines.append("| Classe | Itens no gabarito |")
    lines.append("|---|---:|")
    for label in TYPES:
        lines.append(f"| `{label}` | {support.get(label, 0)} |")
    lines.append("")

    lines.append("## 4. Como a avaliação foi feita")
    lines.append("")
    lines.append(
        "Os três modelos receberam **exatamente o mesmo prompt**: 26 exemplos few-shot "
        "(2 por classe), regras de desempate, definição da área de cobertura e o schema "
        "de saída. O conteúdo dos exemplos foi truncado em 600 caracteres para viabilizar "
        "o modelo local; isso vale igualmente para os três, então a comparação é justa."
    )
    lines.append("")
    lines.append(
        "Cada resposta foi gravada em JSONL com texto bruto, JSON parseado, latência e erro. "
        "Respostas com JSON inválido ou fora do schema foram contadas separadamente. "
        "As métricas multiclasse usam `tipo_perigo`; as binárias usam `relevante`, "
        "nunca `tipo_perigo != nenhum`."
    )
    lines.append("")
    lines.append("| Modelo | Como foi executado | Onde os dados passam |")
    lines.append("|---|---|---|")
    if "deepseek/deepseek-flash" in display:
        lines.append(
            "| DeepSeek Flash | API local de sessões do OpenCode, uma sessão por item | Servidor do provedor |"
        )
    if "gemini/gemini-3.1-flash-lite" in display:
        lines.append(
            "| Gemini 3.1 Flash Lite | API Google Generative Language, `temperature=0`, JSON mode | Servidor do Google |"
        )
    if "ollama/qwen3:8b" in display:
        lines.append(
            "| Qwen3 8B | Ollama local, `/api/chat`, `format=json`, 100% GPU | Fica na máquina local |"
        )
    lines.append("")

    lines.append("## 5. Resultados")
    lines.append("")
    lines.append("### 5.1 Métricas principais")
    lines.append("")
    lines.append("| Modelo | Acurácia tipo | Macro-F1 | Acurácia alerta | Precisão alerta | Recall alerta | F1 alerta |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for model in models:
        multi = model["multiclass"]
        binary = model["binary_relevante"]
        lines.append(
            f"| {display[model['model']]} | {fmt(multi['accuracy'])} | {fmt(multi['macro_f1'])} | "
            f"{fmt(binary['accuracy'])} | {fmt(binary['precision'])} | {fmt(binary['recall'])} | {fmt(binary['f1'])} |"
        )
    lines.append("")
    lines.append(
        "O **macro-F1** dá o mesmo peso a todas as classes com suporte, então é a métrica "
        "mais adequada para não deixar as classes raras invisíveis. A **acurácia de alerta** "
        "é a métrica operacional: acertar se o item vira ou não alerta."
    )
    lines.append("")
    lines.append("| Modelo | Alertas emitidos | Acertos (TP) | Falsos positivos | Falsos negativos |")
    lines.append("|---|---:|---:|---:|---:|")
    for model in models:
        binary = model["binary_relevante"]
        lines.append(
            f"| {display[model['model']]} | {binary['predicted_positives']} | "
            f"{binary['tp']} | {binary['fp']} | {binary['fn']} |"
        )
    lines.append("")
    lines.append(
        f"No gabarito há **{len(alertable)} itens alertáveis**. A tabela acima mostra o "
        "trade-off operacional: o Gemini alerta mais e por isso tem recall maior, mas "
        "também mais falsos positivos; o Qwen3 é mais conservador."
    )
    lines.append("")
    if chart_name:
        lines.append(f"![Comparação dos modelos]({chart_name})")
        lines.append("")

    lines.append("### 5.2 Intervalo de confiança (bootstrap 95%)")
    lines.append("")
    lines.append(
        "Com 120 itens, diferenças pequenas podem ser ruído. Os intervalos abaixo mostram "
        "a faixa plausível de cada métrica."
    )
    lines.append("")
    lines.append("| Modelo | Acurácia tipo | Macro-F1 | Acurácia alerta |")
    lines.append("|---|---|---|---|")
    for model in models:
        boot = (comparison.get("bootstrap") or {}).get("per_model", {}).get(model["key"], {})
        def interval(name: str) -> str:
            item = boot.get(name)
            if not item:
                return "—"
            return f"{fmt(item['low'])}–{fmt(item['high'])}"
        lines.append(
            f"| {display[model['model']]} | {interval('type_accuracy')} | "
            f"{interval('macro_f1')} | {interval('binary_accuracy')} |"
        )
    lines.append("")

    lines.append("### 5.3 F1 por classe")
    lines.append("")
    header = "| Classe | Suporte | " + " | ".join(display[m["model"]] for m in models) + " |"
    lines.append(header)
    lines.append("|---|---:|" + "---:|" * len(models))
    for label in TYPES:
        values = []
        for model in models:
            row = model["multiclass"]["per_class"][label]
            values.append(fmt(row["f1"]))
        lines.append(f"| `{label}` | {support.get(label, 0)} | " + " | ".join(values) + " |")
    lines.append("")
    lines.append(
        "Células “—” indicam classe sem suporte; nesse caso a métrica é indefinida, "
        "não é zero."
    )
    lines.append("")

    lines.append("### 5.4 Comparação pareada")
    lines.append("")
    paired = comparison.get("paired") or {}
    common = paired.get("common_ids") or 0
    lines.append(
        f"Como os três completaram a avaliação, a comparação pareada usa **{common} itens "
        "comuns**. Ela evita que diferenças de cobertura distorçam o resultado."
    )
    lines.append("")
    lines.append("| Modelo | N | Acurácia tipo | Macro-F1 | Acurácia alerta | F1 alerta |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for model in models:
        subset = (paired.get("per_model") or {}).get(model["key"])
        if not subset:
            continue
        lines.append(
            f"| {display[model['model']]} | {subset['n']} | {fmt(subset['type_accuracy'])} | "
            f"{fmt(subset['multiclass']['macro_f1'])} | "
            f"{fmt(subset['binary_relevante']['accuracy'])} | "
            f"{fmt(subset['binary_relevante']['f1'])} |"
        )
    lines.append("")

    lines.append("### 5.5 Área de cobertura")
    lines.append("")
    lines.append(
        "O gabarito tem 6 itens fora da área. O modelo deve manter o tipo do evento, "
        "marcar `fora_da_area=true` e **não** alertar. Alertar um item fora da área é "
        "falso positivo operacional."
    )
    lines.append("")
    lines.append("| Modelo | Fora no gabarito | Detectados como fora | Itens fora alertados |")
    lines.append("|---|---:|---:|---:|")
    for model in models:
        predictions = model.get("predictions", [])
        gt_fora = sum(1 for pred in predictions if pred["gold_fora"])
        detected = sum(
            1 for pred in predictions if pred["gold_fora"] and pred["pred_fora"]
        )
        alerted = sum(
            1 for pred in predictions if pred["gold_fora"] and pred["pred_relevante"]
        )
        lines.append(
            f"| {display[model['model']]} | {gt_fora} | {detected}/{gt_fora} | {alerted} |"
        )
    lines.append("")
    lines.append(
        "Nenhum dos três modelos alertou um item fora da área. A diferença está em "
        "quanto eles percebem corretamente que o evento é fora da cobertura; isso importa "
        "para o produto não gerar alerta para outras regiões."
    )
    lines.append("")

    lines.append("### 5.6 Latência")
    lines.append("")
    lines.append("| Modelo | Média | Mediana | p95 | Máxima |")
    lines.append("|---|---:|---:|---:|---:|")
    for model in models:
        latency = model["latency"]
        lines.append(
            f"| {display[model['model']]} | {fmt(latency.get('mean_s'), 1)} s | "
            f"{fmt(latency.get('median_s'), 1)} s | {fmt(latency.get('p95_s'), 1)} s | "
            f"{fmt(latency.get('max_s'), 1)} s |"
        )
    lines.append("")
    if "ollama/qwen3:8b" in display:
        lines.append(
            "O Qwen3 roda 100% na GPU local (RX 6700 XT, ROCm) e tem custo marginal zero. "
            "A primeira chamada inclui o carregamento do modelo e é mais lenta; as demais "
            "ficam na casa de 11–15 s por item."
        )
        lines.append("")

    lines.append("### 5.7 Endereço")
    lines.append("")
    lines.append(
        "Comparação textual normalizada, sem geocodificação. A coluna “fuzzy” aceita "
        "variações de escrita; “fuzzy entre ambos” considera só os itens em que o modelo "
        "também devolveu algum endereço."
    )
    lines.append("")
    lines.append("| Modelo | Itens com endereço no gabarito | Fuzzy | Fuzzy entre ambos | Endereço previsto sem GT |")
    lines.append("|---|---:|---:|---:|---:|")
    for model in models:
        address = model["address"]
        lines.append(
            f"| {display[model['model']]} | {address['gt_com_endereco']} | "
            f"{fmt(address['fuzzy'])} | {fmt(address['fuzzy_ambos'])} | "
            f"{address['gt_sem_endereco_pred_com_endereco']} |"
        )
    lines.append("")
    lines.append(
        "Esse é o ponto mais fraco dos três. DeepSeek e Gemini frequentemente completam "
        "cidade ou bairro mesmo quando o gabarito não tinha endereço explícito (39 e 38 "
        "casos); o Qwen3 faz isso bem menos (9 casos), mas também acerta menos o endereço "
        "quando ele existe (fuzzy 0,625). Para o produto, todo endereço deve ser tratado "
        "como **local provável**, não como local confirmado, ou passar por "
        "geocodificação/validação antes de aparecer no alerta."
    )
    lines.append("")

    lines.append("## 6. Onde os modelos erram")
    lines.append("")
    lines.append("### 6.1 Principais confusões")
    lines.append("")
    lines.append("| Modelo | Confusão | Ocorrências |")
    lines.append("|---|---|---:|")
    for model in models:
        counter: Counter[tuple[str, str]] = Counter()
        for pred in model.get("predictions", []):
            if pred["pred_type"] and pred["pred_type"] != pred["gold_type"]:
                counter[(pred["gold_type"], pred["pred_type"])] += 1
        for (gold, pred_type), count in counter.most_common(3):
            lines.append(
                f"| {display[model['model']]} | `{gold}` → `{pred_type}` | {count} |"
            )
    lines.append("")
    lines.append(
        "Padrão observado: boa parte dos erros está na fronteira entre **emergência médica**, "
        "**violência física**, **presença de arma** e **nenhum**. São casos em que o texto "
        "descreve uma ocorrência policial ou um atendimento sem deixar claro se ainda há "
        "risco atual para a população."
    )
    lines.append("")

    lines.append("### 6.2 Exemplos de divergência")
    lines.append("")
    lines.append(
        "Itens em que pelo menos um modelo divergiu do gabarito. A coluna de cada modelo "
        "mostra o tipo previsto e se ele geraria alerta (S/N)."
    )
    lines.append("")
    lines.append("| ID | Título | Gabarito | " + " | ".join(display[m["model"]] for m in models) + " |")
    lines.append("|---|---|---|" + "---|" * len(models))
    by_id: dict[str, dict[str, dict[str, Any]]] = {}
    for model in models:
        by_id[model["model"]] = {
            pred["id"]: pred for pred in model.get("predictions", [])
        }
    ranked: list[tuple[int, str]] = []
    for item_id, gold in truth.items():
        wrong = 0
        for model in models:
            pred = by_id[model["model"]].get(item_id)
            if pred and not pred["type_ok"]:
                wrong += 1
        if wrong:
            ranked.append((wrong, item_id))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    for wrong, item_id in ranked[:12]:
        gold = truth[item_id]
        cells = []
        for model in models:
            pred = by_id[model["model"]].get(item_id)
            if not pred:
                cells.append("—")
                continue
            flag = "S" if pred["pred_relevante"] else "N"
            cells.append(f"`{pred['pred_type']}` ({flag})")
        lines.append(
            f"| {item_id} | {cell(title_for(item_id, truth))} | "
            f"`{gold['tipo_perigo']}` ({'S' if gold['relevante'] else 'N'}) | "
            + " | ".join(cells)
            + " |"
        )
    lines.append("")
    lines.append(
        "Esses exemplos são os mais úteis para a reunião: mostram que a discussão não é "
        "só “qual modelo tem o maior número”, mas **que tipo de erro** cada um produz."
    )
    lines.append("")

    lines.append("## 7. Custo, privacidade e operação")
    lines.append("")
    lines.append("| Modelo | Custo por item | Privacidade | Dependência externa |")
    lines.append("|---|---|---|---|")
    lines.append(
        "| DeepSeek Flash | Pago; custo não reportado pela API de sessão | Dados enviados ao provedor | API e saldo |"
        if "deepseek/deepseek-flash" in display
        else ""
    )
    lines.append(
        "| Gemini 3.1 Flash Lite | Plano gratuito com limite de 15 req/min | Dados enviados ao Google | API e cota |"
        if "gemini/gemini-3.1-flash-lite" in display
        else ""
    )
    lines.append(
        "| Qwen3 8B local | Zero custo marginal | Dados não saem da máquina | GPU local |"
        if "ollama/qwen3:8b" in display
        else ""
    )
    lines.append("")
    lines.append(
        "> O relatório automático mostra US$ 0,000000 para DeepSeek e Gemini porque a API "
        "usada não devolveu tokens/custo. Isso **não** significa que sejam gratuitos. "
        "Para o Qwen3 local, o custo marginal é realmente zero; existe o custo do hardware "
        "e da energia."
    )
    lines.append("")
    lines.append(
        "Do ponto de vista operacional, o Qwen3 local é o único que funciona sem internet, "
        "sem chave de API, sem cota e sem enviar o conteúdo dos posts para terceiros. "
        "Em compensação, exige uma máquina com GPU e ocupa cerca de 7,5 GB de VRAM."
    )
    lines.append("")

    lines.append("## 8. Recomendação")
    lines.append("")
    if best["model"].startswith("ollama/"):
        lines.append(
            f"**Escolha principal: {display[best['model']]}.** Ele lidera o macro-F1 "
            f"({fmt(best['multiclass']['macro_f1'])}) e a acurácia de alerta "
            f"({fmt(best['binary_relevante']['accuracy'])}), com custo marginal zero e "
            "dados mantidos localmente."
        )
    else:
        lines.append(
            f"**Se a prioridade for qualidade máxima: {display[best['model']]}.** "
            f"Lidera o macro-F1 ({fmt(best['multiclass']['macro_f1'])}) e a acurácia de "
            f"alerta ({fmt(best['binary_relevante']['accuracy'])})."
        )
    lines.append("")
    if local and best["model"] != local["model"]:
        lines.append(
            f"**Se a prioridade for custo zero e privacidade: {display[local['model']]}.** "
            f"Fica {relative_text(gap_local)} em macro-F1, mas roda localmente, sem cota, "
            "sem chave e sem enviar dados para fora. Para um piloto ou uma operação com "
            "orçamento restrito, é a escolha mais sustentável."
        )
        lines.append("")
    if gemini:
        lines.append(
            f"**Gemini 3.1 Flash Lite** é viável como API gratuita, mas o recall muito alto "
            f"({fmt(gemini['binary_relevante']['recall'])}) vem com precisão menor "
            f"({fmt(gemini['binary_relevante']['precision'])}). Se for usado, vale aplicar "
            "uma etapa de confirmação ou um limiar de confiança para reduzir alertas em excesso."
        )
        lines.append("")
    deepseek_model = next(
        (model for model in models if model["model"].startswith("deepseek/")), None
    )
    if deepseek_model and local:
        deep_bin = deepseek_model["binary_relevante"]
        local_bin = local["binary_relevante"]
        lines.append(
            f"**Trade-off operacional observado:** o DeepSeek emitiu "
            f"{deep_bin['predicted_positives']} alertas ({deep_bin['tp']} corretos, "
            f"{deep_bin['fp']} falsos positivos, {deep_bin['fn']} falsos negativos); "
            f"o Qwen3 emitiu {local_bin['predicted_positives']} "
            f"({local_bin['tp']} corretos, {local_bin['fp']} falsos positivos, "
            f"{local_bin['fn']} falsos negativos). O Qwen3 erra menos por excesso, mas "
            "deixa passar mais eventos. A escolha depende de qual erro é mais caro "
            "para a operação."
        )
        lines.append("")
    lines.append(
        "**Sugestão de arquitetura:** usar o modelo local como primeira triagem, barato e "
        "privado, e reservar o modelo pago para os casos de baixa confiança ou de classes "
        "raras. Isso combina custo baixo com a qualidade do melhor modelo."
    )
    lines.append("")

    lines.append("## 9. Limitações")
    lines.append("")
    lines.append(
        f"- **Amostra de {len(truth)} itens**, com classes raras tendo 2–7 exemplos; "
        "uma diferença de um item muda bastante o F1 dessas classes."
    )
    lines.append(
        "- **Um único anotador.** Não houve dupla anotação nem cálculo de concordância "
        "(kappa). O gabarito é uma referência, não uma verdade absoluta."
    )
    lines.append(
        "- **Few-shot compacto.** Os exemplos foram truncados em 600 caracteres para "
        "viabilizar o modelo local. O prompt completo pode mudar o resultado, "
        "principalmente nos itens truncados."
    )
    lines.append(
        "- **Endereço avaliado por texto**, sem geocodificação. O relatório não mede "
        "distância real nem se o alerta chegaria ao bairro certo."
    )
    lines.append(
        "- **Custo do DeepSeek e do Gemini não foi reportado** pela API usada; "
        "não trate US$ 0,000000 como custo real."
    )
    lines.append(
        "- **Modelos e cotas mudam.** O Gemini 3.8 Flash estava indisponível; foi usado "
        "o 3.1 Flash Lite. O big-pickle free parou por limite de uso e ficou fora da "
        "comparação principal."
    )
    lines.append("")

    lines.append("## 10. Próximos passos")
    lines.append("")
    lines.append(
        "1. Revisar os 14 itens marcados para revisão e os casos de divergência da seção 6.2."
    )
    lines.append(
        "2. Ampliar a amostra para 300–500 posts e incluir dupla anotação em pelo menos 20%."
    )
    lines.append(
        "3. Testar o prompt completo (sem truncar os exemplos) no Qwen3 local e comparar "
        "com o compacto."
    )
    lines.append(
        "4. Medir o custo real do DeepSeek e do Gemini por 1.000 posts antes de decidir."
    )
    lines.append(
        "5. Validar o modelo escolhido em produção sombra, comparando alertas com a "
        "avaliação humana por 2–4 semanas."
    )
    lines.append("")

    lines.append("## 11. Arquivos e reprodutibilidade")
    lines.append("")
    lines.append(
        "- `scripts/data/eval/annotation_blind.jsonl` — amostra cega de 120 posts."
    )
    lines.append(
        "- `scripts/data/eval/ground_truth.jsonl` — gabarito anotado manualmente."
    )
    lines.append(
        "- `scripts/data/eval/few_shot_examples_compact.jsonl` — 26 exemplos usados no prompt."
    )
    lines.append(
        "- `scripts/data/eval/runs/` — respostas brutas, metadados e resumos por modelo."
    )
    lines.append(
        "- `scripts/data/eval/reports/comparison_metrics.json` — métricas completas, "
        "sem respostas brutas, próprio para versionamento."
    )
    lines.append(
        "- `scripts/data/eval/reports/comparison.json` — versão local completa, com "
        "predições e respostas brutas; não versionada por conter conteúdo de terceiros."
    )
    lines.append(
        "- `scripts/data/eval/evaluate.py` — cálculo das métricas e bootstrap."
    )
    lines.append(
        "- `scripts/data/eval/make_report.py` — geração deste relatório."
    )
    lines.append("")
    lines.append("Comandos principais:")
    lines.append("")
    lines.append("```powershell")
    lines.append("python scripts/data/eval/evaluate.py `")
    lines.append("  scripts/data/eval/runs/deepseek_flash_compact.jsonl `")
    lines.append("  scripts/data/eval/runs/gemini_3_1_flash_lite_compact.jsonl `")
    lines.append("  scripts/data/eval/runs/ollama_qwen3_8b_compact.jsonl `")
    lines.append("  --out-dir scripts/data/eval/reports --name comparison --bootstrap 1000")
    lines.append("")
    lines.append("python scripts/data/eval/make_report.py")
    lines.append("```")
    lines.append("")

    lines.append("## Apêndice — big-pickle free")
    lines.append("")
    lines.append(
        "O `opencode/big-pickle` foi testado, mas o plano gratuito impõe limite por sessão "
        "(uma geração por sessão) e um limite global por período. A execução parou perto "
        "de 50 itens, com prompt completo, e por isso **não entra na comparação principal**. "
        "Para usá-lo seria necessário assinatura OpenCode Go ou nova janela de cota."
    )
    lines.append("")

    metrics = json.loads(json.dumps(comparison))
    for model in metrics.get("models", []):
        model.pop("predictions", None)
    metrics["note"] = (
        "Versão sanitizada de comparison.json: sem predições item a item e sem "
        "respostas brutas. Gerada por make_report.py para versionamento."
    )
    (REPORTS / "comparison_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"relatório gravado em {OUTPUT}")
    return 0


def relative_text(gap: float | None) -> str:
    if gap is None:
        return "empatado"
    return f"{gap * 100:.2f} pontos percentuais abaixo do melhor".replace(".", ",")


if __name__ == "__main__":
    raise SystemExit(main())
