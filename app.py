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

st.set_page_config(page_title="AgroScore Validator", page_icon="🛰️", layout="wide")

st.title("🛰️ AgroScore Validator")
st.markdown("Plataforma com **banco de dados de rodovias integrado** e análise robusta de dados geográficos.")

with st.sidebar:
    st.header("Dados da Propriedade")
    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude", value=-17.79, format="%.6f")
    longitude = st.number_input("Longitude", value=-50.93, format="%.6f")
    st.info("Logística, Clima e Solo serão preenchidos automaticamente.")
    st.text_input("Distância da Rodovia (km)", "Automático...", disabled=True)
    st.text_input("Distância do Armazém (km)", "Automático...", disabled=True)
    st.text_input("Índice Pluviométrico (mm)", "Automático...", disabled=True)
    st.text_input("pH do Solo", "Automático...", disabled=True)
    st.text_input("Teor de Argila (%)", "Automático...", disabled=True)
    
    st.subheader("Dados Manuais")
    situacao_reserva_legal = st.selectbox("Situação Legal (CAR)", ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo'])
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)
    presenca_rio_perene = st.checkbox("Possui Rio Perene?", value=True)
    percentual_mecanizavel = st.slider("Área Mecanizável (%)", 0, 100, 85)
    
    analisar = st.button("Analisar Viabilidade", type="primary")

if analisar:
    with st.spinner("Buscando e processando dados..."):
        highway_success, highway_data = find_nearest_highway_from_db(latitude, longitude)
        pois_success, local_pois = find_local_pois(latitude, longitude, return_coords=True)
        hub_success, hub = find_nearest_hub(latitude, longitude)
        clima_success, clima_data = get_clima_data(latitude, longitude)
        soil_success, soil_data = get_soil_data(latitude, longitude)

    if not all([clima_success, pois_success, hub_success, highway_success, soil_success]):
        st.error("Análise interrompida. Verifique os erros e tente novamente:")
        if not highway_success: st.warning(f"Rodovias: {highway_data}")
        if not pois_success: st.warning(f"Logística Local: {local_pois}")
        if not clima_success: st.warning(f"Clima: {clima_data}")
        st.stop()
    
    st.success("Busca de dados automáticos concluída com sucesso!")

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
    tab1, tab2, tab3 = st.tabs(["📊 Resumo", "🗺️ Mapa", "⚖️ Pesos"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Índice de Viabilidade", f"{indice_final:.2f} / 10")
        with col2: st.metric("Média de Chuva", f"{clima_data} mm")
        with col3:
            st.metric("pH do Solo", f"{soil_data['ph']:.2f}")
            st.metric("Argila no Solo", f"{soil_data['clay']:.1f}%")
        st.info(f"**Classificação: {classe}** - {desc_classe}")
        st.info(f"📍 Proximidade do Polo Agro: **{hub['distancia']:.0f} km** de **{hub['nome']}**.")
        st.divider()
        st.subheader("Pontuações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))
            
    with tab2:
        m = folium.Map(location=[latitude, longitude], zoom_start=9)
        folium.Marker([latitude, longitude], popup=f"📍 **{nome_fazenda}**", tooltip="Fazenda", icon=folium.Icon(color='blue', icon='home', prefix='fa')).add_to(m)
        if hub and hub.get('coords'):
            folium.Marker(hub['coords'], popup=f"🏭 **Polo**: {hub['nome']}", icon=folium.Icon(color='purple', icon='star', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[(latitude, longitude), hub['coords']], color='purple', tooltip=f"Polo: {hub['distancia']:.1f} km").add_to(m)
        if local_pois and local_pois.get('silo', {}).get('coords'):
            folium.Marker(local_pois['silo']['coords'], popup=f"📦 **Silo**: {local_pois['silo']['nome']}", icon=folium.Icon(color='orange', icon='industry', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[(latitude, longitude), local_pois['silo']['coords']], color='yellow', tooltip=f"Silo: {local_pois['silo']['distancia']:.1f} km").add_to(m)
        if highway_data and highway_data.get('coords'):
            folium.Marker(highway_data['coords'], popup=f"🛣️ **{highway_data['nome']}**", icon=folium.Icon(color='red', icon='road', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[(latitude, longitude), highway_data['coords']], color='darkorange', tooltip=f"Rodovia: {highway_data['distancia']:.1f} km").add_to(m)
        if local_pois and local_pois.get('cidade', {}).get('coords'):
            folium.Marker(local_pois['cidade']['coords'], popup=f"🏙️ **Cidade**: {local_pois['cidade']['nome']}", icon=folium.Icon(color='lightgray', icon='building', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[(latitude, longitude), local_pois['cidade']['coords']], color='gray', tooltip=f"Cidade: {local_pois['cidade']['distancia']:.1f} km").add_to(m)
        folium_static(m, width=950, height=600)

    with tab3:
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} ({int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)
else:
    st.info("Preencha os dados da propriedade e clique em 'Analisar Viabilidade'.")
