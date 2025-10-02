# scoring_engine.py

"""
Módulo de Lógica de Pontuação (Scoring) para Avaliação de Propriedades Rurais.
Este motor calcula um "Índice de Viabilidade" com base em critérios ponderados.
"""

# Definição dos pesos para cada categoria, conforme nossa discussão.
# Logística e Legal/Fundiário são os mais críticos.
PESOS = {
    'logistica': 0.35,
    'legal_ambiental': 0.30,
    'recursos_hidricos': 0.15,
    'agronomia': 0.10,
    'topografia': 0.10
}

def score_logistica(dist_asfalto_km, dist_silo_km):
    """
    Calcula a pontuação de logística. Quanto menor a distância, maior a pontuação.
    Penaliza fortemente distâncias longas em estradas de terra.
    """
    score = 10
    if dist_asfalto_km > 50:
        score -= 5
    elif dist_asfalto_km > 20:
        score -= 3

    if dist_silo_km > 100:
        score -= 5
    elif dist_silo_km > 50:
        score -= 2
    
    return max(0, score) # Garante que a nota não seja negativa

def score_legal_ambiental(situacao_reserva_legal, possui_geo_sigef):
    """
    Calcula a pontuação legal. Documentação incompleta é um fator eliminatório.
    """
    score = 10
    if situacao_reserva_legal == 'Pendente com passivo':
        score = 2 # Penalidade máxima, pois gera custos e insegurança
    elif situacao_reserva_legal == 'Averbada, mas precisa de averiguação':
        score = 7

    if not possui_geo_sigef:
        score = 0 # Fator eliminatório. Sem GEO, não há financiamento nem venda segura.

    return score

def score_recursos_hidricos(indice_pluviometrico_mm, presenca_rio_perene):
    """
    Calcula a pontuação de água. Essencial para segurança contra secas.
    """
    score = 0
    if indice_pluviometrico_mm > 1400:
        score = 8
    elif indice_pluviometrico_mm > 1100:
        score = 5
    else:
        score = 2

    if presenca_rio_perene:
        score += 2 # Bônus por ter água o ano todo, crucial para irrigação
    
    return min(10, score) # Garante que a nota não passe de 10

def score_agronomia(ph_solo, teor_argila_percent):
    """
    Calcula a pontuação agronômica. Fator manejável, mas impacta o custo inicial.
    """
    score = 10
    # Penaliza solos muito ácidos ou muito básicos
    if not (5.0 < ph_solo < 6.5):
        score -= 3
    
    # Penaliza solos com baixa ou excessiva argila para grãos
    if not (15 < teor_argila_percent < 40):
        score -= 4

    return max(0, score)

def score_topografia(percentual_mecanizavel):
    """
    Calcula a pontuação de topografia. Impacta a eficiência operacional.
    """
    if percentual_mecanizavel >= 80:
        return 10
    elif percentual_mecanizavel >= 60:
        return 7
    elif percentual_mecanizavel >= 40:
        return 4
    else:
        return 1

def calcular_indice_viabilidade(dados_fazenda):
    """
    Função principal que orquestra todos os cálculos e aplica os pesos.
    """
    scores = {
        'logistica': score_logistica(
            dados_fazenda['dist_asfalto_km'],
            dados_fazenda['dist_silo_km']
        ),
        'legal_ambiental': score_legal_ambiental(
            dados_fazenda['situacao_reserva_legal'],
            dados_fazenda['possui_geo_sigef']
        ),
        'recursos_hidricos': score_recursos_hidricos(
            dados_fazenda['indice_pluviometrico_mm'],
            dados_fazenda['presenca_rio_perene']
        ),
        'agronomia': score_agronomia(
            dados_fazenda['ph_solo'],
            dados_fazenda['teor_argila_percent']
        ),
        'topografia': score_topografia(
            dados_fazenda['percentual_mecanizavel']
        )
    }

    indice_final = 0
    for categoria, peso in PESOS.items():
        indice_final += scores[categoria] * peso
    
    return indice_final, scores
    # scoring_engine.py

"""
Módulo de Lógica de Pontuação (Scoring) para Avaliação de Propriedades Rurais.
Versão 2.0: Adiciona classificação de ativos e justificativas.
"""

# Definição dos pesos para cada categoria.
PESOS = {
    'logistica': 0.35,
    'legal_ambiental': 0.30,
    'recursos_hidricos': 0.15,
    'agronomia': 0.10,
    'topografia': 0.10
}

