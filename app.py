# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import (
    find_nearest_highway_from_db, find_local_pois, 
    find_nearest_hub, get_clima_data, get_soil_data
)

# --- Configuração da Página ---
st.set_page_config(page_title="AgroScore Validator 5.1", page_icon="🛰️", layout="wide")

# --- Título e Descrição ---
st.title("🛰️ AgroScore Validator 5.1")
st.markdown("Plataforma com **banco de dados de rodovias integrado** e análise robusta de dados geográficos.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")
    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-17.79, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-50.93, format="%.6f")

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    st.info("Todos os dados de Logística, Clima e Solo serão preenchidos automaticamente.")
    st.text_input("Distância da Rodovia Pavimentada (km)", "Automático...", disabled=True)
    st.text_input("Distância do Armazém Graneleiro (km)", "Automático...", disabled=True)
    
    st.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
    situacao_reserva_legal = st.selectbox("Situação da Reserva Legal (CAR)", ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo'])
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)
    st.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
    st.text_input("Índice Pluviométrico Médio (mm)", "Automático...", disabled=True)
    presenca_rio_perene = st.checkbox("Possui Rio Perene na propriedade?", value=True)
    st.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
    st.text_input("pH do Solo (0-20cm)", "Automático...", disabled=True)
    st.text_input("Teor de Argila do Solo (0-20cm)", "Automático...", disabled=True)
    st.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
    percentual_mecanizavel = st.slider("Área Mecanizável da Fazenda (%)", 0, 100, 85)
    
    analisar = st.button("Analisar Viabilidade", type="primary")

# --- Painel Principal de Resultados ---
if analisar:
    with st.spinner("Buscando e processando dados..."):
        highway_success, highway_data = find_nearest_highway_from_db(latitude, longitude)
        pois_success, local_pois = find_local_pois(latitude, longitude, return_coords=True)
        hub_success, hub = find_nearest_hub(latitude, longitude)
        clima_success, clima_data = get_clima_data(latitude, longitude)
        soil_success, soil_data = get_soil_data(latitude, longitude)

    # A análise de solo não interrompe mais, mas as outras sim, se falharem.
    if not all([clima_success, pois_success, hub_success, highway_success]):
        st.error("A análise foi interrompida. Verifique as mensagens de erro e tente novamente:")
        if not highway_success: st.warning(f"Rodovias: {highway_data}")
        if not pois_success: st.warning(f"Logística Local: {local_pois}")
        if not clima_success: st.warning(f"Clima: {clima_data}")
        st.stop()
    
    st.success("Busca de dados automáticos concluída com sucesso!")

    # CORREÇÃO APLICADA AQUI: Garantindo que todas as chaves estão corretas
    dados_fazenda = {
        'dist_asfalto_km': highway_data['distancia'], 
        'dist_silo_km': local_pois['silo']['distancia'],
        'situacao_reserva_legal': situacao_reserva_legal, 
        'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': clima_data,
        'presenca_rio_perene': presenca_rio_perene,
        'ph_solo': soil_data['ph'],
        'teor_argila_percent': soil_data['clay'],
        'percentual_mecanizavel': percentual_mecanizavel
    }
    
    indice_final, scores_detalhados, classe, desc_classe = calcular_indice_viabilidade(dados_fazenda)
    
    st.header(f"Resultados da Análise: {nome_fazenda}")
    tab1, tab2, tab3 = st.tabs(["📊 Resumo Geral", "🗺️ Detalhes Geográficos", "⚖️ Justificativa dos Pesos"])

    with tab1:
        st.subheader("Compilado da Avaliação")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Índice de Viabilidade Final", value=f"{indice_final:.2f} / 10")
        with col2: st.metric(label="Média de Chuva (30 anos)", value=f"{clima_data} mm")
        with col3:
            st.metric(label="pH do Solo (0-20cm)", value=f"{soil_data['ph']:.2f}")
            st.metric(label="Argila no Solo (0-20cm)", value=f"{soil_data['clay']:.1f}%")
        st.info(f"**Classificação do Ativo: {classe}** - {desc_classe}")
        st.info(f"📍 A fazenda está a aproximadamente **{hub['distancia']:.0f} km** do polo regional **{hub['nome']}**.")
        st.divider()
        st.subheader("Pontouações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))
            
    with tab2:
        st.subheader("Análise Geográfica e Logística")
        farm_coords = (latitude, longitude)
        m = folium.Map(location=farm_coords, zoom_start=9)
        folium.Marker(farm_coords, popup=f"📍 **{nome_fazenda}**", tooltip="Local da Fazenda", icon=folium.Icon(color='blue', icon='home', prefix='fa')).add_to(m)
        if hub and hub.get('coords'):
            folium.Marker(hub['coords'], popup=f"🏭 **Polo Agro**: {hub['nome']} ({hub['distancia']:.1f} km)", tooltip="Polo Agro Mais Próximo", icon=folium.Icon(color='purple', icon='star', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, hub['coords']], color='purple', weight=3, opacity=0.8, tooltip=f"Distância ao Polo: {hub['distancia']:.1f} km").add_to(m)
        if local_pois and local_pois.get('silo', {}).get('coords'):
            folium.Marker(local_pois['silo']['coords'], popup=f"📦 **Armazém/Silo**: {local_pois['silo']['nome']} ({local_pois['silo']['distancia']:.1f} km)", tooltip="Armazém/Silo Mais Próximo", icon=folium.Icon(color='orange', icon='industry', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, local_pois['silo']['coords']], color='yellow', weight=3, opacity=0.8, tooltip=f"Distância ao Armazém: {local_pois['silo']['distancia']:.1f} km").add_to(m)
        if highway_data and highway_data.get('coords'):
            folium.Marker(highway_data['coords'], popup=f"🛣️ **{highway_data['nome']}**: ({highway_data['distancia']:.1f} km)", tooltip="Rodovia Pavimentada Mais Próxima", icon=folium.Icon(color='red', icon='road', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, highway_data['coords']], color='darkorange', weight=3, opacity=0.8, tooltip=f"Distância à Rodovia: {highway_data['distancia']:.1f} km").add_to(m)
        if local_pois and local_pois.get('cidade', {}).get('coords'):
            folium.Marker(local_pois['cidade']['coords'], popup=f"🏙️ **Cidade**: {local_pois['cidade']['nome']} ({local_pois['cidade']['distancia']:.1f} km)", tooltip="Cidade Mais Próxima", icon=folium.Icon(color='lightgray', icon='building', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, local_pois['cidade']['coords']], color='gray', weight=3, opacity=0.8, tooltip=f"Distância à Cidade: {local_pois['cidade']['distancia']:.1f} km").add_to(m)
        folium_static(m, width=950, height=600)

    with tab3:
        st.subheader("Argumentação Sobre os Pesos da Análise")
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)
else:
    st.info("Preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade' para um diagnóstico completo.")
