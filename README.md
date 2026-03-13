# UrbanHub - Smart City Data Platform

**UrbanHub** is a data platform for collecting, processing, and analyzing urban data from multiple sources:
- Weather data (NOAA)
- Bike sharing data (CityBikes API)
- Air pollution data (OpenAQ API)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
cd urban_data

# Install uv if not installed
# pip install uv

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Create data directories
mkdir -p data/{raw/{weather,bikes,pollution},bronze,silver,gold}
```

### Running the Platform

#### 1. Weather Data (Batch) - Download NOAA data
```bash
python run_weather_download.py
```

#### 2. Bike Data (Streaming) - Collect from CityBikes
```bash
python run_bikes_collector.py
```

#### 3. Pollution Data (IoT) - Collect from OpenAQ
```bash
python run_pollution_collector.py
```

#### 4. Dashboard
```bash
streamlit run src/visualization/dashboard.py
```

## 📁 Project Structure

```
urban_data/
├── config/              # Configuration files
├── data/                # Data storage (bronze/silver/gold)
├── docker/              # Docker configuration
├── notebooks/           # Jupyter notebooks
├── src/
│   ├── batch/          # Batch data collection (weather)
│   ├── streaming/      # Streaming data (bikes)
│   ├── iot/            # IoT data (pollution)
│   ├── etl/            # ETL utilities
│   ├── analysis/       # Data analysis
│   ├── visualization/  # Dashboard
│   └── utils/          # Utilities
├── tests/              # Tests
├── SPEC.md            # Technical specification
├── README.md          # This file
└── run_*.py           # Entry point scripts
```

## 📝 Entry Point Scripts

| Script | Purpose |
|--------|---------|
| `run_weather_download.py` | Download NOAA weather data (2020-2024) |
| `run_bikes_collector.py` | Collect bike data from CityBikes API |
| `run_pollution_collector.py` | Collect pollution data from OpenAQ |

## 🔧 Configuration

Edit `config/config.yaml` or `.env` to customize:
- API endpoints
- Collection intervals
- Data paths
- Thresholds

## 📊 Features

### Weather Analysis
- Historical data from 1990
- Temperature, wind, pressure, precipitation
- Anomaly detection
- Seasonal trends

### Bike Sharing
- Real-time station data
- Usage patterns
- Rebalancing alerts

### Air Pollution
- PM2.5, PM10, O3, NO2, CO
- Threshold alerts
- Geographic analysis

### Cross-Analysis
- Weather-Pollution correlation
- Weather-Bike usage correlation
- Favorable conditions analysis

## ⚠️ Note

PostgreSQL is NOT required - the project uses Parquet files for data storage, which is simpler and performant.

## 📝 License

MIT License
