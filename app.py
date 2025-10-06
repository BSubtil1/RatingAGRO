# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import find_all_nearest_pois, find_nearest_hub

# --- Configuração da Página ---
st.set_page_config(page_title="AgroScore Validator 4.0", page_icon="🗺️", layout="wide")

# --- Título e Descrição ---
st.title("🗺️ AgroScore Validator 4.0")
st.markdown("Plataforma com **análise e mapa logístico integrados**. Preencha os dados e clique em 'Analisar Viabilidade' para um diagnóstico completo.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")

    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-16.6869, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-49.2648, format="%.6f")

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    st.info("As distâncias serão calculadas automaticamente ao clicar em 'Analisar'.")
    
    dist_asfalto_km = st.number_input("Distância da Rodovia (km)", min_value=0.0, value=25.0, key="dist_rodovia")
    dist_silo_km = st.number_input("Distância do Armazém Graneleiro (km)", min_value=0.0, value=60.0, key="dist_silo")

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

    analisar = st.button("Analisar Viabilidade", type="primary")

# --- Painel Principal de Resultados ---
if analisar:
    with st.spinner("Buscando dados geográficos e logísticos..."):
        all_pois = find_all_nearest_pois(latitude, longitude, return_coords=True)
        hub = find_nearest_hub(latitude, longitude)
    
    if all_pois and hub:
        st.session_state.dist_rodovia = all_pois['rodovia']['distancia']
        st.session_state.dist_silo = all_pois['silo']['distancia']
        
        dados_fazenda = {
            'dist_asfalto_km': st.session_state.dist_rodovia, 
            'dist_silo_km': st.session_state.dist_silo,
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
            
            farm_coords = (latitude, longitude)
            m = folium.Map(location=farm_coords, zoom_start=9)
            
            folium.Marker(farm_coords, popup=f"📍 **{nome_fazenda}**", 
                          tooltip="Local da Fazenda", icon=folium.Icon(color='blue', icon='home', prefix='fa')).add_to(m)

            if hub and hub['coords']:
                folium.Marker(hub['coords'], popup=f"🏭 **Polo Agro**: {hub['nome']} ({hub['distancia']:.1f} km)",
                              tooltip="Polo Agro Mais Próximo", icon=folium.Icon(color='purple', icon='star', prefix='fa')).add_to(m)
                folium.PolyLine(locations=[farm_coords, hub['coords']], color='purple', weight=3, opacity=0.8,
                                tooltip=f"Distância ao Polo: {hub['distancia']:.1f} km").add_to(m)

            if all_pois['silo']['coords']:
                folium.Marker(all_pois['silo']['coords'], popup=f"📦 **Armazém/Silo**: {all_pois['silo']['nome']} ({all_pois['silo']['distancia']:.1f} km)",
                              tooltip="Armazém/Silo Mais Próximo", icon=folium.Icon(color='orange', icon='industry', prefix='fa')).add_to(m)
                folium.PolyLine(locations=[farm_coords, all_pois['silo']['coords']], color='yellow', weight=3, opacity=0.8,
                                tooltip=f"Distância ao Armazém: {all_pois['silo']['distancia']:.1f} km").add_to(m)

            if all_pois['rodovia']['coords']:
                folium.Marker(all_pois['rodovia']['coords'], popup=f"🛣️ **Rodovia**: {all_pois['rodovia']['nome']} ({all_pois['rodovia']['distancia']:.1f} km)",
                              tooltip="Rodovia Mais Próxima", icon=folium.Icon(color='red', icon='road', prefix='fa')).add_to(m)
                folium.PolyLine(locations=[farm_coords, all_pois['rodovia']['coords']], color='darkorange', weight=3, opacity=0.8,
                                tooltip=f"Distância à Rodovia: {all_pois['rodovia']['distancia']:.1f} km").add_to(m)

            if all_pois['cidade']['coords']:
                folium.Marker(all_pois['cidade']['coords'], popup=f"🏙️ **Cidade**: {all_pois['cidade']['nome']} ({all_pois['cidade']['distancia']:.1f} km)",
                              tooltip="Cidade Mais Próxima", icon=folium.Icon(color='lightgray', icon='building', prefix='fa')).add_to(m)
                folium.PolyLine(locations=[farm_coords, all_pois['cidade']['coords']], color='gray', weight=3, opacity=0.8,
                                tooltip=f"Distância à Cidade: {all_pois['cidade']['distancia']:.1f} km").add_to(m)
            
            folium_static(m, width=950, height=600)

            st.markdown("#### Distâncias Calculadas:")
            st.success(f"🛣️ **Rodovia mais próxima:** Aprox. **{all_pois['rodovia']['distancia']:.1f} km**")
            st.success(f"🏙️ **Cidade/Vila mais próxima:** {all_pois['cidade']['nome']} (aprox. **{all_pois['cidade']['distancia']:.1f} km**)")
            st.success(f"📦 **Armazém/Silo mais próximo:** {all_pois['silo']['nome']} (aprox. **{all_pois['silo']['distancia']:.1f} km**)")
            st.success(f"🏭 **Polo de Agronegócio mais próximo:** {hub['nome']} (aprox. **{hub['distancia']:.1f} km**)")
            
        with tab3:
            st.subheader("Argumentação Sobre os Pesos da Análise")
            st.info("A metodologia de pesos reflete a realidade do investimento em ativos rurais...")
            for categoria, just in JUSTIFICATIVAS_PESOS.items():
                with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                    st.markdown(just)
    else:
        st.error("Não foi possível buscar os dados geográficos. Verifique a conexão ou as coordenadas e tente novamente.")

else:
    st.info("Preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade' para um diagnóstico completo.")
