# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st

# Endpoint da API Overpass, que consulta a base de dados do OpenStreetMap
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Cidades/Polos importantes para o agronegócio brasileiro (lat, lon)
# Esta lista pode ser expandida conforme a necessidade
HUBS_AGRO = {
    "Rio Verde (GO)": (-17.7972, -50.9262),
    "Goiânia (GO)": (-16.6869, -49.2648),
    "Rondonópolis (MT)": (-16.4705, -54.636),
    "Sorriso (MT)": (-12.5447, -55.7126),
    "Uberlândia (MG)": (-18.9186, -48.2772),
    "Cascavel (PR)": (-24.9555, -53.4552),
    "Campinas (SP)": (-22.9068, -47.0616),
    "Porto de Santos (SP)": (-23.9882, -46.3095)
}

def get_distance(coord1, coord2):
    """Calcula a distância em km entre duas coordenadas."""
    return geodesic(coord1, coord2).kilometers

@st.cache_data(show_spinner=False)
def find_nearest_poi(lat, lon, poi_query, radius_km=150):
    """
    Encontra o Ponto de Interesse (POI) mais próximo no OpenStreetMap.
    
    Args:
        lat (float): Latitude da fazenda.
        lon (float): Longitude da fazenda.
        poi_query (str): A query no formato da Overpass API.
        radius_km (int): O raio de busca em quilômetros.

    Returns:
        dict: Um dicionário com o nome e a distância do POI mais próximo.
    """
    radius_m = radius_km * 1000
    
    # Monta a query final
    full_query = f"""
    [out:json];
    (
      {poi_query}(around:{radius_m},{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.post(OVERPASS_URL, data=full_query)
        response.raise_for_status()  # Lança um erro para respostas ruins (4xx ou 5xx)
        data = response.json()
        
        if not data['elements']:
            return {"nome": "Nenhum encontrado no raio de busca", "distancia": radius_km}

        farm_coords = (lat, lon)
        nearest = None
        min_dist = float('inf')

        for element in data['elements']:
            tags = element.get('tags', {})
            name = tags.get('name', 'Sem nome')
            
            # Pega as coordenadas do centro do elemento (para estradas) ou do nó
            if 'center' in element:
                poi_coords = (element['center']['lat'], element['center']['lon'])
            else:
                poi_coords = (element['lat'], element['lon'])

            dist = get_distance(farm_coords, poi_coords)

            if dist < min_dist:
                min_dist = dist
                nearest = {"nome": name, "distancia": round(dist)}
        
        return nearest

    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão com a API de mapas: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado na busca: {e}")
        return None

def find_nearest_hub(lat, lon):
    """Encontra o Polo de Agronegócio mais próximo da lista pré-definida."""
    farm_coords = (lat, lon)
    min_dist = float('inf')
    nearest_hub = None

    for hub, coords in HUBS_AGRO.items():
        dist = get_distance(farm_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_hub = {"nome": hub, "distancia": round(dist)}
            
    return nearest_hub

# Queries pré-definidas para a API Overpass
QUERY_RODOVIA = 'way["highway"~"primary|secondary|tertiary|motorway"]'
QUERY_ARMAZEM = 'node["industrial"~"warehouse"]["service"~"storage"]'
QUERY_CIDADE = 'node["place"~"city|town"]'
