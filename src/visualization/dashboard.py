"""
UrbanHub - Complete Dashboard
Smart City Data Platform

All-in-one dashboard: Weather (Batch) + Bikes (Streaming) + Pollution (IoT)
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os
from loguru import logger

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="UrbanHub - Smart City Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============== DATA LOADING ==============

def load_weather_from_parquet() -> pd.DataFrame:
    """Load weather data from bronze layer."""
    weather_dir = Path("data/bronze/weather")
    if not weather_dir.exists():
        return pd.DataFrame()
    
    all_dfs = []
    for f in weather_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(f)
            all_dfs.append(df)
        except Exception as e:
            logger.warning(f"Failed to read {f}: {e}")
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


def fetch_bikes_from_api(city: Optional[str] = None) -> pd.DataFrame:
    """Fetch bikes data from API."""
    try:
        url = f"{API_BASE}/api/bikes"
        if city:
            url += f"?city={city}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json().get('data', [])
            if data:
                return pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"Failed to fetch bikes: {e}")
    return pd.DataFrame()


def fetch_pollution_from_api() -> pd.DataFrame:
    """Fetch pollution data from API."""
    try:
        response = requests.get(f"{API_BASE}/api/pollution", timeout=10)
        if response.status_code == 200:
            data = response.json().get('data', [])
            if data:
                return pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"Failed to fetch pollution: {e}")
    return pd.DataFrame()


def fetch_bikes_stats() -> Dict:
    """Fetch bikes stats from API."""
    try:
        response = requests.get(f"{API_BASE}/api/bikes/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch bikes stats: {e}")
    return {}


def fetch_pollution_stats() -> Dict:
    """Fetch pollution stats from API."""
    try:
        response = requests.get(f"{API_BASE}/api/pollution/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch pollution stats: {e}")
    return {}


# ============== PAGE: OVERVIEW ==============

def show_overview():
    st.title("🏙️ UrbanHub - Vue d'Ensemble")
    st.markdown("---")
    
    # Fetch all data
    bikes_df = fetch_bikes_from_api()
    pollution_df = fetch_pollution_from_api()
    weather_df = load_weather_from_parquet()
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🌤️ Stations Météo", len(weather_df) if not weather_df.empty else "N/A")
    
    with col2:
        st.metric("🚲 Stations Vélos", len(bikes_df) if not bikes_df.empty else "N/A")
    
    with col3:
        st.metric("🌫️ Capteurs Pollution", len(pollution_df) if not pollution_df.empty else "N/A")
    
    with col4:
        st.metric("🏙️ Villes", "10")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚲 Top 10 Stations - Vélos Disponibles")
        if not bikes_df.empty and 'bikes_available' in bikes_df.columns:
            # Use station_id or name as the label
            label_col = 'name' if 'name' in bikes_df.columns else ('station_id' if 'station_id' in bikes_df.columns else bikes_df.columns[0])
            cols_to_use = ['bikes_available', label_col]
            if 'free_slots' in bikes_df.columns:
                cols_to_use.append('free_slots')
            top = bikes_df.nlargest(10, 'bikes_available')[cols_to_use]
            fig = px.bar(top, x='bikes_available', y=label_col, orientation='h',
                        title="Stations avec le plus de vélos",
                        color='bikes_available', color_continuous_scale='Greens')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("En attente de données bikes...")
    
    with col2:
        st.subheader("🌫️ Niveaux de Pollution par Polluant")
        if not pollution_df.empty:
            poll_stats = pollution_df.groupby('pollutant')['value'].mean().reset_index()
            fig = px.bar(poll_stats, x='pollutant', y='value',
                        title="Moyenne des polluants (μg/m³)",
                        color='value', color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig, use_container_width=True)
    
    # Weather chart
    if not weather_df.empty and 'temperature' in weather_df.columns:
        weather_df['temperature'] = pd.to_numeric(weather_df['temperature'], errors='coerce')
        st.markdown("---")
        st.subheader("🌡️ Distribution des Températures")
        temp_data = weather_df.dropna(subset=['temperature'])
        if not temp_data.empty:
            fig = px.histogram(temp_data, x='temperature',
                              nbins=30, title="Températures en France",
                              labels={'temperature': 'Température (°C)'})
            st.plotly_chart(fig, use_container_width=True)


# ============== PAGE: WEATHER (BATCH) ==============

def show_weather():
    st.title("🌤️ Météo - Données Historiques (Batch)")
    st.markdown("---")
    
    weather_df = load_weather_from_parquet()
    
    if weather_df.empty:
        st.warning("Aucune donnée météo chargée. Lancez d'abord le traitement des données météo.")
        return
    
    # Convert numeric columns
    for col in ['temperature', 'wind_speed', 'pressure', 'visibility', 'precipitation']:
        if col in weather_df.columns:
            weather_df[col] = pd.to_numeric(weather_df[col], errors='coerce')
    
    st.success(f"✅ {len(weather_df)} enregistrements chargés")
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    
    if 'temperature' in weather_df.columns:
        # Filter out invalid temperatures (NOAA uses 999.9 for missing)
        weather_df = weather_df[(weather_df['temperature'] > -50) & (weather_df['temperature'] < 50)]
        
        with col1:
            st.metric("Température Moyenne", f"{weather_df['temperature'].mean():.1f}°C")
        with col2:
            st.metric("Température Max", f"{weather_df['temperature'].max():.1f}°C")
        with col3:
            st.metric("Température Min", f"{weather_df['temperature'].min():.1f}°C")
    
    if 'wind_speed' in weather_df.columns:
        with col4:
            st.metric("Vitesse Vent Moy", f"{weather_df['wind_speed'].mean():.1f} m/s")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌡️ Températures par Station")
        if 'station_id' in weather_df.columns and 'temperature' in weather_df.columns:
            # Convert to numeric
            weather_df['temperature'] = pd.to_numeric(weather_df['temperature'], errors='coerce')
            station_temp = weather_df.groupby('station_id')['temperature'].mean().nlargest(20)
            if not station_temp.empty:
                fig = px.bar(x=station_temp.values, y=station_temp.index, orientation='h',
                            title="Top 20 Stations - Température Moyenne")
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💨 Vitesse du Vent")
        if 'wind_speed' in weather_df.columns:
            weather_df['wind_speed'] = pd.to_numeric(weather_df['wind_speed'], errors='coerce')
            wind_data = weather_df.dropna(subset=['wind_speed'])
            if not wind_data.empty:
                fig = px.histogram(wind_data, x='wind_speed',
                                  nbins=30, title="Distribution Vitesse du Vent")
                st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("📊 Données Météo")
    cols = ['station_id', 'timestamp', 'temperature', 'wind_speed', 'pressure', 'visibility']
    available = [c for c in cols if c in weather_df.columns]
    st.dataframe(weather_df[available].head(100), use_container_width=True)


# ============== PAGE: BIKES (STREAMING) ==============

def show_bikes():
    st.title("🚲 Vélos - Temps Réel (Streaming)")
    st.markdown("---")
    
    # City filter
    cities = ["Tous", "Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", 
              "Nantes", "Strasbourg", "Montpellier", "Nice", "Lille"]
    city = st.selectbox("Ville", cities)
    
    bikes_df = fetch_bikes_from_api(city if city != "Tous" else None)
    stats = fetch_bikes_stats()
    
    if bikes_df.empty:
        st.warning("Aucune donnée bikes disponible. Vérifiez que le serveur API tourne.")
        return
    
    # Stats
    if stats.get('success'):
        s = stats.get('stats', {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Stations Total", s.get('total_stations', 0))
        with col2:
            st.metric("Vélos Disponibles", s.get('total_bikes_available', 0))
        with col3:
            st.metric("Places Libres", s.get('total_free_slots', 0))
        with col4:
            st.metric("Taux Utilisation", f"{s.get('utilization_rate', 0)}%")
    
    st.markdown("---")
    
    # Map
    st.subheader("🗺️ Carte des Stations")
    if 'latitude' in bikes_df.columns and 'longitude' in bikes_df.columns:
        bikes_df['lat'] = bikes_df['latitude']
        bikes_df['lon'] = bikes_df['longitude']
        
        hover_col = 'station_name' if 'station_name' in bikes_df.columns else 'station_id'
        
        fig = px.scatter_mapbox(bikes_df.head(200), lat='lat', lon='lon',
                               size='bikes_available', color='bikes_available',
                               hover_name=hover_col, zoom=5, center={"lat": 46.6, "lon": 2.5},
                               mapbox_style="carto-positron",
                               title="Stations de vélos en France")
        st.plotly_chart(fig, use_container_width=True)
    
    # Tables
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚴 Stations les Plus Utilisées")
        if stats.get('success'):
            busiest = pd.DataFrame(stats.get('busiest_stations', []))
            if not busiest.empty:
                st.dataframe(busiest[['name', 'bikes', 'slots', 'usage']].head(10), use_container_width=True)
    
    with col2:
        st.subheader("📋 Toutes les Stations")
        display_cols = ['station_name', 'station_id', 'latitude', 'longitude', 'bikes_available', 'free_slots']
        avail = [c for c in display_cols if c in bikes_df.columns]
        st.dataframe(bikes_df[avail].head(20), use_container_width=True)


# ============== PAGE: POLLUTION (IOT) ==============

def show_pollution():
    st.title("🌫️ Pollution - Temps Réel (IoT)")
    st.markdown("---")
    
    pollution_df = fetch_pollution_from_api()
    stats = fetch_pollution_stats()
    
    if pollution_df.empty:
        st.warning("Aucune donnée pollution disponible.")
        return
    
    # Stats
    if stats.get('success'):
        pollutants = stats.get('pollutants', {})
        
        cols = st.columns(len(pollutants))
        for i, (name, s) in enumerate(pollutants.items()):
            with cols[i]:
                st.metric(name, f"{s.get('avg', 0):.1f} {s.get('unit', '')}",
                         f"Max: {s.get('max', 0)}")
    
    st.markdown("---")
    
    # Map
    st.subheader("🗺️ Carte de la Pollution")
    if 'latitude' in pollution_df.columns and 'longitude' in pollution_df.columns:
        fig = px.scatter_mapbox(pollution_df, lat='latitude', lon='longitude',
                               size='value', color='value',
                               hover_name='sensor_name', zoom=5, center={"lat": 46.6, "lon": 2.5},
                               mapbox_style="carto-positron",
                               title="Capteurs de Pollution en France")
        st.plotly_chart(fig, use_container_width=True)
    
    # By city
    st.subheader("🏙️ Pollution par Ville")
    if 'sensor_name' in pollution_df.columns:
        pollution_df['city'] = pollution_df['sensor_name'].apply(lambda x: x.split(' - ')[0] if ' - ' in str(x) else 'Unknown')
        city_poll = pollution_df.groupby('city')['value'].mean().reset_index()
        fig = px.bar(city_poll, x='city', y='value', title="Pollution Moyenne par Ville",
                    color='value', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig, use_container_width=True)
    
    # Data
    st.subheader("📊 Données")
    st.dataframe(pollution_df, use_container_width=True)


# ============== PAGE: ANALYSES ==============

def show_analyses():
    st.title("📈 Analyses Croisées")
    st.markdown("---")
    
    bikes_df = fetch_bikes_from_api()
    pollution_df = fetch_pollution_from_api()
    weather_df = load_weather_from_parquet()
    
    st.info("💡 Cette page combine les trois sources de données pour des analyses approfondies.")
    
    # Analysis 1: Weather vs Pollution
    st.subheader("1. Corrélation Météo vs Pollution")
    
    if not pollution_df.empty and not weather_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Pollution par type de polluant**")
            poll_by_type = pollution_df.groupby('pollutant')['value'].mean()
            fig = go.Figure(data=[go.Pie(labels=poll_by_type.index, values=poll_by_type.values,
                                         title="Distribution Polluants")])
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("**Températures enregistrées**")
            if 'temperature' in weather_df.columns:
                fig = px.box(weather_df.dropna(subset=['temperature']), y='temperature',
                           title="Boxplot Températures")
                st.plotly_chart(fig, use_container_width=True)
    
    # Analysis 2: Bike Usage Patterns
    st.markdown("---")
    st.subheader("2. Patterns d'Utilisation des Vélos")
    
    if not bikes_df.empty:
        # Usage rate
        bikes_df['total'] = bikes_df['bikes_available'] + bikes_df['free_slots']
        bikes_df['usage_rate'] = bikes_df['bikes_available'] / bikes_df['total'] * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(bikes_df, x='usage_rate', nbins=20,
                              title="Distribution Taux d'Utilisation")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Dynamic column for station name
            name_col = 'station_name' if 'station_name' in bikes_df.columns else ('name' if 'name' in bikes_df.columns else 'station_id')
            critical_cols = [name_col, 'bikes_available', 'free_slots']
            critical = bikes_df.nsmallest(10, 'bikes_available')[critical_cols]
            st.dataframe(critical, use_container_width=True)
    
    # Analysis 3: Pollution hotspots
    st.markdown("---")
    st.subheader("3. Zones à Risque de Pollution")
    
    if not pollution_df.empty:
        # High pollution areas
        if 'value' in pollution_df.columns:
            high_poll = pollution_df.nlargest(10, 'value')[['sensor_name', 'pollutant', 'value']]
            st.write("**Top 10 mesures élevées de pollution**")
            st.dataframe(high_poll, use_container_width=True)
            
            # Threshold alerts
            thresholds = {'PM2.5': 25, 'PM10': 50, 'O3': 120, 'NO2': 40}
            alerts = []
            for _, row in pollution_df.iterrows():
                pollutant = row.get('pollutant')
                value = row.get('value')
                if pollutant in thresholds and value > thresholds[pollutant]:
                    alerts.append(row)
            
            if alerts:
                st.warning(f"⚠️ {len(alerts)} dépassements de seuils détectés!")
                st.dataframe(pd.DataFrame(alerts)[['sensor_name', 'pollutant', 'value']], use_container_width=True)
            else:
                st.success("✅ Tous les niveaux de pollution sont dans les normes.")


# ============== MAIN ==============

def main():
    # Sidebar
    st.sidebar.title("🏙️ UrbanHub")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio("Navigation",
        ["Vue d'Ensemble", "Météo (Batch)", "Vélos (Streaming)", "Pollution (IoT)", "Analyses"])
    
    # API Status
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        if r.status_code == 200:
            st.sidebar.success("🟢 API Connectée")
        else:
            st.sidebar.warning("🟡 API Déconnectée")
    except:
        st.sidebar.error("🔴 API Inaccessible")
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"UrbanHub v1.0\nMis à jour: {datetime.now().strftime('%H:%M:%S')}")
    
    # Show page
    if page == "Vue d'Ensemble":
        show_overview()
    elif page == "Météo (Batch)":
        show_weather()
    elif page == "Vélos (Streaming)":
        show_bikes()
    elif page == "Pollution (IoT)":
        show_pollution()
    elif page == "Analyses":
        show_analyses()


if __name__ == "__main__":
    main()
