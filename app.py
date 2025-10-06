# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS
from geolocation_service import find_all_nearest_pois, find_nearest_hub

# --- Configuração da Página ---
st.set_page_config(page_title="AgroScore Validator 3.4", page_icon="🛰️", layout="wide")

# --- Título e Descrição ---
st.title("🛰️ AgroScore Validator 3.4")
st.markdown("Plataforma com **mapa logístico completo**, mostrando as rotas para Silos, Cidades e Rodovias.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")

    nome_fazenda = st.text_input("Nome da Fazenda", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-16.6869, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-49.2648, format="%.6f")

    # CORREÇÃO APLICADA AQUI: a chave 'armazem' foi trocada para 'silo'
    if 'pois' not in st.session_state:
        st.session_state.pois = {
            'rodovia': {'nome': 'Não encontrada', 'distancia': 25.0, 'coords': None},
            'cidade': {'nome': 'Não encontrada', 'distancia': 60.0, 'coords': None},
            'silo': {'nome': 'Não encontrado', 'distancia': 60.0, 'coords': None}
        }
    if 'hub' not in st.session_state:
        st.session_state.hub = {'nome': 'Não encontrado', 'distancia': 100.0, 'coords': None}
    
    if st.button("Buscar Dados Geográficos", type="primary"):
        with st.spinner("Realizando busca geográfica otimizada..."):
            all_pois_with_coords = find_all_nearest_pois(latitude, longitude, return_coords=True)
            if all_pois_with_coords:
                st.session_state.pois = all_pois_with_coords
            st.session_state.hub = find_nearest_hub(latitude, longitude)

    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    
    dist_asfalto_km = st.number_input(
        "Distância da Rodovia (km)", 
        min_value=0.0,
        value=float(st.session_state.get('pois', {}).get('rodovia', {}).get('distancia', 25.0))
    )
    dist_silo_km = st.number_input(
        "Distância do Armazém Graneleiro (km)",
        min_value=0.0, 
        value=float(st.session_state.get('pois', {}).get('silo', {}).get('distancia', 60.0))
    )

    # O restante dos inputs continua igual
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
    dados_fazenda = {
        'dist_asfalto_km': dist_asfalto_km, 'dist_silo_km': dist_silo_km,
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
        
        m = folium.Map(location=[latitude, longitude], zoom_start=9)
        folium.Marker(
            [latitude, longitude], 
            popup=f"📍 **{nome_fazenda}**", 
            tooltip="Local da Fazenda",
            icon=folium.Icon(color='blue', icon='home', prefix='fa')
        ).add_to(m)

        farm_coords = (latitude, longitude)

        if 'pois' in st.session_state:
            pois = st.session_state.pois
            
            # Linha para Silo/Graneleiro (Amarelo)
            if pois['silo']['coords']:
                silo_coords = pois['silo']['coords']
                folium.Marker(
                    silo_coords, 
                    popup=f"📦 **Armazém/Silo**: {pois['silo']['nome']} ({pois['silo']['distancia']:.1f} km)",
                    tooltip="Armazém/Silo Mais Próximo",
                    icon=folium.Icon(color='orange', icon='industry', prefix='fa')
                ).add_to(m)
                folium.PolyLine(
                    locations=[farm_coords, silo_coords],
                    color='yellow', weight=3, opacity=0.8,
                    tooltip=f"Distância ao Armazém: {pois['silo']['distancia']:.1f} km"
                ).add_to(m)

            # Rodovia (Laranja Escuro)
            if pois['rodovia']['coords']:
                rodovia_coords = pois['rodovia']['coords']
                folium.Marker(
                    rodovia_coords, 
                    popup=f"🛣️ **Rodovia**: {pois['rodovia']['nome']} ({pois['rodovia']['distancia']:.1f} km)",
                    tooltip="Rodovia Mais Próxima",
                    icon=folium.Icon(color='red', icon='road', prefix='fa')
                ).add_to(m)
                folium.PolyLine(
                    locations=[farm_coords, rodovia_coords],
                    color='darkorange', weight=3, opacity=0.8,
                    tooltip=f"Distância à Rodovia: {pois['rodovia']['distancia']:.1f} km"
                ).add_to(m)

            # Cidade (Neutro/Cinza)
            if pois['cidade']['coords']:
                cidade_coords = pois['cidade']['coords']
                folium.Marker(
                    cidade_coords, 
                    popup=f"🏙️ **Cidade**: {pois['cidade']['nome']} ({pois['cidade']['distancia']:.1f} km)",
                    tooltip="Cidade Mais Próxima",
                    icon=folium.Icon(color='lightgray', icon='building', prefix='fa')
                ).add_to(m)
                folium.PolyLine(
                    locations=[farm_coords, cidade_coords],
                    color='gray', weight=3, opacity=0.8,
                    tooltip=f"Distância à Cidade: {pois['cidade']['distancia']:.1f} km"
                ).add_to(m)
        
        folium_static(m, width=700, height=500)

        st.markdown("#### Distâncias Calculadas:")
        if 'pois' in st.session_state:
            pois = st.session_state.pois
            st.success(f"🛣️ **Rodovia mais próxima:** Aprox. **{pois['rodovia']['distancia']:.1f} km**")
            st.success(f"🏙️ **Cidade/Vila mais próxima:** {pois['cidade']['nome']} (aprox. **{pois['cidade']['distancia']:.1f} km**)")
            st.success(f"📦 **Armazém/Silo mais próximo:** {pois['silo']['nome']} (aprox. **{pois['silo']['distancia']:.1f} km**)")
        if 'hub' in st.session_state:
            st.success(f"🏭 **Polo de Agronegócio mais próximo:** {st.session_state.hub['nome']} (aprox. **{st.session_state.hub['distancia']:.1f} km**)")
    
    with tab3:
        st.subheader("Argumentação Sobre os Pesos da Análise")
        st.info("A metodologia de pesos reflete a realidade do investimento em ativos rurais...")
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)
else:
    st.info("Insira as coordenadas da fazenda e clique em 'Buscar Dados Geográficos' na barra lateral para começar.")
