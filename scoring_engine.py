# scoring_engine.py

"""
Módulo de Lógica de Pontuação (Scoring) para Avaliação de Propriedades Rurais.
"""

PESOS = {
    'logistica': 0.35,
    'legal_ambiental': 0.30,
    'recursos_hidricos': 0.15,
    'agronomia': 0.10,
    'topografia': 0.10
}

JUSTIFICATIVAS_PESOS = {
    'logistica': """
    **Peso Altíssimo (35%):** A logística impacta diretamente a margem de lucro. Um frete caro pode inviabilizar a venda de commodities, tornando a fazenda uma 'ilha' produtiva sem acesso eficiente ao mercado.
    """,
    'legal_ambiental': """
    **Peso Altíssimo (30%):** Problemas de documentação (matrícula, GEO, CAR) são eliminatórios. Eles impedem financiamentos, transferências e podem gerar multas ou embargos. Um passivo ambiental é uma dívida oculta.
    """,
    'recursos_hidricos': """
    **Peso Estratégico (15%):** A água é o seguro da produção. Em anos de seca, a capacidade de irrigar não apenas salva a safra, mas permite a 'safrinha', dobrando a receita anual.
    """,
    'agronomia': """
    **Peso Manejável (10%):** A tecnologia hoje permite corrigir a maioria dos problemas de solo (acidez, fertilidade). É um problema solucionável com investimento (CAPEX) e não um impeditivo estratégico.
    """,
    'topografia': """
    **Peso Manejável (10%):** O relevo define a 'eficiência operacional'. Áreas planas permitem o uso de maquinário de grande porte, reduzindo o custo por hectare. Áreas acidentadas direcionam a vocação da fazenda para atividades específicas.
    """
}

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
    if indice_final >= 8.0:
        return "Classe A - Oportunidade Prime", "Ativo com fundamentos excepcionais e baixo risco aparente."
    elif indice_final >= 6.5:
        return "Classe B - Investimento Estratégico", "Ativo sólido com grande potencial, mas requer atenção a pontos específicos."
    elif indice_final >= 4.5:
        return "Classe C - Requer Cautela", "Ativo com desafios significativos que exigem um plano de reestruturação."
    else:
        return "Classe D - Alto Risco", "Ativo com múltiplos fatores limitantes críticos. Investimento não recomendado."

def calcular_indice_viabilidade(dados_fazenda):
    scores = {
        'logistica': score_logistica(dados_fazenda['dist_asfalto_km'], dados_fazenda['dist_silo_km']),
        'legal_ambiental': score_legal_ambiental(dados_fazenda['situacao_reserva_legal'], dados_fazenda['possui_geo_sigef']),
        'recursos_hidricos': score_recursos_hidricos(dados_fazenda['indice_pluviometrico_mm'], dados_fazenda['presenca_rio_perene']),
        'agronomia': score_agronomia(dados_fazenda['ph_solo'], dados_fazenda['teor_argila_percent']),
        'topografia': score_topografia(dados_fazenda['percentual_mecanizavel'])
    }
    indice_final = sum(scores[categoria] * peso for categoria, peso in PESOS.items())
    classe, desc_classe = classificar_ativo(indice_final)
    return indice_final, scores, classe, desc_classe
