# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import find_all_nearest_pois, find_nearest_hub, get_clima_data, get_soil_data

# --- Configuração da Página ---
st.set_page_config(page_title="AgroScore Validator 4.5", page_icon="🛰️", layout="wide")

# --- Título e Descrição ---
st.title("🛰️ AgroScore Validator 4.5")
st.markdown("Plataforma com **análise de solo, clima e logística automáticas**.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")
    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-17.79, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-50.93, format="%.6f")

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    st.info("Todos os dados de Logística, Clima e Solo serão preenchidos automaticamente.")
    dist_asfalto_km = st.number_input("Distância da Rodovia (km)", min_value=0.0, value=25.0, key="dist_rodovia", disabled=True)
    dist_silo_km = st.number_input("Distância do Armazém Graneleiro (km)", min_value=0.0, value=60.0, key="dist_silo", disabled=True)

    st.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
    situacao_reserva_legal = st.selectbox("Situação da Reserva Legal (CAR)", ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo'])
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)
    
    st.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
    st.text_input("Índice Pluviométrico Médio (mm)", "Automático...", disabled=True)
    presenca_rio_perene = st.checkbox("Possui Rio Perene na propriedade?", value=True)

    # MUDANÇA AQUI: Removemos os sliders de pH e Argila
    st.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
    st.text_input("pH do Solo", "Automático...", disabled=True)
    st.text_input("Teor de Argila do Solo (%)", "Automático...", disabled=True)

    st.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
    percentual_mecanizavel = st.slider("Área Mecanizável da Fazenda (%)", 0, 100, 85)
    
    analisar = st.button("Analisar Viabilidade", type="primary")

# --- Painel Principal de Resultados ---
if analisar:
    all_pois, hub, clima_data, soil_data = None, None, None, None
    with st.spinner("Buscando dados de solo, clima, geografia e logística... (Pode levar até 1 minuto)"):
        all_pois = find_all_nearest_pois(latitude, longitude, return_coords=True)
        hub = find_nearest_hub(latitude, longitude)
        clima_data = get_clima_data(latitude, longitude)
        soil_data = get_soil_data(latitude, longitude)

    if any(data is None for data in [clima_data, all_pois, hub, soil_data]):
        st.error("A análise foi interrompida porque não foi possível obter todos os dados automáticos. Verifique as mensagens de erro e tente novamente.")
        st.stop()
    
    dados_fazenda = {
        'dist_asfalto_km': all_pois['rodovia']['distancia'], 
        'dist_silo_km': all_pois['silo']['distancia'],
        'situacao_reserva_legal': situacao_reserva_legal, 'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': clima_data,
        'presenca_rio_perene': presenca_rio_perene,
        'ph_solo': soil_data['ph'], # Usa dado automático
        'teor_argila_percent': soil_data['clay'], # Usa dado automático
        'percentual_mecanizavel': percentual_mecanizavel
    }
    
    indice_final, scores_detalhados, classe, desc_classe = calcular_indice_viabilidade(dados_fazenda)
    
    st.header(f"Resultados da Análise: {nome_fazenda}")
    tab1, tab2, tab3 = st.tabs(["📊 Resumo Geral", "🗺️ Detalhes Geográficos", "⚖️ Justificativa dos Pesos"])

    with tab1:
        st.subheader("Compilado da Avaliação")
        col1, col2, col3 = st.columns(3) # Adicionamos uma terceira coluna
        with col1:
            st.metric(label="Índice de Viabilidade Final", value=f"{indice_final:.2f} / 10")
        with col2:
            st.metric(label="Média de Chuva (30 anos)", value=f"{clima_data} mm")
        with col3:
            # MUDANÇA AQUI: Exibimos o "indicador" de solo
            st.metric(label="pH do Solo (0-20cm)", value=f"{soil_data['ph']:.2f}")
            st.metric(label="Argila no Solo (0-20cm)", value=f"{soil_data['clay']:.1f}%")

        st.info(f"**Classificação do Ativo: {classe}** - {desc_classe}")
        st.info(f"📍 A fazenda está a aproximadamente **{hub['distancia']:.0f} km** do polo regional **{hub['nome']}**.")
        st.divider()

        st.subheader("Pontuações por Categoria")
        # ... (restante do código igual) ...
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))
            
    with tab2:
        # ... (mapa igual) ...
        st.subheader("Análise Geográfica e Logística")
        # ...
        folium_static(...)
        
    with tab3:
        # ... (justificativas igual) ...
        st.subheader("Argumentação Sobre os Pesos da Análise")
        # ...
else:
    st.info("Preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade' para um diagnóstico completo.")

# Para o código completo das abas 2 e 3 e o resto, use a versão anterior, pois eles não mudam.
# Colei apenas as partes que foram alteradas para manter a resposta mais curta.
# Para garantir, vou colocar o código completo abaixo, já que a aba 2 e 3 não apareceram.
