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

# --- BANCO DE DADOS INTERNO DE RODOVIAS ---
RODOVIAS_DB = {
    "BR-153 (Belém-Brasília)": [(-16.68, -49.25), (-17.73, -49.24), (-18.52, -49.19), (-20.45, -51.39)],
    "BR-060 (Brasília-Bela Vista)": [(-16.68, -49.25), (-17.29, -50.23), (-17.79, -50.93), (-18.89, -52.88)],
    "BR-364 (Cuiabá-Porto Velho)": [(-17.79, -50.93), (-17.88, -51.71), (-16.33, -54.69), (-15.60, -56.09)],
    "BR-163 (Cuiabá-Santarém)": [(-15.60, -56.09), (-13.05, -55.90), (-12.54, -55.71), (-11.86, -55.50)],
    "GO-070 (Goiânia-Itaberaí)": [(-16.68, -49.25), (-16.51, -49.56), (-16.39, -49.95), (-16.20, -51.22)],
}

# --- Constantes ---
HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Rio Verde (GO)": (-17.7972, -50.9262),
    "Sapezal (MT)": (-13.5428, -58.8744), "Jataí (GO)": (-17.8814, -51.7144),
    "São Desidério (BA)": (-12.3619, -44.9731), "Uberlândia (MG)": (-18.9186, -48.2772),
}
DEFAULT_SOIL_DATA = {"ph": 5.8, "clay": 30.0}

# --- Funções de Lógica ---
def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

@st.cache_data
def find_nearest_highway_from_db(lat, lon):
    farm_coords = (lat, lon)
    min_dist = float('inf')
    nearest_highway_info = {"nome": "Nenhuma rodovia encontrada", "distancia": 999, "coords": None}
    for highway_name, points in RODOVIAS_DB.items():
        for point_coords in points:
            dist = get_distance(farm_coords, point_coords)
            if dist < min_dist:
                min_dist = dist
                nearest_highway_info = {
                    "nome": highway_name, "distancia": round(dist, 1), "coords": point_coords
                }
    return True, nearest_highway_info

@st.cache_data(show_spinner=False, ttl=86400)
def get_soil_data(lat, lon):
    params = {"lon": lon, "lat": lat, "property": ["phh2o", "clay"], "depth": ["0-20cm"], "value": ["mean"]}
    try:
        response = requests.get(SOILGRIDS_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
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
            st.warning(f"Não foi possível obter dados de solo da API. Usando valores padrão (pH {DEFAULT_SOIL_DATA['ph']}, Argila {DEFAULT_SOIL_DATA['clay']}%).")
            return True, DEFAULT_SOIL_DATA
    except Exception as e:
        st.warning(f"Não foi possível buscar dados de solo (Erro: {e.__class__.__name__}). Usando valores padrão.")
        return True, DEFAULT_SOIL_DATA

@st.cache_data(show_spinner=False, ttl=86400)
def get_clima_data(lat, lon):
    ano_atual = datetime.now().year
    start_date, end_date = f"{ano_atual - 31}-01-01", f"{ano_atual - 1}-12-31"
    params = {"latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date, "daily": "precipitation_sum", "timezone": "auto"}
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        if 'daily' not in data or 'precipitation_sum' not in data['daily']: return False, "API de clima não retornou dados."
        total_precipitation = sum(p for p in data['daily']['precipitation_sum'] if p is not None)
        num_years = len(data['daily']['time']) / 365.25
        if num_years < 28: return False, "API de clima: Dados históricos insuficientes."
        return True, int(total_precipitation / num_years)
    except Exception as e: return False, f"Não foi possível buscar os dados de clima. Erro: {e}"

@st.cache_data(show_spinner=False, ttl=3600)
def find_local_pois(lat, lon, return_coords=False):
    raio_local_m = 75 * 1000
    query_combinada = f"""[out:json][timeout:45];((node["place"~"city|town|village"](around:{raio_local_m},{lat},{lon}););(node["man_made"="silo"](around:{raio_local_m},{lat},{lon});way["building"="silo"](around:{raio_local_m},{lat},{lon});node["name"~"Silo|Cooperativa|Graneleiro",i](around:{raio_local_m},{lat},{lon});););out center;"""
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data=query_combinada, timeout=60)
            response.raise_for_status()
            data = response.json()
            results = {"cidade": {"nome": "Não encontrada", "distancia": raio_local_m / 1000, "coords": None}, "silo": {"nome": "Não encontrado", "distancia": raio_local_m / 1000, "coords": None}}
            if not data.get('elements'): return True, results
            farm_coords = (lat, lon)
            min_dists = {"cidade": float('inf'), "silo": float('inf')}
            for element in data['elements']:
                tags, name = element.get('tags', {}), element.get('tags', {}).get('name', 'Silo/Armazém')
                poi_coords = (element.get('center', {}).get('lat', element.get('lat')), element.get('center', {}).get('lon', element.get('lon')))
                if poi_coords[0] is None: continue
                dist = get_distance(farm_coords, poi_coords)
                if "place" in tags and dist < min_dists["cidade"]:
                    min_dists["cidade"] = dist
                    results["cidade"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
                elif ("man_made" in tags and tags["man_made"] == "silo") or any(keyword in name for keyword in ["Silo", "Cooperativa", "Graneleiro"]) and dist < min_dists["silo"]:
                    min_dists["silo"] = dist
                    results["silo"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
            return True, results
        except (requests.exceptions.RequestException, json.JSONDecodeError): continue
    return False, "Todos os servidores de mapas para POIs locais falharam."

def find_nearest_hub(lat, lon):
    farm_coords = (lat, lon)
    min_dist, nearest_hub = float('inf'), None
    for hub_name, coords in HUBS_AGRO.items():
        dist = get_distance(farm_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_hub = {"nome": hub_name, "distancia": round(dist, 1), "coords": coords}
    return True, nearest_hub
