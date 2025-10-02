# app.py

import streamlit as st
from scoring_engine import calcular_indice_viabilidade, PESOS

# --- Configuração da Página ---
st.set_page_config(
    page_title="AgroScore Validator",
    page_icon="🌱",
    layout="wide"
)

# --- Título e Descrição ---
st.title("🌱 AgroScore Validator")
st.markdown("Ferramenta de análise rápida para avaliação de viabilidade de propriedades rurais. Insira os dados da fazenda na barra lateral para gerar o **Índice de Viabilidade**.")

# --- Barra Lateral de Entradas (Inputs) ---
st.sidebar.header("Dados de Entrada da Propriedade")

# 1. Logística
st.sidebar.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
dist_asfalto_km = st.sidebar.number_input("Distância do Asfalto (km)", min_value=0, value=25)
dist_silo_km = st.sidebar.number_input("Distância do Armazém/Silo (km)", min_value=0, value=60)

# 2. Legal/Ambiental
st.sidebar.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
situacao_reserva_legal = st.sidebar.selectbox(
    "Situação da Reserva Legal (CAR)",
    ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo']
)
possui_geo_sigef = st.sidebar.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)

# 3. Recursos Hídricos
st.sidebar.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
indice_pluviometrico_mm = st.sidebar.slider(
    "Índice Pluviométrico Médio Anual (mm)", 
    min_value=600, max_value=2500, value=1500
)
presenca_rio_perene = st.sidebar.checkbox("Possui Rio Perene na propriedade?", value=True)

# 4. Agronomia
st.sidebar.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
ph_solo = st.sidebar.slider("pH médio do Solo", min_value=3.0, max_value=9.0, value=5.8, step=0.1)
teor_argila_percent = st.sidebar.slider("Teor de Argila do Solo (%)", min_value=5, max_value=70, value=30)

# 5. Topografia
st.sidebar.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
percentual_mecanizavel = st.sidebar.slider(
    "Área Mecanizável da Fazenda (%)", 
    min_value=0, max_value=100, value=85
)

# --- Botão de Ação ---
if st.sidebar.button("Analisar Viabilidade"):
    # Organiza os dados para enviar ao motor de cálculo
    dados_fazenda = {
        'dist_asfalto_km': dist_asfalto_km,
        'dist_silo_km': dist_silo_km,
        'situacao_reserva_legal': situacao_reserva_legal,
        'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': indice_pluviometrico_mm,
        'presenca_rio_perene': presenca_rio_perene,
        'ph_solo': ph_solo,
        'teor_argila_percent': teor_argila_percent,
        'percentual_mecanizavel': percentual_mecanizavel
    }

    # Calcula o índice e os scores individuais
    indice_final, scores_detalhados = calcular_indice_viabilidade(dados_fazenda)

    # --- Exibição dos Resultados ---
    st.header("Resultados da Análise")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Índice de Viabilidade Final")
        
        # Lógica para cor do medidor
        if indice_final >= 7.5:
            cor_delta = "normal"
            recomendacao = "✅ **Alto Potencial:** Ativo com fundamentos sólidos. Prossiga com a due diligence aprofundada."
        elif indice_final >= 5.0:
            cor_delta = "off"
            recomendacao = "⚠️ **Potencial com ressalvas:** O ativo é viável, mas possui pontos de atenção que podem impactar a TIR. Análise de custos é crucial."
        else:
            cor_delta = "inverse"
            recomendacao = "❌ **Alto Risco:** Fatores limitantes críticos foram identificados. O investimento não é recomendado sem uma reavaliação estratégica profunda."

        st.metric(label="Pontuação de 0 a 10", value=f"{indice_final:.2f}", delta_color=cor_delta)
        st.markdown(recomendacao)

    with col2:
        st.subheader("Pontuações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10)) # Barra de progresso de 0 a 100

else:
    st.info("Por favor, preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade'.")
