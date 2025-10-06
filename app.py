# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import find_all_nearest_pois, find_nearest_hub, get_clima_data

# --- Configuração da Página ---
st.set_page_config(page_title="AgroScore Validator 4.4", page_icon="🛰️", layout="wide")

# --- Título e Descrição ---
st.title("🛰️ AgroScore Validator 4.4")
st.markdown("Plataforma com **análise de contexto regional**, correlacionando a fazenda com os principais polos do agronegócio.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")
    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-17.79, format="%.6f") # Coordenadas perto de Rio Verde para exemplo
    longitude = st.number_input("Longitude da Sede", value=-50.93, format="%.6f")

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    st.info("As distâncias e o índice pluviométrico serão preenchidos automaticamente.")
    dist_asfalto_km = st.number_input("Distância da Rodovia (km)", min_value=0.0, value=25.0, key="dist_rodovia")
    dist_silo_km = st.number_input("Distância do Armazém Graneleiro (km)", min_value=0.0, value=60.0, key="dist_silo")

    st.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
    situacao_reserva_legal = st.selectbox("Situação da Reserva Legal (CAR)", ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo'])
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)
    
    st.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
    st.text_input("Índice Pluviométrico Médio Anual (mm)", "Será buscado automaticamente...", disabled=True)
    presenca_rio_perene = st.checkbox("Possui Rio Perene na propriedade?", value=True)

    st.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
    ph_solo = st.slider("pH médio do Solo", 3.0, 9.0, 5.8, 0.1)
    teor_argila_percent = st.slider("Teor de Argila do Solo (%)", 5, 70, 30)
    st.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
    percentual_mecanizavel = st.slider("Área Mecanizável da Fazenda (%)", 0, 100, 85)
    
    analisar = st.button("Analisar Viabilidade", type="primary")

# --- Painel Principal de Resultados ---
if analisar:
    all_pois, hub, clima_data = None, None, None
    with st.spinner("Buscando dados geográficos, logísticos e climáticos..."):
        all_pois = find_all_nearest_pois(latitude, longitude, return_coords=True)
        hub = find_nearest_hub(latitude, longitude)
        clima_data = get_clima_data(latitude, longitude)

    if clima_data is None or all_pois is None or hub is None:
        st.error("A análise foi interrompida porque não foi possível obter todos os dados automáticos. Verifique as mensagens de erro acima e tente novamente.")
        st.stop()

    dist_rodovia_final = all_pois['rodovia']['distancia']
    dist_silo_final = all_pois['silo']['distancia']
    
    dados_fazenda = {
        'dist_asfalto_km': dist_rodovia_final, 'dist_silo_km': dist_silo_final,
        'situacao_reserva_legal': situacao_reserva_legal, 'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': clima_data,
        'presenca_rio_perene': presenca_rio_perene,
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
            st.metric(label="Média Anual de Chuva (30 anos)", value=f"{clima_data} mm")
        with col2:
            st.subheader(f"Classificação do Ativo: {classe}")
            st.info(desc_classe)
        
        # MUDANÇA AQUI: Adicionamos o card de contexto regional
        st.divider()
        st.subheader("Contexto Regional")
        st.info(f"📍 A fazenda está a aproximadamente **{hub['distancia']:.0f} km** do polo regional **{hub['nome']}**, um dos principais centros do agronegócio no Brasil.")

        st.divider()
        st.subheader("Pontuações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))
            
    with tab2:
        # O mapa continua igual, mas agora exibirá o marcador do Polo Agro
        st.subheader("Análise Geográfica e Logística")
        farm_coords = (latitude, longitude)
        m = folium.Map(location=farm_coords, zoom_start=9)
        folium.Marker(farm_coords, popup=f"📍 **{nome_fazenda}**", tooltip="Local da Fazenda", icon=folium.Icon(color='blue', icon='home', prefix='fa')).add_to(m)
        if hub and hub.get('coords'):
            folium.Marker(hub['coords'], popup=f"🏭 **Polo Agro**: {hub['nome']} ({hub['distancia']:.1f} km)", tooltip="Polo Agro Mais Próximo", icon=folium.Icon(color='purple', icon='star', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, hub['coords']], color='purple', weight=3, opacity=0.8, tooltip=f"Distância ao Polo: {hub['distancia']:.1f} km").add_to(m)
        if all_pois and all_pois['silo'].get('coords'):
            folium.Marker(all_pois['silo']['coords'], popup=f"📦 **Armazém/Silo**: {all_pois['silo']['nome']} ({all_pois['silo']['distancia']:.1f} km)", tooltip="Armazém/Silo Mais Próximo", icon=folium.Icon(color='orange', icon='industry', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, all_pois['silo']['coords']], color='yellow', weight=3, opacity=0.8, tooltip=f"Distância ao Armazém: {all_pois['silo']['distancia']:.1f} km").add_to(m)
        if all_pois and all_pois['rodovia'].get('coords'):
            folium.Marker(all_pois['rodovia']['coords'], popup=f"🛣️ **Rodovia**: {all_pois['rodovia']['nome']} ({all_pois['rodovia']['distancia']:.1f} km)", tooltip="Rodovia Mais Próxima", icon=folium.Icon(color='red', icon='road', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, all_pois['rodovia']['coords']], color='darkorange', weight=3, opacity=0.8, tooltip=f"Distância à Rodovia: {all_pois['rodovia']['distancia']:.1f} km").add_to(m)
        if all_pois and all_pois['cidade'].get('coords'):
            folium.Marker(all_pois['cidade']['coords'], popup=f"🏙️ **Cidade**: {all_pois['cidade']['nome']} ({all_pois['cidade']['distancia']:.1f} km)", tooltip="Cidade Mais Próxima", icon=folium.Icon(color='lightgray', icon='building', prefix='fa')).add_to(m)
            folium.PolyLine(locations=[farm_coords, all_pois['cidade']['coords']], color='gray', weight=3, opacity=0.8, tooltip=f"Distância à Cidade: {all_pois['cidade']['distancia']:.1f} km").add_to(m)
        folium_static(m, width=950, height=600)

    with tab3:
        # ... (Esta aba continua igual)
        st.subheader("Argumentação Sobre os Pesos da Análise")
        st.info("A metodologia de pesos reflete a realidade do investimento em ativos rurais...")
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)
else:
    st.info("Preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade' para um diagnóstico completo.")
