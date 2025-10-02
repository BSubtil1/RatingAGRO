# app.py

import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from scoring_engine import calcular_indice_viabilidade, PESOS, JUSTIFICATIVAS_PESOS

# --- Configuração da Página ---
st.set_page_config(
    page_title="AgroScore Validator 2.0",
    page_icon="🗺️",
    layout="wide"
)

# --- Funções Auxiliares ---

def create_pdf_report(dados_fazenda, indice_final, scores_detalhados, classe, desc_classe):
    """Gera o laudo da análise em um arquivo PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Cabeçalho
    pdf.cell(0, 10, f"Laudo de Viabilidade - {dados_fazenda['nome_fazenda']}", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, "C")
    pdf.ln(10)

    # Resumo Geral
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Resumo da Avaliacao", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, f"Indice de Viabilidade Final: {indice_final:.2f} / 10")
    pdf.multi_cell(0, 5, f"Classificacao do Ativo: {classe}")
    pdf.multi_cell(0, 5, f"Recomendacao: {desc_classe}")
    pdf.ln(10)

    # Detalhamento dos Scores
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. Pontuacoes por Categoria", 0, 1)
    pdf.set_font("Arial", "", 10)
    for categoria, score in scores_detalhados.items():
        pdf.multi_cell(0, 5, f"- {categoria.replace('_', ' ').title()}: {score:.1f} / 10")
    pdf.ln(10)
    
    # Dados de Entrada
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "3. Dados de Entrada Utilizados", 0, 1)
    pdf.set_font("Arial", "", 10)
    for chave, valor in dados_fazenda.items():
         if chave not in ['latitude', 'longitude']: # Nao precisa mostrar lat/lon no PDF
             pdf.multi_cell(0, 5, f"- {chave.replace('_', ' ').title()}: {valor}")
    pdf.ln(10)
    
    # Salva o PDF em memória
    return pdf.output(dest='S').encode('latin-1')


# --- Título e Descrição ---
st.title("🗺️ AgroScore Validator 2.0")
st.markdown("Uma plataforma aprimorada para análise de viabilidade de ativos rurais, agora com laudo em PDF, geolocalização e classificação de ativos.")

# --- Barra Lateral de Entradas (Inputs) ---
with st.sidebar:
    st.header("Dados de Entrada da Propriedade")

    nome_fazenda = st.text_input("Nome da Fazenda (para busca e laudo)", "Fazenda Boa Esperança")
    latitude = st.number_input("Latitude da Sede", value=-16.68, format="%.6f")
    longitude = st.number_input("Longitude da Sede", value=-49.25, format="%.6f")

    # 1. Logística
    st.subheader("1. Logística (Peso: {}%)".format(int(PESOS['logistica']*100)))
    dist_asfalto_km = st.number_input("Distância do Asfalto (km)", min_value=0, value=25)
    dist_silo_km = st.number_input("Distância do Armazém/Silo (km)", min_value=0, value=60)

    # 2. Legal/Ambiental
    st.subheader("2. Legal e Ambiental (Peso: {}%)".format(int(PESOS['legal_ambiental']*100)))
    situacao_reserva_legal = st.selectbox(
        "Situação da Reserva Legal (CAR)",
        ['Averbada e regular', 'Averbada, mas precisa de averiguação', 'Pendente com passivo']
    )
    possui_geo_sigef = st.checkbox("Possui Georreferenciamento (SIGEF)?", value=True)

    # 3. Recursos Hídricos
    st.subheader("3. Recursos Hídricos (Peso: {}%)".format(int(PESOS['recursos_hidricos']*100)))
    indice_pluviometrico_mm = st.slider("Índice Pluviométrico Médio Anual (mm)", 600, 2500, 1500)
    presenca_rio_perene = st.checkbox("Possui Rio Perene na propriedade?", value=True)

    # 4. Agronomia
    st.subheader("4. Agronomia (Peso: {}%)".format(int(PESOS['agronomia']*100)))
    ph_solo = st.slider("pH médio do Solo", 3.0, 9.0, 5.8, 0.1)
    teor_argila_percent = st.slider("Teor de Argila do Solo (%)", 5, 70, 30)

    # 5. Topografia
    st.subheader("5. Topografia (Peso: {}%)".format(int(PESOS['topografia']*100)))
    percentual_mecanizavel = st.slider("Área Mecanizável da Fazenda (%)", 0, 100, 85)

    # --- Botão de Ação ---
    analisar = st.button("Analisar Viabilidade", type="primary")

# --- Painel Principal de Resultados ---
if analisar:
    dados_fazenda = {
        'nome_fazenda': nome_fazenda, 'latitude': latitude, 'longitude': longitude,
        'dist_asfalto_km': dist_asfalto_km, 'dist_silo_km': dist_silo_km,
        'situacao_reserva_legal': situacao_reserva_legal, 'possui_geo_sigef': possui_geo_sigef,
        'indice_pluviometrico_mm': indice_pluviometrico_mm, 'presenca_rio_perene': presenca_rio_perene,
        'ph_solo': ph_solo, 'teor_argila_percent': teor_argila_percent,
        'percentual_mecanizavel': percentual_mecanizavel
    }

    indice_final, scores_detalhados, classe, desc_classe = calcular_indice_viabilidade(dados_fazenda)

    st.header(f"Resultados da Análise: {nome_fazenda}")

    # Aba de Resumo
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo Geral", "🗺️ Localização e Busca", "⚖️ Justificativa dos Pesos", "📄 Laudo PDF"])

    with tab1:
        st.subheader("Compilado da Avaliação")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Índice de Viabilidade Final", value=f"{indice_final:.2f} / 10")
            
            # Download do PDF
            pdf_bytes = create_pdf_report(dados_fazenda, indice_final, scores_detalhados, classe, desc_classe)
            st.download_button(
                label="📥 Baixar Laudo em PDF",
                data=pdf_bytes,
                file_name=f"Laudo_{nome_fazenda.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

        with col2:
            st.subheader(f"Classificação do Ativo: {classe}")
            st.info(desc_classe)

        st.divider()
        st.subheader("Pontuações por Categoria")
        for categoria, score in scores_detalhados.items():
            st.markdown(f"**{categoria.replace('_', ' ').title()}**")
            st.progress(int(score * 10))

    with tab2:
        st.subheader("Localização da Propriedade")
        map_data = pd.DataFrame({'lat': [latitude], 'lon': [longitude]})
        st.map(map_data, zoom=12)

        st.subheader("Busca por Informações na Internet")
        st.info("Esta é uma busca preliminar por notícias ou registros públicos. A ausência de resultados não é conclusiva.")
        query = f'"{nome_fazenda}" OR "fazenda {nome_fazenda}" OR "leilão fazenda {nome_fazenda}"'
        google_search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        st.markdown(f"[Clique aqui para buscar por '{nome_fazenda}' no Google]({google_search_url})", unsafe_allow_html=True)
        st.warning("Atenção: A análise de informações online deve ser feita com critério, verificando a veracidade e a data das fontes.")
    
    with tab3:
        st.subheader("Argumentação Sobre os Pesos da Análise")
        st.info("A metodologia de pesos reflete a realidade do investimento em ativos rurais, onde certos fatores têm impacto desproporcional na viabilidade e no risco.")
        for categoria, just in JUSTIFICATIVAS_PESOS.items():
            with st.expander(f"**{categoria.replace('_', ' ').title()} (Peso: {int(PESOS[categoria]*100)}%)**"):
                st.markdown(just)

    with tab4:
        st.subheader("Pré-visualização e Download do Laudo")
        st.info("Utilize o botão abaixo para baixar o relatório consolidado da sua análise em formato PDF.")
        st.download_button(
                label="📥 Baixar Laudo em PDF",
                data=pdf_bytes,
                file_name=f"Laudo_{nome_fazenda.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

else:
    st.info("Bem-vindo ao AgroScore Validator 2.0! Preencha os dados da propriedade na barra lateral e clique em 'Analisar Viabilidade' para começar.")
