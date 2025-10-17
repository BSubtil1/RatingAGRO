# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

# --- APIs (APENAS PARA CLIMA E SOLO) ---
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# --- BANCO DE DADOS INTERNO DE RODOVIAS ---
# Representamos as principais rodovias pavimentadas como uma série de pontos-chave (cidades/trevos).
# Isso é extremamente rápido e confiável, eliminando a dependência de APIs externas para logística.
RODOVIAS_DB = {
    # Rodovias Federais (BR)
    "BR-153 (Belém-Brasília)": [(-16.68, -49.25), (-17.73, -49.24), (-18.52, -49.19), (-20.45, -51.39)],
    "BR-060 (Brasília-Bela Vista)": [(-16.68, -49.25), (-17.29, -50.23), (-17.79, -50.93), (-18.89, -52.88)],
    "BR-364 (Cuiabá-Porto Velho)": [(-17.79, -50.93), (-17.88, -51.71), (-16.33, -54.69), (-15.60, -56.09)],
    "BR-163 (Cuiabá-Santarém)": [(-15.60, -56.09), (-13.05, -55.90), (-12.54, -55.71), (-11.86, -55.50)],
    "BR-070 (Brasília-Cáceres)": [(-15.82, -47.92), (-16.03, -50.15), (-15.89, -52.36), (-15.60, -56.09)],
    "BR-050 (Brasília-Santos)": [(-16.76, -47.61), (-18.17, -47.96), (-18.91, -48.27), (-19.74, -47.93)],
    "BR-242 (Bahia-Mato Grosso)": [(-12.09, -45.80), (-12.91, -41.48), (-12.54, -55.71), (-13.33, -53.16)],

    # Principais Rodovias de Goiás (GO)
    "GO-070 (Goiânia-Itaberaí)": [(-16.68, -49.25), (-16.51, -49.56), (-16.39, -49.95), (-16.20, -51.22)],
    "GO-080 (Goiânia-Uruaçu)": [(-16.68, -49.25), (-15.93, -49.50), (-15.53, -49.14), (-14.52, -49.14)],
    "GO-164 (Quirinópolis-Mozarlândia)": [(-18.44, -50.45), (-17.79, -50.93), (-16.20, -51.22), (-14.74, -50.57)],
    "GO-060 (Goiânia-Iporá)": [(-16.68, -49.25), (-16.71, -49.95), (-16.62, -50.60), (-16.44, -51.11)],
}

# --- Constantes (HUBS_AGRO) ---
# ... (a lista de HUBS_AGRO continua a mesma)
HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Rio Verde (GO)": (-17.7972, -50.9262),
    "Sapezal (MT)": (-13.5428, -58.8744), "Jataí (GO)": (-17.8814, -51.7144),
    "São Desidério (BA)": (-12.3619, -44.9731), "Nova Ubiratã (MT)": (-12.9869, -55.2533),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Porto de Santos (SP)": (-23.9882, -46.3095),
}

# --- Funções de Lógica ---

def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

# NOVA FUNÇÃO DE BUSCA DE RODOVIA - 100% OFFLINE E CONFIÁVEL
@st.cache_data
def find_nearest_highway_from_db(lat, lon):
    """Calcula a distância até a rodovia mais próxima usando o banco de dados interno."""
    farm_coords = (lat, lon)
    min_dist = float('inf')
    nearest_highway_info = {"nome": "Nenhuma rodovia encontrada", "distancia": 999, "coords": None}

    for highway_name, points in RODOVIAS_DB.items():
        for point_coords in points:
            dist = get_distance(farm_coords, point_coords)
            if dist < min_dist:
                min_dist = dist
                nearest_highway_info = {
                    "nome": highway_name,
                    "distancia": round(dist, 1),
                    "coords": point_coords
                }
    
    return True, nearest_highway_info

# As funções de solo e clima continuam iguais
@st.cache_data(show_spinner=False, ttl=86400)
def get_soil_data(lat, lon):
    params = {"lon": lon, "lat": lat, "property": ["phh2o", "clay"], "depth": ["0-20cm"], "value": ["mean"]}
    try:
        response = requests.get(SOILGRIDS_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        layers = data['properties']['layers']
        ph_value, clay_value = None, None
        for layer in layers:
            if layer['name'] == 'phh2o': ph_value = layer['depths'][0]['values']['mean'] / 10.0
            elif layer['name'] == 'clay': clay_value = layer['depths'][0]['values']['mean'] / 10.0
        if ph_value is not None and clay_value is not None:
            return True, {"ph": round(ph_value
