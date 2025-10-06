# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

# --- APIs ---
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# --- Constantes (HUBS_AGRO) ---
# ... (a lista de HUBS_AGRO continua a mesma)
HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Sapezal (MT)": (-13.5428, -58.8744),
    "Campo Novo do Parecis (MT)": (-13.6744, -57.8894), "Diamantino (MT)": (-14.4086, -56.4458),
    "Nova Ubiratã (MT)": (-12.9869, -55.2533), "Nova Mutum (MT)": (-13.8291, -56.0822),
    "Querência (MT)": (-12.6042, -52.1939), "Primavera do Leste (MT)": (-15.5597, -54.2958),
    "Lucas do Rio Verde (MT)": (-13.0531, -55.9083), "São Desidério (BA)": (-12.3619, -44.9731),
    "Formosa do Rio Preto (BA)": (-11.0483, -45.1928), "Correntina (BA)": (-13.3431, -44.6372),
    "Luís Eduardo Magalhães (BA)": (-12.0919, -45.8019), "Balsas (MA)": (-7.5325, -46.0356),
    "Uruçuí (PI)": (-7.2294, -44.5583), "Bom Jesus (PI)": (-9.0744, -44.3592),
    "Rio Verde (GO)": (-17.7972, -50.9262), "Jataí (GO)": (-17.8814, -51.7144),
    "Cristalina (GO)": (-16.7686, -47.6144), "Unaí (MG)": (-16.3575, -46.9061),
    "Uberlândia (MG)": (-18.9186, -48.2772), "Uberaba (MG)": (-19.7483, -47.9319),
    "Paracatu (MG)": (-17.2219, -46.8753), "Maracaju (MS)": (-21.6144, -55.1683),
    "Ponta Porã (MS)": (-22.5361, -55.7256), "Dourados (MS)": (-22.2211, -54.8056),
    "Sidrolândia (MS)": (-20.9319, -54.9608), "Cascavel (PR)": (-24.9555, -53.4552),
    "Tibagi (PR)": (-24.5103, -50.4158), "Guarapuava (PR)": (-25.3947, -51.4578),
    "Tupanciretã (RS)": (-29.0836, -53.8436), "Piracicaba (SP)": (-22.7253, -47.6492),
    "Porto de Santos (SP)": (-23.9882, -46.3095)
}


# --- Funções de Lógica ---

def get_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

# NOVA FUNÇÃO PARA BUSCAR DADOS DE SOLO
@st.cache_data(show_spinner=False, ttl=86400)
def get_soil_data(lat, lon):
    """Busca dados de pH e argila para uma coordenada usando a API SoilGrids."""
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["phh2o", "clay"], # pH em água e Teor de argila
        "depth": ["0-20cm"], # Profundidade do solo superficial
        "value": ["mean"]
    }
    try:
        response = requests.get(SOILGRIDS_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        layers = data['properties']['layers']
        ph_value = None
        clay_value = None

        for layer in layers:
            if layer['name'] == 'phh2o':
                # O valor do pH vem multiplicado por 10
                ph_value = layer['depths'][0]['values']['mean'] / 10.0
            elif layer['name'] == 'clay':
                # O valor de argila vem em g/kg, dividimos por 10 para ter %
                clay_value = layer['depths'][0]['values']['mean'] / 10.0
        
        if ph_value is not None and clay_value is not None:
            return {"ph": round(ph_value, 2), "clay": round(clay_value, 1)}
        else:
            st.warning("Não foi possível extrair os dados de solo da resposta da API.")
            return None

    except Exception as e:
        st.warning(f"Não foi possível buscar dados de solo. A análise usará valores padrão. Erro: {e}")
        return None

# As funções get_clima_data, find_all_nearest_pois e find_nearest_hub continuam as mesmas
# ... (código das outras funções aqui) ...
@st.cache_data(show_spinner=False, ttl=86400)
def get_clima_data(lat, lon):
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
    results = {
        "rodovia": {"nome": "Não encontrada", "distancia": raio_rodovia_m / 1000, "coords": None},
        "cidade": {"nome": "Não encontrada", "distancia": raio_local_m / 1000, "coords": None},
        "silo": {"nome": "Não encontrado", "distancia": raio_local_m / 1000, "coords": None}
    }
    for i, endpoint in enumerate(["https://overpass-api.de/api/interpreter", "https://lz4.overpass-api.de/api/interpreter", "https://z.overpass-api.de/api/interpreter"]):
        try:
            st.toast(f"Tentando servidor de mapas {i+1}...")
            response = requests.post(endpoint, data=query_combinada, timeout=60)
            response.raise_for_status()
            data = response.json()
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
            return results
        except (requests.exceptions.Timeout, requests.exceptions.HTTPError, json.JSONDecodeError) as e:
            st.toast(f"Servidor {i+1} falhou. Tentando o próximo...")
            continue
    st.error("Todos os servidores de mapas falharam. Tente novamente mais tarde.")
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
