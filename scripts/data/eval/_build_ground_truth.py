"""Consolida a anotacao manual cega dos 120 itens de annotation_blind.jsonl.

Este arquivo e a fonte das anotacoes. Rode-o para regerar ground_truth.jsonl
e ground_truth.csv. Os campos de anotacao foram preenchidos manualmente, sem
consultar os pre-rotulos do Gemini.
"""

import csv
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
BLIND = BASE / "annotation_blind.jsonl"
OUT_JSONL = BASE / "ground_truth.jsonl"
OUT_CSV = BASE / "ground_truth.csv"

TAXONOMY = {
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
}

# id: (tipo_perigo, descricao, endereco, confianca, revisar, observacoes)
A = {
    "sjd-001": ("nenhum", "Operacao da Ficco cumpre mandados por trafico internacional em Sao Joao del-Rei; acao policial sem local ou risco imediato.", None, 0.90, False, ""),
    "sjd-002": ("violencia_fisica", "Homem resiste a abordagem da Guarda Civil, danifica o proprio veiculo e avanca contra os agentes com uma ferramenta.", "Sao Joao del-Rei, MG", 0.85, False, ""),
    "sjd-003": ("assedio", "Medico de 31 anos e preso em Resende Costa por suspeita de crimes sexuais e assedio durante atendimentos.", "Resende Costa, MG", 0.90, False, ""),
    "sjd-004": ("emergencia_medica", "Jovem de 20 anos morre afogado em lagoa na zona rural de Lagoa Dourada.", "Zona rural de Lagoa Dourada, MG", 0.95, False, ""),
    "sjd-005": ("nenhum", "Relato de racismo em resort de Tiradentes; nao ha evento de seguranca fisica ou alerta local.", "Tiradentes, MG", 0.90, False, "tipo nao coberto pela taxonomia"),
    "sjd-006": ("presenca_arma", "Jovem baleado durante desfile em Sao Joao del-Rei nao resiste; suspeitos foram presos.", "Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-007": ("presenca_arma", "Adolescente de 15 anos e atingida por disparos no Residencial Risoleta Neves 1, bairro Tijuco.", "Residencial Risoleta Neves 1, Bairro Tijuco, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-008": ("nenhum", "Homenagem a carnavalescos da cidade; conteudo cultural.", None, 0.95, False, ""),
    "sjd-009": ("nenhum", "Pos-jogo de futebol com confusao e reclamacoes de arbitragem; sem evento de seguranca publica.", None, 0.95, False, ""),
    "sjd-010": ("acidente_transito", "Acidente frontal entre moto e carro na BR-265, proximo a Calcinacao Vitoria, mata motociclista.", "BR-265, proximidades da Calcinacao Vitoria, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-011": ("nenhum", "Regra eleitoral sobre restricao de prisoes; conteudo informativo nacional.", None, 0.95, False, ""),
    "sjd-012": ("incendio_fumaca", "Onibus da linha 634 e incendiado por criminosos em Venda Nova, Belo Horizonte; fora da area de cobertura.", "Bairro Nova York, Venda Nova, Belo Horizonte, MG", 0.95, False, "fora_da_area"),
    "sjd-013": ("nenhum", "Obito do radialista Geraldinho; conteudo cultural e obituario.", None, 0.95, False, ""),
    "sjd-014": ("assalto", "Mulher e assaltada com faca nas proximidades de supermercado na Avenida Leite de Castro, bairro Fabricas.", "Avenida Leite de Castro, Bairro Fabricas, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-015": ("emergencia_medica", "Enxame de abelhas causa tumulto na Rua Aureliano Raposo, regiao central; texto truncado.", "Rua Aureliano Raposo, Centro, Sao Joao del-Rei, MG", 0.65, True, "texto_truncado"),
    "sjd-016": ("nenhum", "Concurso Rainha Agro 2026; evento cultural.", None, 0.95, False, ""),
    "sjd-017": ("nenhum", "Comparativo de mudancas da cidade em 10 anos; conteudo de redes sociais.", None, 0.95, False, ""),
    "sjd-018": ("acidente_transito", "Motociclista de 48 anos morre em colisao com carro na Avenida Maria Alves Barbosa, bairro Tijuco.", "Avenida Maria Alves Barbosa, Bairro Tijuco, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-019": ("nenhum", "Campanha contra pichacao; conteudo institucional.", None, 0.90, False, ""),
    "sjd-020": ("nenhum", "Entrega de viaturas ao Corpo de Bombeiros em outras regioes; Sao Joao del-Rei nao foi contemplada.", None, 0.95, False, ""),
    "sjd-021": ("nenhum", "Anuncio de shows de Alcione e Maria Gadu no aniversario da cidade; conteudo cultural.", None, 0.95, False, ""),
    "sjd-022": ("assedio", "Homem e retirado de onibus Tarifa Zero apos relatos de possivel importunacao; texto truncado.", "Onibus Tarifa Zero, Sao Joao del-Rei, MG", 0.65, True, "texto_truncado; tipo inferido do titulo"),
    "sjd-023": ("nenhum", "Dados estaduais sobre mortalidade por cancer de prostata; conteudo de saude publica.", None, 0.95, False, ""),
    "sjd-024": ("emergencia_medica", "Homem morre apos ataque de enxame de abelhas na Colonia do Recondengo, zona rural.", "Colonia do Recondengo, zona rural de Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-025": ("nenhum", "Articulacao para implantacao do segundo hospital universitario; conteudo administrativo.", None, 0.90, False, ""),
    "sjd-026": ("acidente_transito", "Veiculo atinge fachada de residencia ao tentar manobra de re na Rua Coronel Jose de Assis Sobrinho, Matosinhos; sem feridos.", "Rua Coronel Jose de Assis Sobrinho, Bairro Matosinhos, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-027": ("emergencia_medica", "Estudante de 13 anos morre apos mal subito em aula de educacao fisica na Escola Estadual Tome Portes del Rei.", "Escola Estadual Tome Portes del Rei, Bairro Matosinhos, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-028": ("perseguicao", "Homem e capturado apos perseguicao policial; deixa cair revolver calibre .32 durante a fuga.", "Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-029": ("emergencia_medica", "Coletor de lixo fica ferido ao recolher saco com vidro descartado irregularmente; texto truncado.", "Sao Joao del-Rei, MG", 0.75, False, "texto_truncado"),
    "sjd-030": ("furto", "Furto de fios subterraneos na Rua Santo Antonio, bairro Tejuco, causa curto-circuito e prejuizos.", "Rua Santo Antonio, Bairro Tejuco, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-031": ("violencia_fisica", "Operacao da PM no bairro Alto das Merces termina em resistencia, uso de elastometro e spray e duas prisoes.", "Bairro Alto das Merces, Sao Joao del-Rei, MG", 0.70, True, "tipo debativel: operacao policial com resistencia"),
    "sjd-032": ("nenhum", "Casamento do influenciador Gustavo Tubarao em Tiradentes; conteudo social.", "Tiradentes, MG", 0.95, False, ""),
    "sjd-033": ("nenhum", "Luto oficial pela morte de estudante; desdobramento administrativo de ocorrencia ja registrada.", None, 0.95, False, ""),
    "sjd-034": ("via_bloqueada", "Trecho da Avenida Leite de Castro alaga apos poucos minutos de chuva; texto truncado.", "Avenida Leite de Castro, Sao Joao del-Rei, MG", 0.80, False, "texto_truncado"),
    "sjd-035": ("nenhum", "Liberacao de ingressos para a Del Rei Expo; conteudo de servico.", None, 0.95, False, ""),
    "sjd-036": ("incendio_fumaca", "Incendio atinge a Serra de Sao Jose na regiao do Mangue, em Tiradentes; fumaca visivel.", "Serra de Sao Jose, regiao do Mangue, Tiradentes, MG", 0.90, False, ""),
    "sjd-037": ("presenca_arma", "Disparo de arma de fogo durante briga no Bar do Chiquinho, Centro; proprietarios divulgam nota.", "Bar do Chiquinho, Centro, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-038": ("emergencia_medica", "Coletor de lixo fica ferido durante o trabalho em Sao Joao del-Rei; texto truncado.", "Sao Joao del-Rei, MG", 0.75, False, "texto_truncado"),
    "sjd-039": ("nenhum", "Janela de onibus quebra sem feridos; incidente de transporte sem risco atual.", "Cruzamento com a Rua Paulo Freitas, Sao Joao del-Rei, MG", 0.85, False, ""),
    "sjd-040": ("incendio_fumaca", "Cruzeiro das Aguas Santas permanece de pe apos incendio na Serra de Sao Jose; cenario de destruicao.", "Serra de Sao Jose, MG", 0.70, False, "desdobramento de incendio anterior"),
    "sjd-041": ("furto", "Caminhao e produtos agricolas sao furtados em empresa as margens da BR-265, em Barbacena; veiculo recuperado.", "BR-265, Barbacena, MG", 0.90, False, ""),
    "sjd-042": ("violencia_fisica", "Mulher de 30 anos e encontrada morta em residencia no bairro Senhor dos Montes; causas desconhecidas.", "Bairro Senhor dos Montes, Sao Joao del-Rei, MG", 0.55, True, "circunstancias desconhecidas"),
    "sjd-043": ("local_suspeito", "Operacao da PM prende suspeito de trafico no bairro Colonia do Marcal e apreende drogas e balanca.", "Bairro Colonia do Marcal, Sao Joao del-Rei, MG", 0.75, False, ""),
    "sjd-044": ("nenhum", "UFSJ anuncia curso de Engenharia de Energia; conteudo institucional.", None, 0.95, False, ""),
    "sjd-045": ("nenhum", "Prefeito recebe titulo de cidadao honorario; conteudo politico.", None, 0.95, False, ""),
    "sjd-046": ("via_bloqueada", "Carro fica preso em beco ao lado da Catedral do Pilar, no Centro; retirada gera movimentacao.", "Beco ao lado da Catedral Basilica de Nossa Senhora do Pilar, Centro, Sao Joao del-Rei, MG", 0.60, True, "bloqueio pontual e ja resolvido"),
    "sjd-047": ("assalto", "Comercio no Centro e assaltado por homem que simulou estar armado e levou joias.", "Centro, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-048": ("presenca_arma", "Pessoa e ferida por disparos na Rua Padre Custodio Dias; suspeitos fugiram de moto.", "Rua Padre Custodio Dias, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-049": ("nenhum", "Licitacao para jurados do Carnaval; conteudo administrativo.", None, 0.95, False, ""),
    "sjd-050": ("nenhum", "Prefeitura anuncia interdicoes temporarias programadas para obras e eventos; sem incidente de seguranca.", None, 0.90, False, "interdicao planejada"),
    "sjd-051": ("local_suspeito", "Inspecao encontra whisky falsificado em adega de Santa Cruz de Minas; proprietario reage e e autuado.", "Adega em Santa Cruz de Minas, MG", 0.65, True, "risco sanitario; tipo debativel"),
    "sjd-052": ("nenhum", "Escola de samba campea do Carnaval; conteudo cultural.", None, 0.95, False, ""),
    "sjd-053": ("nenhum", "Estreia de curta-metragem; conteudo cultural.", None, 0.95, False, ""),
    "sjd-054": ("emergencia_medica", "Desabamento de predio com lar de idosos mobiliza resgate no bairro Jardim Vitoria; texto truncado.", "Bairro Jardim Vitoria, MG", 0.50, True, "texto_truncado; cidade nao confirmada"),
    "sjd-055": ("nenhum", "Morte do jornalista Renato Machado no Rio de Janeiro; fora da area.", None, 0.95, False, "fora_da_area"),
    "sjd-056": ("furto", "Bicicleta e furtada na regiao central; candidato divulga imagens e pede ajuda.", "Regiao central, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-057": ("nenhum", "Distribuicao de kits de TV digital; conteudo de servico.", None, 0.95, False, ""),
    "sjd-058": ("nenhum", "Retomada das atividades dos CRAS; conteudo de servico.", None, 0.95, False, ""),
    "sjd-059": ("nenhum", "Projeto de iluminacao cenica do patrimonio; nao e iluminacao publica deficiente.", None, 0.95, False, ""),
    "sjd-060": ("emergencia_medica", "Ataque de abelhas na cavalgada da Expo Prados deixa pessoas hospitalizadas, cavalos mortos e colisoes.", "Expo Prados, Prados, MG", 0.85, False, ""),
    "sjd-061": ("nenhum", "Orcamento municipal de 2026; conteudo administrativo.", None, 0.95, False, ""),
    "sjd-062": ("nenhum", "Previsao do tempo com chuva no fim de semana; conteudo meteorologico.", None, 0.95, False, ""),
    "sjd-063": ("emergencia_medica", "Homem de 39 anos morre apos cair de arvore de cerca de 10 metros no bairro Paloma, em Dores de Campos.", "Bairro Paloma, Dores de Campos, MG", 0.90, False, ""),
    "sjd-064": ("local_suspeito", "Adolescente e apreendido com crack apos denuncia de trafico em Sao Joao del-Rei; local nao especificado.", None, 0.55, True, "local nao especificado; acao concluida"),
    "sjd-065": ("nenhum", "Post sobre casamento do influenciador Gustavo Tubarao; conteudo de entretenimento.", None, 0.95, False, ""),
    "sjd-066": ("violencia_fisica", "Briga generalizada em casa de shows na Colonia do Marcal mobiliza a Policia Militar; texto truncado.", "Casa de shows, Colonia do Marcal, Sao Joao del-Rei, MG", 0.80, False, "texto_truncado"),
    "sjd-067": ("nenhum", "Comentario de rede social; sem evento de seguranca.", None, 0.98, False, ""),
    "sjd-068": ("nenhum", "Empate do Athletic com o Sport pela Serie B; conteudo esportivo.", None, 0.98, False, ""),
    "sjd-069": ("nenhum", "Falecimento do pai do prefeito; conteudo institucional e obituario.", None, 0.95, False, ""),
    "sjd-070": ("nenhum", "Indice de Progresso Social do municipio; conteudo estatistico.", None, 0.95, False, ""),
    "sjd-071": ("furto", "Policia Civil recupera manto e coroa furtados de imagem na Matriz de Nossa Senhora da Assuncao, em Barbacena.", "Matriz de Nossa Senhora da Assuncao, Barbacena, MG", 0.90, False, ""),
    "sjd-072": ("nenhum", "Acordo da Prefeitura e DAMAE com a Cemig para quitacao de divida; conteudo administrativo.", None, 0.95, False, ""),
    "sjd-073": ("violencia_fisica", "Corpo de homem nao identificado e encontrado no Rio das Mortes, entre a ponte de Santa Cruz de Minas e o Bezerrao; causas desconhecidas.", "Rio das Mortes, entre a ponte de Santa Cruz de Minas e o Bezerrao, Sao Joao del-Rei, MG", 0.50, True, "circunstancias desconhecidas"),
    "sjd-074": ("nenhum", "Lobo-guara e encontrado morto as margens de rodovia em Resende Costa; suspeita de atropelamento; sem risco humano.", "Rodovia de acesso a Resende Costa, MG", 0.95, False, ""),
    "sjd-075": ("nenhum", "Campanha de dentistas para familias atingidas por chuvas em Juiz de Fora e Uba; fora da area.", None, 0.95, False, "fora_da_area"),
    "sjd-076": ("incendio_fumaca", "Incendio se espalha pela Serra de Sao Jose, entre Sao Joao del-Rei, Tiradentes e Santa Cruz de Minas.", "Serra de Sao Jose, entre Sao Joao del-Rei, Tiradentes e Santa Cruz de Minas, MG", 0.90, False, ""),
    "sjd-077": ("nenhum", "Casal de Sao Joao del-Rei retido em Dubai devido a cancelamentos de voos; fora da area.", None, 0.95, False, "fora_da_area"),
    "sjd-078": ("nenhum", "Reportagem sobre os 30 anos do caso ET de Varginha; conteudo historico.", None, 0.98, False, ""),
    "sjd-079": ("violencia_fisica", "Estudante de medicina e morta com mais de 100 golpes de faca em Barbacena; namorado e preso.", "Barbacena, MG", 0.95, False, ""),
    "sjd-080": ("nenhum", "PM desmente boato de tentativa de sequestro no bairro Matosinhos; nao houve registro.", None, 0.90, False, "boato desmentido"),
    "sjd-081": ("nenhum", "Reorganizacao da gestao do complexo ferroviario; conteudo administrativo.", None, 0.95, False, ""),
    "sjd-082": ("nenhum", "Cartaz de procurado do ex-goleiro Bruno no Rio de Janeiro; fora da area.", None, 0.95, False, "fora_da_area"),
    "sjd-083": ("nenhum", "Campanha de arrecadacao para familias atingidas por chuvas em Uba; fora da area.", None, 0.95, False, "fora_da_area"),
    "sjd-084": ("nenhum", "Explosao de fogos de artificio durante procissao em Matosinhos assusta moradores; sem feridos ou incendio confirmados; texto truncado.", "Procissao do Senhor Bom Jesus de Matosinhos, Sao Joao del-Rei, MG", 0.60, True, "texto_truncado; sem dano confirmado"),
    "sjd-085": ("nenhum", "Anuncio de Paulo Ricardo no festival Sao Joao dos Queijos; conteudo cultural.", None, 0.98, False, ""),
    "sjd-086": ("nenhum", "Procissao do Encontro; conteudo religioso e cultural.", None, 0.98, False, ""),
    "sjd-087": ("nenhum", "Turista argentino e preso por racismo em Tiradentes; crime sem risco fisico atual.", "Proximidades da estacao ferroviaria, Tiradentes, MG", 0.80, False, "tipo nao coberto pela taxonomia"),
    "sjd-088": ("nenhum", "PM flagra consumo de drogas e furto em hospital de Barbacena; ocorrencia resolvida.", "Hospital no Bairro Floresta, Barbacena, MG", 0.75, False, "acao policial concluida"),
    "sjd-089": ("assalto", "Video registra roubo na Rua Aureliano Pimentel, em Sao Joao del-Rei; texto truncado.", "Rua Aureliano Pimentel, Sao Joao del-Rei, MG", 0.80, False, "texto_truncado"),
    "sjd-090": ("perseguicao", "Perseguicao policial termina com carro interceptado na Rua dos Inconfidentes, Centro de Tiradentes; texto truncado.", "Rua dos Inconfidentes, Centro, Tiradentes, MG", 0.80, False, "texto_truncado"),
    "sjd-091": ("incendio_fumaca", "Incendio atinge a Serra do Lenheiro, com fogo avancando perto de residencias no bairro Tejuco.", "Serra do Lenheiro, Bairro Tejuco, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-092": ("nenhum", "Procissao da Soledade com interdicoes viarias programadas; evento planejado.", None, 0.85, False, "interdicao planejada"),
    "sjd-093": ("nenhum", "Meme sobre cabelo por bairro; conteudo de humor.", None, 0.98, False, ""),
    "sjd-094": ("nenhum", "Intervencao filosofica na Rua da Cachaca; conteudo cultural.", None, 0.98, False, ""),
    "sjd-095": ("nenhum", "Aniversario de 39 anos da UFSJ; conteudo institucional.", None, 0.98, False, ""),
    "sjd-096": ("emergencia_medica", "Homem e resgatado apos ficar preso em paredao na Serra de Sao Jose, regiao de Santa Cruz de Minas; texto truncado.", "Serra de Sao Jose, regiao de Santa Cruz de Minas, MG", 0.80, False, "texto_truncado"),
    "sjd-097": ("nenhum", "Obrigatoriedade de maletas de urgencia nas unidades basicas; conteudo de politica publica.", None, 0.95, False, ""),
    "sjd-098": ("nenhum", "Familia pede apuracao de morte apos procedimento odontologico; caso investigado, sem alerta imediato.", "Hospital das Merces, Sao Joao del-Rei, MG", 0.70, True, "tipo nao coberto; caso investigado"),
    "sjd-099": ("nenhum", "Megaoperacao estadual contra faccoes; conteudo geral, sem local especifico.", None, 0.90, False, ""),
    "sjd-100": ("nenhum", "Lancamento de livro em Tiradentes; conteudo cultural.", None, 0.98, False, ""),
    "sjd-101": ("acidente_transito", "Acidente entre carro e motocicleta no cruzamento da Rua Cristovao Colombo; texto truncado e cidade nao explicita.", "Rua Cristovao Colombo, Sao Joao del-Rei, MG", 0.65, True, "texto_truncado; cidade inferida"),
    "sjd-102": ("incendio_fumaca", "Veterinarios se mobilizam para socorrer animais atingidos pelos incendios na Serra de Sao Jose.", "Serra de Sao Jose, Sao Joao del-Rei, MG", 0.80, False, "desdobramento de incendio"),
    "sjd-103": ("nenhum", "Empate do Athletic com a Ponte Preta; conteudo esportivo.", None, 0.98, False, ""),
    "sjd-104": ("nenhum", "Aecio Neves reassume presidencia do PSDB; conteudo politico nacional.", None, 0.98, False, ""),
    "sjd-105": ("nenhum", "Paroquia esclarece uso de fogos na procissao do Jubileu; conteudo institucional.", "Santuario do Senhor Bom Jesus de Matosinhos, Sao Joao del-Rei, MG", 0.85, False, ""),
    "sjd-106": ("nenhum", "Piada sobre guia turistico; conteudo de humor.", None, 0.98, False, ""),
    "sjd-107": ("nenhum", "Alerta pessoal sobre surto de dengue durante o carnaval; sem local ou evento especifico.", None, 0.70, True, "saude publica; sem local"),
    "sjd-108": ("nenhum", "Turista e preso por racismo em Tiradentes; crime sem risco fisico atual.", "Maria Fumaca, Tiradentes, MG", 0.80, False, "tipo nao coberto pela taxonomia"),
    "sjd-109": ("nenhum", "Feto e encontrado em estacao de tratamento de esgoto em Barbacena; circunstancias desconhecidas.", "Estacao de Tratamento e Esgoto, Bairro Nova Cidade, Barbacena, MG", 0.65, True, "circunstancias desconhecidas; sem alerta acionavel"),
    "sjd-110": ("assalto", "Dois homens armados invadem posto de combustiveis em Sao Joao del-Rei e roubam cerca de R$ 13 mil.", "Posto de combustiveis, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-111": ("assalto", "Casal de idosos e assaltado na madrugada na regiao da Colonia do Girola; texto truncado.", "Colonia do Girola, Sao Joao del-Rei, MG", 0.85, False, "texto_truncado"),
    "sjd-112": ("presenca_arma", "Jovem e assassinado a tiros nas proximidades do desfile do Carnaval Cultural, em Sao Joao del-Rei.", "Proximidades da avenida do desfile, Sao Joao del-Rei, MG", 0.90, False, ""),
    "sjd-113": ("violencia_fisica", "Mulher e agredida pelo companheiro no bairro Bela Vista apos discussao; autor foge.", "Bairro Bela Vista, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-114": ("assalto", "Motociclista de aplicativo tem a moto roubada sob ameaca de faca no bairro Cidade do Verde; suspeito apreendido.", "Bairro Cidade do Verde, Sao Joao del-Rei, MG", 0.95, False, ""),
    "sjd-115": ("nenhum", "Aposentadoria do juiz da 2a Vara Criminal; conteudo institucional.", None, 0.98, False, ""),
    "sjd-116": ("nenhum", "Divulgacao de areas VIP da Del Rei Expo; conteudo de entretenimento.", None, 0.98, False, ""),
    "sjd-117": ("perseguicao", "Perseguicao policial e registrada na Avenida Leite de Castro; texto truncado.", "Avenida Leite de Castro, Sao Joao del-Rei, MG", 0.75, False, "texto_truncado"),
    "sjd-118": ("via_bloqueada", "Avenida Leite de Castro fica alagada apos poucos minutos de chuva; texto truncado.", "Avenida Leite de Castro, Sao Joao del-Rei, MG", 0.80, False, "texto_truncado"),
    "sjd-119": ("nenhum", "Lei estadual libera controle de javalis; conteudo legislativo.", None, 0.95, False, ""),
    "sjd-120": ("emergencia_medica", "Homem de 73 anos morre apos cair do telhado de uma residencia na Rua Nazare Candido, Residencial Lenheiro.", "Rua Nazare Candido, Residencial Lenheiro, Sao Joao del-Rei, MG", 0.95, False, ""),
}


def main() -> None:
    items = [json.loads(line) for line in BLIND.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [item["id"] for item in items]
    if len(items) != 120:
        raise SystemExit(f"esperava 120 itens, encontrei {len(items)}")
    missing = [i for i in ids if i not in A]
    extra = [i for i in A if i not in set(ids)]
    if missing or extra:
        raise SystemExit(f"anotacoes faltando={missing} sobrando={extra}")

    out = []
    for item in items:
        tipo, descricao, endereco, confianca, revisar, observacoes = A[item["id"]]
        if tipo not in TAXONOMY:
            raise SystemExit(f"tipo invalido em {item['id']}: {tipo}")
        if not 0.0 <= confianca <= 1.0:
            raise SystemExit(f"confianca invalida em {item['id']}: {confianca}")
        fora_da_area = "fora_da_area" in observacoes
        relevante = tipo != "nenhum" and not fora_da_area
        row = {
            "id": item["id"],
            "fonte_url": item["fonte_url"],
            "fonte_data": item["fonte_data"],
            "titulo": item["titulo"],
            "conteudo_completo": item["conteudo_completo"],
            "tipo_perigo": tipo,
            "descricao": descricao,
            "endereco": endereco,
            "confianca": confianca,
            "revisar": revisar,
            "observacoes": observacoes,
            "fora_da_area": fora_da_area,
            "relevante": relevante,
        }
        out.append(row)

    with OUT_JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)

    counts = Counter(row["tipo_perigo"] for row in out)
    print("Itens anotados:", len(out))
    print("Com tipo de evento:", sum(1 for row in out if row["tipo_perigo"] != "nenhum"))
    print("Alertaveis (relevante):", sum(1 for row in out if row["relevante"]))
    print("Nao alertaveis:", sum(1 for row in out if not row["relevante"]))
    print("Fora da area:", sum(1 for row in out if row["fora_da_area"]))
    print("Para revisar:", sum(1 for row in out if row["revisar"]))
    print("Confianca media:", round(sum(row["confianca"] for row in out) / len(out), 3))
    print("Com endereco:", sum(1 for row in out if row["endereco"]))
    print("\nDistribuicao por tipo:")
    for tipo, n in counts.most_common():
        print(f"  {tipo}: {n}")
    print(f"\nGravado: {OUT_JSONL.name} e {OUT_CSV.name}")


if __name__ == "__main__":
    main()
