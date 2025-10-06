# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HUBS_AGRO = {
    "Rio Verde (GO)": (-17.7972, -50.9262), "Goiânia (GO)": (-16.6869, -49.2648),
    "Rondonópolis (MT)": (-16.4705, -54.636), "Sorriso (MT)": (-12.5447, -55.7126),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Cascavel (PR)": (-24.9555, -53.4552),
    "Campinas (SP)": (-22.9068, -47.0616), "Porto de Santos (SP)": (-23.9882, -46.3095)
}

def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

@st.cache_data(show_spinner=False, ttl=3600)
def find_all_nearest_pois(lat, lon, return_coords=False):
    raio_rodovia_m = 100 * 1000
    raio_local_m = 75 * 1000

    # MUDANÇA AQUI: Query do silo foi simplificada para ser mais rápida
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
    
    results = {
        "rodovia": {"nome": "Não encontrada", "distancia": raio_rodovia_m / 1000, "coords": None},
        "cidade": {"nome": "Não encontrada", "distancia": raio_local_m / 1000, "coords": None},
        "silo": {"nome": "Não encontrado", "distancia": raio_local_m / 1000, "coords": None}
    }

    try:
        # MUDANÇA AQUI: Timeout da requisição aumentado para 60 segundos
        response = requests.post(OVERPASS_URL, data=query_combinada, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not data['elements']:
            return results

        farm_coords = (lat, lon)
        min_dists = {"rodovia": float('inf'), "cidade": float('inf'), "silo": float('inf')}

        for element in data['elements']:
            tags = element.get('tags', {})
            name = tags.get('name', 'Silo/Armazém')
            
            if 'center' in element:
                poi_coords = (element['center']['lat'], element['center']['lon'])
            else:
                poi_coords = (element['lat'], element['lon'])
            
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
        return results
    except requests.exceptions.Timeout:
        st.error("A busca demorou demais e foi cancelada (Timeout). A análise usará os valores manuais de distância.")
        return None
    except requests.exceptions.RequestException as e:
        st.warning(f"Não foi possível buscar dados geográficos. A análise usará os valores manuais. Erro: {e}")
        return None
    except json.JSONDecodeError:
        st.warning("A API de mapas retornou uma resposta inválida. A análise usará os valores manuais.")
        return None

def find_nearest_hub(lat, lon):
    farm_coords = (lat, lon)
    min_dist = float('inf')
    nearest_hub = None
    for hub_name, coords in HUBS_AGRO.items():
        dist = get_distance(farm_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_hub = {"nome": hub_name, "distancia": round(dist, 1), "coords": coords}
    return nearest_hub
