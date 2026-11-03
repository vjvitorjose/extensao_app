# -*- coding: utf-8 -*-
"""Monta o conjunto few-shot da avaliação, fora dos 120 itens do gabarito.

Os exemplos reais vêm de `facebook_sjddoficial_posts.json` (mesmo universo da
amostra), mas são selecionados por título e conferidos contra
`annotation_blind.jsonl`. As classes sem exemplo real disponível usam exemplos
sintéticos, marcados com `origem = "sintetico"`.

Uso:
    python scripts/data/eval/_build_few_shot.py

Saídas:
    scripts/data/eval/few_shot_examples.jsonl
    scripts/data/eval/few_shot_manifest.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent
POSTS = DATA / "facebook_sjddoficial_posts.json"
BLIND = BASE / "annotation_blind.jsonl"
OUT_JSONL = BASE / "few_shot_examples.jsonl"
OUT_MANIFEST = BASE / "few_shot_manifest.json"

TAXONOMY = [
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


def norm(text: str | None) -> str:
    """Normaliza para comparação: sem acento, minúsculo, só letras/números."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def unique_posts(posts: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for post in posts:
        key = (norm(post.get("titulo")), norm(post.get("conteudo_completo")))
        if key in seen:
            continue
        seen.add(key)
        out.append(post)
    return out


