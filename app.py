# app.py

import streamlit as st
import pandas as pd
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import (
    find_nearest_poi, find_nearest_hub,
    QUERY_RODOVIA, QUERY_ARMAZEM, QUERY_CIDADE
)

# --- Configuração da Página ---
st.set_page_config(
    page_title="AgroScore Validator 3.0",
    page_icon="🛰️",
    layout="wide"
)

# --- Título e Descrição ---
st.title("🛰️ AgroScore Validator 3.0")
st.markdown("Plataforma com **busca automática de logística**. Insira as coordenadas da fazenda e clique em 'Buscar Dados Geográficos' para popular os campos de distância.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")

    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-16.6869, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-49.2648, format="%.6f")

    # Botão para iniciar a busca geográfica
    if st.button("Buscar Dados Geográficos", type="primary"):
        with st.spinner("Buscando rodovias, cidades e armazéns... Isso pode levar alguns segundos."):
            st.session_state.rodovia = find_nearest_poi(latitude, longitude, QUERY_RODOVIA)
            st.session_state.cidade = find_nearest_poi(latitude, longitude, QUERY_CIDADE)
            st.session_state.armazem = find_nearest_poi(latitude, longitude, QUERY_ARMAZEM)
            st.session_state.hub = find_nearest_hub(latitude, longitude)

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    # Usamos o st.session_state para guardar os valores encontrados
    dist_asfalto_km = st.number_input(
        "Distância da Rodovia (km)", 
        min_value=0, 
        value=st.session_state.get('rodovia', {}).get('distancia', 25)
    )
    dist_silo_km = st.number_input(
        "Distância do Armazém (km)",
        min_value=0, 
        value=st.session_state.get('armazem', {}).get('distancia', 60)
    )

    # ... O restante dos inputs continua igual ...
    st.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
    situacao_reserva_legal = st.selectbox("Situação da Reserva Legal (CAR)", ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo'])
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)

    st.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
    indice_pluviometrico_mm = st.slider("Índice Pluviométrico Médio Anual (mm)", 600, 2500, 1500)
    presenca_rio_perene = st.checkbox("Possui Rio Perene na propriedade?", value=True)

    st.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
    ph_solo = st.slider("pH médio do Solo", 3.0, 9.0, 5.8, 0.1)
    teor_argila_percent = st.slider("Teor de Argila do Solo (%)", 5, 70, 30)

    st.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
    percentual_mecanizavel = st.slider("Área Mecanizável da Fazenda (%)", 0, 100, 85)

    analisar = st.button("Analisar Viabilidade")

# --- Painel Principal de Resultados ---
if analisar:
    # Coleta dos dados para o motor de análise
    dados_fazenda = {
        'dist_asfalto_km': dist_asfalto_km, 'dist_silo_km': dist_silo_km,
        # ... o resto dos dados ...
        'situacao_reserva_legal': situacao_reserva_legal, 'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': indice_pluviometrico_mm, 'presenca_rio_perene': presenca_rio_perene,
        'ph_solo': ph_solo, 'teor_argila_percent': teor_argila_percent,
        'percentual_mecanizavel': percentual_mecanizavel
    }
    indice_final, scores_detalhados, classe, desc_classe = calcular_indice_viabilidade(dados_fazenda)

    st.header(f"Resultados da Análise: {nome_fazenda}")

    tab1, tab2, tab3 = st.tabs(["📊 Resumo Geral", "🗺️ Detalhes Geográficos", "⚖️ Justificativa dos Pesos"])

    with tab1:
        st.subheader("Compilado da Avaliação")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Índice de Viabilidade Final", value=f"{indice_final:.2f} / 10")
        with col2:
            st.subheader(f"Classificação do Ativo: {classe}")
            st.info(desc_classe)
        st.divider()
        st.subheader("Pontuações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))

    with tab2:
        st.subheader("Análise Geográfica e Logística")
        st.map(pd.DataFrame({'lat': [latitude], 'lon': [longitude]}), zoom=12)
        
        st.markdown("#### Distâncias Calculadas:")
        if 'rodovia' in st.session_state:
            st.success(f"🛣️ **Rodovia mais próxima:** Aprox. **{st.session_state.rodovia['distancia']} km**")
        if 'cidade' in st.session_state:
            st.success(f"🏙️ **Cidade/Vila mais próxima:** {st.session_state.cidade['nome']} (aprox. **{st.session_state.cidade['distancia']} km**)")
        if 'armazem' in st.session_state:
            st.success(f"📦 **Armazém/Silo mais próximo:** Aprox. **{st.session_state.armazem['distancia']} km**")
        if 'hub' in st.session_state:
            st.success(f"🏭 **Polo de Agronegócio mais próximo:** {st.session_state.hub['nome']} (aprox. **{st.session_state.hub['distancia']} km**)")

    with tab3:
        st.subheader("Argumentação Sobre os Pesos da Análise")
        st.info("A metodologia de pesos reflete a realidade do investimento em ativos rurais...")
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)
else:
    st.info("Insira as coordenadas da fazenda e clique em 'Buscar Dados Geográficos' na barra lateral para começar.")
