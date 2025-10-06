# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

# MUDANÇA AQUI: Criamos uma lista de servidores alternativos para a API Overpass
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# --- Constantes ---
HUBS_AGRO = {
    "Rio Verde (GO)": (-17.7972, -50.9262), "Goiânia (GO)": (-16.6869, -49.2648),
    "Rondonópolis (MT)": (-16.4705, -54.636), "Sorriso (MT)": (-12.5447, -55.7126),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Cascavel (PR)": (-24.9555, -53.4552),
    "Campinas (SP)": (-22.9068, -47.0616), "Porto de Santos (SP)": (-23.9882, -46.3095)
}

# --- Funções de Lógica ---

def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

@st.cache_data(show_spinner=False, ttl=86400)
def get_clima_data(lat, lon):
    # ... (Esta função permanece igual) ...
    ano_atual = datetime.now().year
    start_date = f"{ano_atual - 31}-01-01"
    end_date = f"{ano_atual - 1}-12-31"
    params = {
        "latitude": lat, "longitude": lon, "start_date": start_date,
        "end_date": end_date, "daily": "precipitation_sum", "timezone": "auto"
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        if 'daily' not in data or 'precipitation_sum' not in data['daily']:
            st.error("Erro na API de clima: Dados de precipitação não encontrados.")
            return None
        total_precipitation = sum(p for p in data['daily']['precipitation_sum'] if p is not None)
        num_years = len(data['daily']['time']) / 365.25
        if num_years < 28:
            st.error("Erro na API de clima: Dados históricos insuficientes.")
            return None
        annual_avg = total_precipitation / num_years
        return int(annual_avg)
    except requests.exceptions.Timeout:
        st.error("A busca de dados de clima falhou (Timeout). Tente novamente.")
        return None
    except Exception as e:
        st.error(f"Não foi possível buscar os dados de clima. Erro: {e}")
        return None

@st.cache_data(show_spinner=False, ttl=3600)
def find_all_nearest_pois(lat, lon, return_coords=False):
    raio_rodovia_m = 100 * 1000
    raio_local_m = 75 * 1000
    query_combinada = f"""
    [out:json][timeout:45];
    (
      way["highway"~"primary|secondary|tertiary|motorway"](around:{raio_rodovia_m},{lat},{lon});
      node["place"~"city|town|village"](around:{raio_local_m},{lat},{lon});
      (
        node["man_made"="silo"](around:{raio_local_m},{lat},{lon});
        way["building"="silo"](around:{raio_local_m},{lat},{lon});
        node["name"~"Silo|Cooperativa|Graneleiro",i](around:{raio_local_m},{lat},{lon});
      );
    );
    out center;
    """
    
    # MUDANÇA AQUI: Itera sobre a lista de servidores
    for i, endpoint in enumerate(OVERPASS_ENDPOINTS):
        try:
            st.toast(f"Tentando servidor de mapas {i+1}/{len(OVERPASS_ENDPOINTS)}...")
            response = requests.post(endpoint, data=query_combinada, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Se chegamos aqui, a busca funcionou. Processamos os resultados.
            results = {
                "rodovia": {"nome": "Não encontrada", "distancia": raio_rodovia_m / 1000, "coords": None},
                "cidade": {"nome": "Não encontrada", "distancia": raio_local_m / 1000, "coords": None},
                "silo": {"nome": "Não encontrado", "distancia": raio_local_m / 1000, "coords": None}
            }
            if not data['elements']: return results
            
            farm_coords = (lat, lon)
            min_dists = {"rodovia": float('inf'), "cidade": float('inf'), "silo": float('inf')}
            
            for element in data['elements']:
                tags = element.get('tags', {})
                name = tags.get('name', 'Silo/Armazém')
                if 'center' in element: poi_coords = (element['center']['lat'], element['center']['lon'])
                else: poi_coords = (element['lat'], element['lon'])
                dist = get_distance(farm_coords, poi_coords)
                
                if "highway" in tags:
                    if dist < min_dists["rodovia"]:
                        min_dists["rodovia"] = dist
                        results["rodovia"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
                elif "place" in tags:
                    if dist < min_dists["cidade"]:
                        min_dists["cidade"] = dist
                        results["cidade"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
                elif "man_made" in tags or "Silo" in name or "Cooperativa" in name or "Graneleiro" in name:
                    if dist < min_dists["silo"]:
                        min_dists["silo"] = dist
                        results["silo"] = {"nome": name, "distancia": round(dist, 1), "coords": poi_coords if return_coords else None}
            
            return results # Retorna o sucesso e sai do loop

        except (requests.exceptions.Timeout, requests.exceptions.HTTPError, json.JSONDecodeError) as e:
            # Se um servidor falhar, avisa e continua para o próximo
            st.toast(f"Servidor {i+1} falhou. Erro: {e.__class__.__name__}. Tentando o próximo...")
            continue # Pula para a próxima iteração do loop
    
    # Se todos os servidores da lista falharem, exibe o erro final
    st.error("Todos os servidores de mapas falharam em responder. Tente novamente mais tarde.")
    return None

def find_nearest_hub(lat, lon):
    # ... (Esta função continua exatamente igual) ...
    farm_coords = (lat, lon)
    min_dist = float('inf')
    nearest_hub = None
    for hub_name, coords in HUBS_AGRO.items():
        dist = get_distance(farm_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_hub = {"nome": hub_name, "distancia": round(dist, 1), "coords": coords}
    return nearest_hub