# 20 exemplos reais. `match` é um prefixo do título normalizado (sem acentos),
# escolhido para ser único no universo de posts únicos fora do teste.
REAL_EXAMPLES = [
    {
        "match": "uma funcionaria da unidade de pronto atendimento",
        "tipo_perigo": "assedio",
        "descricao": (
            "Funcionária da UPA de São João del-Rei denuncia assédio sexual e "
            "moral contra o diretor da unidade."
        ),
        "endereco": "UPA de São João del-Rei",
        "confianca": 0.85,
        "revisar": False,
        "observacoes": "Denúncia registrada; caso em apuração.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um jovem de 23 anos foi preso nesta quinta feira",
        "tipo_perigo": "perseguicao",
        "descricao": (
            "Jovem foge da Polícia Militar em alta velocidade em Conselheiro "
            "Lafaiete, abandona a namorada ferida e é preso após perseguição."
        ),
        "endereco": "Conselheiro Lafaiete, MG",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "Evento fora da área de cobertura.",
        "fora_da_area": True,
        "relevante": False,
    },
    {
        "match": "durante uma operacao de batida policial realizada",
        "tipo_perigo": "local_suspeito",
        "descricao": (
            "Operação policial apreende drogas e materiais do tráfico em uma "
            "oficina no bairro Córrego do Ouro."
        ),
        "endereco": "Bairro Córrego do Ouro, São João del-Rei",
        "confianca": 0.80,
        "revisar": False,
        "observacoes": "Ponto de tráfico com local identificável.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "dois homens foram conduzidos a delegacia de policia civil",
        "tipo_perigo": "local_suspeito",
        "descricao": (
            "Dois homens são conduzidos à delegacia após ocorrência de tráfico "
            "e uso de drogas no bairro Cuiabá, em Tiradentes."
        ),
        "endereco": "Bairro Cuiabá, Tiradentes",
        "confianca": 0.80,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um acidente foi registrado na tarde desta terca feira 6",
        "tipo_perigo": "acidente_transito",
        "descricao": (
            "Motocicleta colide com ciclista próximo à ponte entre São João "
            "del-Rei e Santa Cruz de Minas; um homem fica ferido."
        ),
        "endereco": "Ponte entre São João del-Rei e Santa Cruz de Minas",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um carro e um onibus da dkn transportes",
        "tipo_perigo": "acidente_transito",
        "descricao": (
            "Carro e ônibus da DKN Transportes colidem no Trevo do Tijuco, em "
            "São João del-Rei."
        ),
        "endereco": "Trevo do Tijuco, São João del-Rei",
        "confianca": 0.85,
        "revisar": False,
        "observacoes": "Texto truncado no teaser do Facebook.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "uma motocicleta foi furtada na noite deste sabado",
        "tipo_perigo": "furto",
        "descricao": (
            "Motocicleta Honda Titan 150 é furtada na Rua Sebastião Alves do "
            "Banho, no bairro Colônia do Marçal."
        ),
        "endereco": (
            "Rua Sebastião Alves do Banho, Colônia do Marçal, "
            "São João del-Rei"
        ),
        "confianca": 0.95,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "uma ocorrencia de furto foi registrada na noite de segunda feira",
        "tipo_perigo": "furto",
        "descricao": (
            "Dois suspeitos subtraem produtos de um estabelecimento comercial "
            "no bairro Matosinhos sem efetuar o pagamento."
        ),
        "endereco": "Bairro Matosinhos, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um video mostra uma briga generalizada",
        "tipo_perigo": "violencia_fisica",
        "descricao": (
            "Vídeo mostra briga generalizada entre jovens nas proximidades da "
            "Rodoviária Velha, em São João del-Rei."
        ),
        "endereco": "Proximidades da Rodoviária Velha, São João del-Rei",
        "confianca": 0.80,
        "revisar": False,
        "observacoes": "Texto truncado no teaser do Facebook.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "uma tentativa de homicidio foi registrada na manha desta sexta feira 29",
        "tipo_perigo": "violencia_fisica",
        "descricao": (
            "Tentativa de homicídio é registrada no bairro Barro Preto; a "
            "vítima é socorrida com vida."
        ),
        "endereco": "Bairro Barro Preto, São João del-Rei",
        "confianca": 0.80,
        "revisar": False,
        "observacoes": "Sem informação sobre arma de fogo; tipo pelo evento central.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um adolescente de 17 anos morreu apos ser baleado",
        "tipo_perigo": "presenca_arma",
        "descricao": (
            "Adolescente de 17 anos é baleado e morre em Santa Cruz de Minas; "
            "dois suspeitos em uma motocicleta efetuaram os disparos."
        ),
        "endereco": "Rua Artur Napoleão Morais, Santa Cruz de Minas",
        "confianca": 0.95,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "disparos de arma de fogo foram registrados na noite deste domingo 12 no bairro aguas ferreas",
        "tipo_perigo": "presenca_arma",
        "descricao": (
            "Disparos de arma de fogo são registrados no bairro Águas Férreas; "
            "um homem teria sido atingido."
        ),
        "endereco": "Bairro Águas Férreas, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um incendio de grandes proporcoes mobiliza equipes",
        "tipo_perigo": "incendio_fumaca",
        "descricao": (
            "Incêndio de grandes proporções atinge um prédio e áreas de "
            "vegetação nos bairros Caieiras e São Judas Tadeu."
        ),
        "endereco": "Bairros Caieiras e São Judas Tadeu, São João del-Rei",
        "confianca": 0.95,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um carro teve um principio de incendio",
        "tipo_perigo": "incendio_fumaca",
        "descricao": (
            "Carro tem princípio de incêndio na Avenida Josué de Queirós, em "
            "São João del-Rei."
        ),
        "endereco": "Avenida Josué de Queirós, São João del-Rei",
        "confianca": 0.80,
        "revisar": False,
        "observacoes": "Texto truncado no teaser do Facebook.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "parte do tronco de uma arvore caiu",
        "tipo_perigo": "via_bloqueada",
        "descricao": (
            "Parte do tronco de uma árvore cai na Rua Comendador Bastos e "
            "provoca a interdição parcial da via."
        ),
        "endereco": "Rua Comendador Bastos, Centro, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "a rua paulo freitas em sao joao del rei",
        "tipo_perigo": "via_bloqueada",
        "descricao": (
            "Rua Paulo Freitas sofre com pontos de alagamento durante a chuva "
            "em São João del-Rei."
        ),
        "endereco": "Rua Paulo Freitas, São João del-Rei",
        "confianca": 0.85,
        "revisar": False,
        "observacoes": "Texto truncado no teaser do Facebook.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "um grave acidente foi registrado nesta terca feira",
        "tipo_perigo": "emergencia_medica",
        "descricao": (
            "Motorista de 53 anos fica preso às ferragens após acidente na "
            "MGC-383 e é resgatado por bombeiros."
        ),
        "endereco": "Rodovia MGC-383, sentido Madre de Deus de Minas",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "Evento central é o resgate/ferimento, não só a colisão.",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "match": "a diocese de sao joao del rei divulgou uma nota de pesar",
        "tipo_perigo": "emergencia_medica",
        "descricao": (
            "Ônibus com 48 romeiros sai da pista e cai em uma ribanceira em "
            "Cruzeiro, SP; há vítimas."
        ),
        "endereco": "Cruzeiro, SP",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "Evento fora da área de cobertura.",
        "fora_da_area": True,
        "relevante": False,
    },
    {
        "match": "mulheres a partir de 15 anos ja podem se inscrever",
        "tipo_perigo": "nenhum",
        "descricao": (
            "Campanha municipal oferece curso gratuito de defesa pessoal para "
            "mulheres; não há evento de perigo concreto."
        ),
        "endereco": "São João del-Rei",
        "confianca": 0.95,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": False,
    },
    {
        "match": "o el nino e um fenomeno climatico",
        "tipo_perigo": "nenhum",
        "descricao": (
            "Artigo explica o fenômeno El Niño e seus efeitos climáticos; não "
            "descreve evento de perigo concreto."
        ),
        "endereco": None,
        "confianca": 0.95,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": False,
    },
]


