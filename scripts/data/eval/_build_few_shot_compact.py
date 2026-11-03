# -*- coding: utf-8 -*-
"""Gera uma versão compacta dos 26 exemplos few-shot.

O modelo local (Ollama) processa o prompt no CPU/GPU doméstica. Para manter a
avaliação viável, o conteúdo de cada exemplo é truncado em um limite de
caracteres. Títulos, datas, rótulos e todos os campos de saída são preservados.
O mesmo arquivo compacto deve ser usado pelos três modelos comparados.

Uso:
    python scripts/data/eval/_build_few_shot_compact.py
    python scripts/data/eval/_build_few_shot_compact.py --max-chars 400
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "few_shot_examples.jsonl"
OUTPUT = BASE / "few_shot_examples_compact.jsonl"
MANIFEST = BASE / "few_shot_compact_manifest.json"


def truncate(text: str | None, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # Evita cortar no meio de uma palavra.
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:") + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-chars", type=int, default=600)
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--out", default=str(OUTPUT))
    args = parser.parse_args()

    source = Path(args.source)
    examples = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    compact = []
    for example in examples:
        item = dict(example)
        item["conteudo_completo"] = truncate(example.get("conteudo_completo"), args.max_chars)
        item["_truncated"] = len(example.get("conteudo_completo") or "") > args.max_chars
        compact.append(item)

    out = Path(args.out)
    out.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in compact) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "source": str(source),
        "out": str(out),
        "max_chars": args.max_chars,
        "examples": len(compact),
        "truncated": sum(1 for item in compact if item["_truncated"]),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "out_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "source_chars": sum(
            len(item.get("titulo") or "") + len(item.get("conteudo_completo") or "")
            for item in examples
        ),
        "out_chars": sum(
            len(item.get("titulo") or "") + len(item.get("conteudo_completo") or "")
            for item in compact
        ),
        "by_type": {},
    }
    counts: dict[str, int] = {}
    for item in compact:
        counts[item["tipo_perigo"]] = counts.get(item["tipo_perigo"], 0) + 1
    manifest["by_type"] = dict(sorted(counts.items()))
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