# Justificativas dos pesos para explicar a metodologia no app.
JUSTIFICATIVAS_PESOS = {
    'logistica': """
    **Peso Altíssimo (35%):** A logística é o fator que mais impacta a margem de lucro.
    Um frete caro (distância, estradas ruins) pode inviabilizar a venda de commodities de baixo valor agregado,
    tornando a fazenda uma 'ilha' produtiva sem acesso eficiente ao mercado. É um custo fixo que corrói o resultado anualmente.
    """,
    'legal_ambiental': """
    **Peso Altíssimo (30%):** Problemas de documentação (matrícula, GEO, CAR) são eliminatórios.
    Eles impedem financiamentos, transferências e podem gerar multas milionárias ou embargos.
    Um passivo ambiental é uma dívida oculta que o comprador herda integralmente.
    """,
    'recursos_hidricos': """
    **Peso Estratégico (15%):** A água é o seguro da produção. Em anos de seca (cada vez mais comuns),
    a capacidade de irrigar não apenas salva a safra, mas permite a 'safrinha', dobrando a receita anual.
    A outorga de água é um dos ativos mais valiosos de uma propriedade.
    """,
    'agronomia': """
    **Peso Manejável (10%):** A tecnologia hoje permite corrigir a grande maioria dos problemas de solo (acidez, fertilidade).
    Embora importante, é um problema solucionável com investimento (CAPEX). O app trata isso mais como um custo a ser calculado
    do que um impeditivo estratégico.
    """,
    'topografia': """
    **Peso Manejável (10%):** O relevo define a 'eficiência operacional'. Áreas planas permitem o uso de maquinário de grande porte,
    reduzindo o custo por hectare. Áreas acidentadas não são ruins, mas direcionam a vocação da fazenda para
    atividades específicas (pecuária, café de montanha, silvicultura).
    """
}

# ... (todas as funções score_logistica, score_legal_ambiental, etc., continuam exatamente as mesmas) ...
def score_logistica(dist_asfalto_km, dist_silo_km):
    score = 10
    if dist_asfalto_km > 50: score -= 5
    elif dist_asfalto_km > 20: score -= 3
    if dist_silo_km > 100: score -= 5
    elif dist_silo_km > 50: score -= 2
    return max(0, score)

def score_legal_ambiental(situacao_reserva_legal, possui_geo_sigef):
    score = 10
    if situacao_reserva_legal == 'Pendente com passivo': score = 2
    elif situacao_reserva_legal == 'Averbada, mas precisa de averiguação': score = 7
    if not possui_geo_sigef: score = 0
    return score

def score_recursos_hidricos(indice_pluviometrico_mm, presenca_rio_perene):
    score = 0
    if indice_pluviometrico_mm > 1400: score = 8
    elif indice_pluviometrico_mm > 1100: score = 5
    else: score = 2
    if presenca_rio_perene: score += 2
    return min(10, score)

def score_agronomia(ph_solo, teor_argila_percent):
    score = 10
    if not (5.0 < ph_solo < 6.5): score -= 3
    if not (15 < teor_argila_percent < 40): score -= 4
    return max(0, score)

def score_topografia(percentual_mecanizavel):
    if percentual_mecanizavel >= 80: return 10
    elif percentual_mecanizavel >= 60: return 7
    elif percentual_mecanizavel >= 40: return 4
    else: return 1

def classificar_ativo(indice_final):
    """
    Cria um critério de pontuação para classificar a fazenda analisada.
    """
    if indice_final >= 8.0:
        return "Classe A - Oportunidade Prime", "Ativo com fundamentos excepcionais e baixo risco aparente. Altamente recomendado."
    elif indice_final >= 6.5:
        return "Classe B - Investimento Estratégico", "Ativo sólido com grande potencial, mas requer atenção a pontos específicos."
    elif indice_final >= 4.5:
        return "Classe C - Requer Cautela", "Ativo com desafios significativos. A viabilidade depende de um plano de reestruturação com alto CAPEX."
    else:
        return "Classe D - Alto Risco", "Ativo com múltiplos fatores limitantes críticos. Investimento não recomendado no cenário atual."


def calcular_indice_viabilidade(dados_fazenda):
    """
    Função principal que orquestra todos os cálculos e aplica os pesos.
    """
    scores = {
        'logistica': score_logistica(
            dados_fazenda['dist_asfalto_km'],
            dados_fazenda['dist_silo_km']
        ),
        'legal_ambiental': score_legal_ambiental(
            dados_fazenda['situacao_reserva_legal'],
            dados_fazenda['possui_geo_sigef']
        ),
        'recursos_hidricos': score_recursos_hidricos(
            dados_fazenda['indice_pluviometrico_mm'],
            dados_fazenda['presenca_rio_perene']
        ),
        'agronomia': score_agronomia(
            dados_fazenda['ph_solo'],
            dados_fazenda['teor_argila_percent']
        ),
        'topografia': score_topografia(
            dados_fazenda['percentual_mecanizavel']
        )
    }

    indice_final = 0
    for categoria, peso in PESOS.items():
        indice_final += scores[categoria] * peso
    
    classe, desc_classe = classificar_ativo(indice_final)
    
    return indice_final, scores, classe, desc_classe