SYNTHETIC_EXAMPLES = [
    {
        "tipo_perigo": "assedio",
        "titulo": (
            "Uma mulher relatou ter sido importunada sexualmente por um homem "
            "dentro de um ônibus do transporte coletivo, no bairro Tejuco, em "
            "São João del-Rei."
        ),
        "conteudo_completo": (
            "Uma mulher relatou ter sido importunada sexualmente por um homem "
            "dentro de um ônibus do transporte coletivo, no bairro Tejuco, em "
            "São João del-Rei. O suspeito desembarcou e fugiu. A Polícia "
            "Militar foi acionada e registrou a ocorrência."
        ),
        "descricao": (
            "Mulher relata importunação sexual dentro de ônibus no bairro "
            "Tejuco."
        ),
        "endereco": "Bairro Tejuco, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "tipo_perigo": "iluminacao_ruim",
        "titulo": (
            "Moradores do bairro Colônia do Marçal relatam que a Rua das "
            "Acácias está há semanas sem iluminação pública."
        ),
        "conteudo_completo": (
            "Moradores do bairro Colônia do Marçal relatam que a Rua das "
            "Acácias está há semanas sem iluminação pública. O local fica "
            "escuro à noite e, segundo os moradores, aumenta o risco de "
            "assaltos. A prefeitura foi acionada."
        ),
        "descricao": (
            "Rua das Acácias está sem iluminação pública há semanas, segundo "
            "moradores."
        ),
        "endereco": "Rua das Acácias, Colônia do Marçal, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "tipo_perigo": "iluminacao_ruim",
        "titulo": (
            "Um poste de iluminação foi danificado em uma colisão na Avenida "
            "Leite de Castro, em São João del-Rei, e a via ficou às escuras."
        ),
        "conteudo_completo": (
            "Um poste de iluminação foi danificado em uma colisão na Avenida "
            "Leite de Castro, em São João del-Rei, e a via ficou às escuras "
            "durante a noite. Motoristas e pedestres relatam dificuldade de "
            "circulação no trecho."
        ),
        "descricao": (
            "Poste danificado deixa trecho da Avenida Leite de Castro sem "
            "iluminação."
        ),
        "endereco": "Avenida Leite de Castro, São João del-Rei",
        "confianca": 0.85,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "tipo_perigo": "perseguicao",
        "titulo": (
            "Uma mulher foi seguida por um homem em uma motocicleta por várias "
            "ruas do Centro de São João del-Rei."
        ),
        "conteudo_completo": (
            "Uma mulher foi seguida por um homem em uma motocicleta por várias "
            "ruas do Centro de São João del-Rei. Ela só conseguiu escapar ao "
            "entrar em uma loja. A Polícia Militar foi acionada e faz buscas "
            "pelo suspeito."
        ),
        "descricao": (
            "Mulher é seguida por homem em motocicleta no Centro de São João "
            "del-Rei."
        ),
        "endereco": "Centro, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "tipo_perigo": "assalto",
        "titulo": (
            "Dois homens armados renderam um comerciante e levaram dinheiro do "
            "caixa de uma padaria no Centro de São João del-Rei."
        ),
        "conteudo_completo": (
            "Dois homens armados renderam um comerciante e levaram dinheiro do "
            "caixa de uma padaria no Centro de São João del-Rei. Ninguém ficou "
            "ferido. A Polícia Militar foi acionada e realiza buscas pelos "
            "suspeitos."
        ),
        "descricao": (
            "Dois homens armados assaltam padaria no Centro de São João "
            "del-Rei."
        ),
        "endereco": "Centro, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
    {
        "tipo_perigo": "assalto",
        "titulo": (
            "Um motociclista foi abordado por dois suspeitos em uma moto e teve "
            "o celular e a carteira roubados na Avenida Leite de Castro, em "
            "São João del-Rei."
        ),
        "conteudo_completo": (
            "Um motociclista foi abordado por dois suspeitos em uma moto e teve "
            "o celular e a carteira roubados na Avenida Leite de Castro, em "
            "São João del-Rei. A vítima não se feriu. A Polícia Militar foi "
            "acionada."
        ),
        "descricao": (
            "Motociclista tem celular e carteira roubados por dois suspeitos "
            "em uma moto."
        ),
        "endereco": "Avenida Leite de Castro, São João del-Rei",
        "confianca": 0.90,
        "revisar": False,
        "observacoes": "",
        "fora_da_area": False,
        "relevante": True,
    },
]


def main() -> None:
    posts = json.loads(POSTS.read_text(encoding="utf-8"))
    unique = unique_posts(posts)
    blind = read_jsonl(BLIND)
    blind_titles = {norm(item.get("titulo")) for item in blind}
    blind_contents = {norm(item.get("conteudo_completo")) for item in blind}

    outside = [
        post
        for post in unique
        if norm(post.get("titulo")) not in blind_titles
        and norm(post.get("conteudo_completo")) not in blind_contents
    ]

    records: list[dict] = []
    used_titles: set[str] = set()

    for index, annotation in enumerate(REAL_EXAMPLES, start=1):
        match = norm(annotation["match"])
        candidates = [post for post in outside if norm(post.get("titulo")).startswith(match)]
        # Evita usar o mesmo post duas vezes, mesmo que dois prefixos coincidam.
        candidates = [post for post in candidates if norm(post.get("titulo")) not in used_titles]
        if not candidates:
            raise SystemExit(f"Exemplo real não encontrado: {annotation['match']!r}")
        post = candidates[0]
        used_titles.add(norm(post.get("titulo")))
        record = {
            "id": f"fs-real-{index:02d}",
            "origem": "real",
            "fonte_url": post.get("fonte_url"),
            "fonte_data": post.get("fonte_data"),
            "titulo": post.get("titulo"),
            "conteudo_completo": post.get("conteudo_completo"),
            **{key: annotation[key] for key in (
                "tipo_perigo",
                "descricao",
                "endereco",
                "confianca",
                "revisar",
                "observacoes",
                "fora_da_area",
                "relevante",
            )},
        }
        records.append(record)

    for index, annotation in enumerate(SYNTHETIC_EXAMPLES, start=1):
        record = {
            "id": f"fs-syn-{index:02d}",
            "origem": "sintetico",
            "fonte_url": None,
            "fonte_data": None,
            "titulo": annotation["titulo"],
            "conteudo_completo": annotation["conteudo_completo"],
            **{key: annotation[key] for key in (
                "tipo_perigo",
                "descricao",
                "endereco",
                "confianca",
                "revisar",
                "observacoes",
                "fora_da_area",
                "relevante",
            )},
        }
        records.append(record)

    # Validações.
    counts = Counter(record["tipo_perigo"] for record in records)
    missing = [tipo for tipo in TAXONOMY if counts[tipo] != 2]
    if missing:
        raise SystemExit(f"Cada classe deve ter exatamente 2 exemplos; ajustar: {missing}")

    for record in records:
        if record["tipo_perigo"] not in TAXONOMY:
            raise SystemExit(f"Tipo inválido: {record['tipo_perigo']!r}")
        expected_relevant = record["tipo_perigo"] != "nenhum" and not record["fora_da_area"]
        if record["relevante"] != expected_relevant:
            raise SystemExit(
                f"Relevância inconsistente em {record['id']}: "
                f"esperado {expected_relevant}, obtido {record['relevante']}"
            )
        if norm(record["titulo"]) in blind_titles or norm(record["conteudo_completo"]) in blind_contents:
            raise SystemExit(f"Vazamento: {record['id']} está no conjunto de teste")

    OUT_JSONL.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "total": len(records),
        "por_classe": dict(sorted(counts.items())),
        "reais": sum(1 for record in records if record["origem"] == "real"),
        "sinteticos": sum(1 for record in records if record["origem"] == "sintetico"),
        "fora_da_area": sum(1 for record in records if record["fora_da_area"]),
        "alertaveis": sum(1 for record in records if record["relevante"]),
        "universo_posts": len(posts),
        "universo_unico": len(unique),
        "universo_fora_do_teste": len(outside),
        "arquivo": OUT_JSONL.name,
        "validacoes": [
            "2 exemplos por classe da taxonomia",
            "relevante = tipo_perigo != nenhum e fora_da_area == false",
            "nenhum título/conteúdo do conjunto de teste",
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
