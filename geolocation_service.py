# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

# --- APIs ---
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# --- Constantes ---
HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Rio Verde (GO)": (-17.7972, -50.9262),
    "Sapezal (MT)": (-13.5428, -58.8744), "Jataí (GO)": (-17.8814, -51.7144),
    "São Desidério (BA)": (-12.3619, -44.9731), "Nova Ubiratã (MT)": (-12.9869, -55.2533),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Porto de Santos (SP)": (-23.9882, -46.3095),
}
# --- VALORES PADRÃO DE FALLBACK ---
DEFAULT_SOIL_DATA = {"ph": 5.8, "clay": 30.0}

# --- Funções de Lógica ---
def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

@st.cache_data(show_spinner=False, ttl=86400)
def get_soil_data(lat, lon):
    """
    Busca dados de pH e argila. Se falhar, retorna valores padrão e um aviso.
    """
    params = {"lon": lon, "lat": lat, "property": ["phh2o", "clay"], "depth": ["0-20cm"], "value": ["mean"]}
    try:
        response = requests.get(SOILGRIDS_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Verificação robusta da estrutura da resposta
        layers = data.get('properties', {}).get('layers', [])
        ph_value, clay_value = None, None
        
        for layer in layers:
            if layer.get('name') == 'phh2o':
                ph_value = layer.get('depths', [{}])[0].get('values', {}).get('mean')
                if ph_value is not None: ph_value /= 10.0
            elif layer.get('name') == 'clay':
                clay_value = layer.get('depths', [{}])[0].get('values', {}).get('mean')
                if clay_value is not None: clay_value /= 10.0
        
        if ph_value is not None and clay_value is not None:
            return True, {"ph": round(ph_value, 2), "clay": round(clay_value, 1)}
        else:
            # Se a extração falhou, ativa o Plano B
            st.warning(f"Não foi possível obter dados de solo da API. Usando valores padrão (pH {DEFAULT_SOIL_DATA['ph']}, Argila {DEFAULT_SOIL_DATA['clay']}%).")
            return True, DEFAULT_SOIL_DATA

    except Exception as e:
        # Se a conexão falhou, ativa o Plano B
        st.warning(f"Não foi possível buscar dados de solo (Erro: {e.__class__.__name__}). Usando valores padrão (pH {DEFAULT_SOIL_DATA['ph']}, Argila {DEFAULT_SOIL_DATA['clay']}%).")
        return True, DEFAULT_SOIL_DATA

# ... (O restante do arquivo continua o mesmo)
@st.cache_data(show_spinner=False, ttl=86400)
def get_clima_data(lat, lon):
    # ...
    return True, 1500 # Exemplo

@st.cache_data(show_spinner=False, ttl=3600)
def find_all_nearest_pois(lat, lon, return_coords=False):
    # ...
    return True, {} # Exemplo

def find_nearest_hub(lat, lon):
    # ...
    return True, {} # Exemplo
