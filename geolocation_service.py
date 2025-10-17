# geolocation_service.py

import requests
from geopy.distance import geodesic
import streamlit as st
import json
from datetime import datetime

# --- APIs (APENAS PARA CLIMA E SOLO) ---
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

# --- BANCO DE DADOS INTERNO DE RODOVIAS (SIMPLIFICADO E ROBUSTO) ---
RODOVIAS_DB = {
    # Federais Eixo Norte-Sul
    "BR-153 (Transbrasiliana)": [(-16.68, -49.25), (-17.73, -49.24), (-18.52, -49.19), (-20.81, -49.38), (-23.21, -47.67)],
    "BR-163 (Cuiabá-Santarém)": [(-16.33, -54.69), (-15.60, -56.09), (-13.05, -55.90), (-12.54, -55.71), (-11.86, -55.50), (-22.22, -54.80), (-24.95, -53.45)],
    "BR-158": [(-15.89, -52.36), (-17.13, -52.96), (-18.44, -50.45), (-29.08, -53.84), (-31.77, -52.33)],
    # Federais Eixo Leste-Oeste
    "BR-060 (Brasília-Mato Grosso do Sul)": [(-15.79, -47.88), (-16.68, -49.25), (-17.79, -50.93), (-20.44, -54.64)],
    "BR-364 (Sudeste a Noroeste)": [(-22.72, -47.64), (-18.91, -48.27), (-17.88, -51.71), (-16.33, -54.69), (-15.60, -56.09), (-8.76, -63.90)],
    "BR-242 (Bahia-Mato Grosso)": [(-12.97, -38.50), (-12.09, -45.80), (-13.01, -48.33), (-13.29, -51.85), (-12.54, -55.71)],
    "BR-050 (Brasília-Santos)": [(-15.79, -47.88), (-18.17, -47.96), (-18.91, -48.27), (-19.74, -47.93), (-22.90, -47.06), (-23.93, -46.33)],
    # Estaduais Relevantes (GO, MT, BA, SP)
    "GO-070": [(-16.68, -49.25), (-16.20, -51.22)],
    "GO-164": [(-18.44, -50.45), (-17.79, -50.93), (-14.74, -50.57)],
    "MT-130": [(-16.47, -54.63), (-15.55, -54.29)],
    "BA-052 (Estrada do Feijão)": [(-12.91, -41.48), (-11.40, -43.12)],
    "SP-330 (Anhanguera)": [(-20.53, -47.39), (-22.90, -47.06), (-23.55, -46.63)],
    "SP-348 (Bandeirantes)": [(-22.72, -47.64), (-23.55, -46.63)],
    "SP-310 (Washington Luís)": [(-21.28, -48.31), (-22.21, -47.98)],
}

# --- Constantes (HUBS_AGRO e FALLBACK) ---
HUBS_AGRO = {
    "Sorriso (MT)": (-12.5447, -55.7126), "Rio Verde (GO)": (-17.7972, -50.9262),
    "Sapezal (MT)": (-13.5428, -58.8744), "Jataí (GO)": (-17.8814, -51.7144),
    "São Desidério (BA
