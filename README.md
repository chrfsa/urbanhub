# UrbanHub - Smart City Data Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.30+-red.svg" alt="Streamlit">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Architecture-Batch%20%7C%20Streaming%20%7C%20IoT-orange.svg" alt="Data Sources">
</p>

## 📋 Overview

**UrbanHub** is a comprehensive Smart City data platform that collects, processes, and analyzes urban data from multiple sources to produce actionable insights for public decision-makers.

The platform ingests three types of data streams typical of real-world Big Data systems:

| Data Type | Source | Description |
|-----------|--------|-------------|
| **Batch** | NOAA Weather | Historical meteorological data from 1990 |
| **Streaming** | CityBikes API | Real-time bike sharing station data |
| **IoT** | OpenAQ API | Air pollution sensor measurements |

---

## 🏗️ Architecture

```
Sources de données
      │
      ▼
Ingestion (API / HTTP)
      │
      ▼
Stockage Data Lake (Parquet)
      │
      ▼
Traitement ETL
      │
      ▼
Analyse Data / IA
      │
      ▼
Dashboard & API
```

### Data Pipeline

```
Raw Data (CSV/JSON) → Bronze (Parquet) → Silver (Cleaned) → Gold (Aggregates)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd urban_data

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Platform

#### Option 1: Run Individual Components

```bash
# 1. Download weather data (Batch)
python run_weather_download.py

# 2. Collect bike data (Streaming)
python run_bikes_collector.py

# 3. Collect pollution data (IoT)
python run_pollution_collector.py

# 4. Start API server
python run_api_server.py

# 5. Launch dashboard
streamlit run src/visualization/dashboard.py
```

#### Option 2: Run All Components

```bash
# Make script executable
chmod +x run_all.sh

# Run all collectors
./run_all.sh
```

---

## 📁 Project Structure

```
urban_data/
├── config/                    # Configuration files
│   └── config.yaml           # Main configuration
├── data/                     # Data storage (Data Lake)
│   ├── raw/                 # Raw data (CSV/JSON)
│   │   ├── weather/         # NOAA weather files
│   │   ├── bikes/           # CityBikes JSON files
│   │   └── pollution/       # OpenAQ JSON files
│   ├── bronze/              # Raw Parquet files
│   ├── silver/              # Cleaned Parquet files
│   └── gold/                # Aggregated data
├── src/
│   ├── batch/               # Batch data collection (weather)
│   │   └── collector_weather.py
│   ├── streaming/           # Streaming data collection (bikes)
│   │   └── collector_bikes.py
│   ├── iot/                 # IoT data collection (pollution)
│   │   └── collector_pollution.py
│   ├── api/                 # FastAPI server
│   │   └── server.py
│   ├── analysis/            # Data analysis scripts
│   ├── visualization/       # Streamlit dashboard
│   │   └── dashboard.py
│   └── utils/               # Utilities (logger, storage, config)
├── notebooks/               # Jupyter notebooks for EDA
├── tests/                   # Unit tests
├── SPEC.md                  # Technical specification
├── README.md                # This file
└── run_*.py                # Entry point scripts
```

---

## 📊 Features

### 1. Weather Data (Batch)

- **Source**: NOAA Global Hourly Weather Data
- **Coverage**: France stations from 1990
- **Variables**:
  - `station_id`, `timestamp`
  - `temperature`, `wind_speed`, `wind_direction`
  - `pressure`, `precipitation`, `visibility`

**Business Questions**:
- Identify abnormal weather periods
- Correlation between weather conditions and visibility
- Seasonal temperature evolution in major French cities
- Days with extreme weather conditions

### 2. Bike Sharing (Streaming)

- **Source**: CityBikes API
- **Coverage**: Major French cities (Paris, Lyon, Marseille, etc.)
- **Variables**:
  - `station_id`, `station_name`
  - `latitude`, `longitude`
  - `bikes_available`, `free_slots`
  - `timestamp`

**Business Questions**:
- Stations with highest usage rate
- Zones with insufficient bike supply
- Daily usage peaks
- Geographic imbalances in bike availability
- Critical stations requiring rebalancing

### 3. Air Pollution (IoT)

- **Source**: OpenAQ API
- **Coverage**: French cities
- **Pollutants**: PM2.5, PM10, O3, NO2, CO
- **Variables**:
  - `sensor_id`, `pollutant`
  - `latitude`, `longitude`
  - `value`, `unit`, `timestamp`

**Business Questions**:
- Areas with highest pollution levels
- Daily pollution variation
- Dominant pollutants in studied cities
- Abnormal pollution episodes

### 4. Cross-Analysis

- Relationship between weather conditions and pollution
- Weather influence on bike usage
- Favorable conditions for soft mobility
- Periods with strong interaction between mobility, pollution, and weather

---

## ⚙️ Configuration

Edit `config/config.yaml` or `.env`:

```yaml
# Data Collection
weather:
  start_year: 1990
  stations:
    - "07765099999"  # Paris-Orly
    - "07607099999"  # Bordeaux
    - "07386099999"  # Lyon

bikes:
  cities:
    - "Paris"
    - "Lyon"
    - "Marseille"
  collection_interval: 600  # seconds

pollution:
  country: "FR"
  collection_interval: 3600  # seconds
```

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| Data Processing | pandas, pyarrow, polars |
| API Server | FastAPI, uvicorn |
| Dashboard | Streamlit |
| Storage | Parquet files (no database required) |
| Logging | Python logging |
| HTTP Client | aiohttp, requests |

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 👥 Authors

- **Said** - Initial work

---

## 🙏 Acknowledgments

- [NOAA](https://www.ncei.noaa.gov/) - Weather data
- [CityBikes](https://api.citybik.es/) - Bike sharing data
- [OpenAQ](https://openaq.org/) - Air quality data
