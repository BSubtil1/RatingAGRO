# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Rio Verde (GO)": (-17.7972, -50.9262),
    "Sapezal (MT)": (-13.5428, -58.8744), "Jataí (GO)": (-17.8814, -51.7144),
    "São Desidério (BA)": (-12.3619, -44.9731), "Nova Ubiratã (MT)": (-12.9869, -55.2533),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Porto de Santos (SP)": (-23.9882, -46.3095),
}

def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

@st.cache_data(show_spinner=False, ttl=86400)
def get_clima_data(lat, lon):
    ano_atual = datetime.now().year
    start_date = f"{ano_atual - 31}-01-01"
    end_date = f"{ano_atual - 1}-12-31"
    params = {"latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date, "daily": "precipitation_sum", "timezone": "auto"}
    
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        if 'daily' not in data or 'precipitation_sum' not in data['daily']:
            return False, "API de clima não retornou dados de precipitação."
        
        total_precipitation = sum(p for p in data['daily']['precipitation_sum'] if p is not None)
        num_years = len(data['daily']['time']) / 365.25
        
        if num_years < 28:
            return False, "API de clima: Dados históricos insuficientes para um cálculo preciso."

        return True, int(total_precipitation / num_years)
    except requests.exceptions.Timeout:
        return False, "A busca de dados de clima demorou demais e falhou (Timeout)."
    except Exception as e:
        return False, f"Não foi possível buscar dados de clima. Erro: {e}"

@st.cache_data(show_spinner=False, ttl=3600)
def find_all_nearest_pois(lat, lon, return_coords=False):
    raio_rodovia_m, raio_local_m = 100 * 1000, 75 * 1000
    query_combinada = f"""[out:json][timeout:45];(way["highway"~"primary|secondary|tertiary|motorway"](around:{raio_rodovia_m},{lat},{lon});node["place"~"city|town|village"](around:{raio_local_m},{lat},{lon});(node["man_made"="silo"](around:{raio_local_m},{lat},{lon});way["building"="silo"](around:{raio_local_m},{lat},{lon});node["name"~"Silo|Cooperativa|Graneleiro",i](around:{raio_local_m},{lat},{lon});););out center;"""
    
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data=query_combinada, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            results = {
                "rodovia": {"nome": "Não encontrada", "distancia": raio_rodovia_m / 1000, "coords": None},
                "cidade": {"nome": "Não encontrada", "distancia": raio_local_m / 1000, "coords": None},
                "silo": {"nome": "Não encontrado", "distancia": raio_local_m / 1000, "coords": None}
            }
            if not data.get('elements'): return True, results
            
            farm_coords = (lat, lon)
            min_dists = {"rodovia": float('inf'), "cidade": float('inf'), "silo": float('inf')}
            
            for element in data['elements']:
                tags = element.get('tags', {})
                name = tags.get('name', 'Silo/Armazém')
                poi_coords = (element.get('center', {}).get('lat', element.get('lat')), element.get('center', {}).get('lon', element.get('lon')))
                if poi_coords[0] is None: continue
                
                dist = get_distance(farm_coords, poi_coords)
                
                if "highway" in tags and dist < min_dists["rodovia"]:
                    min_dists["rodovia"] = dist
                    results["rodovia"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
                elif "place" in tags and dist < min_dists["cidade"]:
                    min_dists["cidade"] = dist
                    results["cidade"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
                elif ("man_made" in tags and tags["man_made"] == "silo") or any(keyword in name for keyword in ["Silo", "Cooperativa", "Graneleiro"]) and dist < min_dists["silo"]:
                    min_dists["silo"] = dist
                    results["silo"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
            
            return True, results
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            continue
            
    return False, "Todos os servidores de mapas falharam em responder. Tente novamente mais tarde."

def find_nearest_hub(lat, lon):
    farm_coords = (lat, lon)
    min_dist, nearest_hub = float('inf'), None
    for hub_name, coords in HUBS_AGRO.items():
        dist = get_distance(farm_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_hub = {"nome": hub_name, "distancia": round(dist, 1), "coords": coords}
    return True, nearest_hub
