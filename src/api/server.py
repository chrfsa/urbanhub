"""
UrbanHub - FastAPI Streaming Server
Smart City Data Platform

This server collects bike and pollution data in background
and provides API endpoints for real-time data access.
"""

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.streaming.collector_bikes import BikesCollector
from src.iot.collector_pollution import PollutionCollector
from src.utils.config import get_config


# Global state for streaming data
class DataStore:
    """In-memory data store for streaming data."""
    
    def __init__(self):
        self.bikes_data: List[Dict] = []
        self.bikes_timestamp: Optional[datetime] = None
        self.pollution_data: List[Dict] = []
        self.pollution_timestamp: Optional[datetime] = None
        self.bikes_history: List[Dict] = []
        self.pollution_history: List[Dict] = []
        self.lock = threading.Lock()
    
    def update_bikes(self, data: List[Dict], timestamp: datetime):
        with self.lock:
            self.bikes_data = data
            self.bikes_timestamp = timestamp
            # Keep last 60 snapshots in history (1 hour at 1min intervals)
            self.bikes_history.append({
                'timestamp': timestamp,
                'data': data
            })
            if len(self.bikes_history) > 60:
                self.bikes_history = self.bikes_history[-60:]
    
    def update_pollution(self, data: List[Dict], timestamp: datetime):
        with self.lock:
            self.pollution_data = data
            self.pollution_timestamp = timestamp
            # Keep last 6 snapshots in history (1 hour at 10min intervals)
            self.pollution_history.append({
                'timestamp': timestamp,
                'data': data
            })
            if len(self.pollution_history) > 6:
                self.pollution_history = self.pollution_history[-6:]
    
    def get_bikes(self) -> Dict:
        with self.lock:
            return {
                'data': self.bikes_data,
                'timestamp': self.bikes_timestamp.isoformat() if self.bikes_timestamp else None,
                'count': len(self.bikes_data)
            }
    
    def get_pollution(self) -> Dict:
        with self.lock:
            return {
                'data': self.pollution_data,
                'timestamp': self.pollution_timestamp.isoformat() if self.pollution_timestamp else None,
                'count': len(self.pollution_data)
            }
    
    def get_bikes_history(self) -> List[Dict]:
        with self.lock:
            return [
                {'timestamp': h['timestamp'].isoformat(), 'count': len(h['data'])}
                for h in self.bikes_history
            ]
    
    def get_pollution_history(self) -> List[Dict]:
        with self.lock:
            return [
                {'timestamp': h['timestamp'].isoformat(), 'count': len(h['data'])}
                for h in self.pollution_history
            ]


# Global data store
data_store = DataStore()

# Background collection threads
bikes_collector = None
pollution_collector = None
running = False


def collect_bikes_continuously(interval: int = 60):
    """Background thread to collect bike data."""
    global bikes_collector, running
    
    logger.info(f"Starting bikes collection thread (interval: {interval}s)")
    bikes_collector = BikesCollector()
    
    while running:
        try:
            result = bikes_collector.run_collection()
            if result.get('success'):
                # Get the latest JSON file
                bikes_dir = Path(get_config().get_data_dir('raw', 'bikes'))
                json_files = sorted(bikes_dir.glob('bikes_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
                if json_files:
                    # Read JSON Lines format (one object per line)
                    with open(json_files[0]) as f:
                        data = [json.loads(line) for line in f]
                    data_store.update_bikes(data, datetime.utcnow())
                    logger.info(f"Bikes updated: {len(data)} stations")
        except Exception as e:
            logger.error(f"Error collecting bikes: {e}")
        
        time.sleep(interval)


def collect_pollution_continuously(interval: int = 600):
    """Background thread to collect pollution data."""
    global pollution_collector, running
    
    logger.info(f"Starting pollution collection thread (interval: {interval}s)")
    pollution_collector = PollutionCollector(use_simulation=True)
    
    while running:
        try:
            result = pollution_collector.run_collection(latest_only=True)
            if result.get('success'):
                df = result.get('dataframe')
                if df is not None and not df.empty:
                    data = df.to_dict('records')
                    data_store.update_pollution(data, datetime.utcnow())
                    logger.info(f"Pollution updated: {len(data)} measurements")
        except Exception as e:
            logger.error(f"Error collecting pollution: {e}")
        
        time.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global running
    
    # Startup
    running = True
    
    # Get config
    config = get_config()
    bikes_interval = config.get('apis.citybikes.collection_interval', 60)
    pollution_interval = config.get('apis.openaq.collection_interval', 600)
    
    # Start background threads
    bikes_thread = threading.Thread(
        target=collect_bikes_continuously,
        args=(bikes_interval,),
        daemon=True
    )
    bikes_thread.start()
    
    pollution_thread = threading.Thread(
        target=collect_pollution_continuously,
        args=(pollution_interval,),
        daemon=True
    )
    pollution_thread.start()
    
    # Initial collection
    logger.info("Performing initial data collection...")
    
    # Collect bikes
    try:
        bikes_collector = BikesCollector()
        result = bikes_collector.run_collection()
        if result.get('success'):
            # Get the latest JSON file
            bikes_dir = Path(get_config().get_data_dir('raw', 'bikes'))
            json_files = sorted(bikes_dir.glob('bikes_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            if json_files:
                # Read JSON Lines format (one object per line)
                with open(json_files[0]) as f:
                    data = [json.loads(line) for line in f]
                data_store.update_bikes(data, datetime.utcnow())
                logger.info(f"Initial bikes: {len(data)} stations")
    except Exception as e:
        logger.error(f"Initial bikes collection failed: {e}")
    
    # Collect pollution
    try:
        pollution_collector = PollutionCollector(use_simulation=True)
        result = pollution_collector.run_collection(latest_only=True)
        if result.get('success'):
            df = result.get('dataframe')
            if df is not None and not df.empty:
                data = df.to_dict('records')
                data_store.update_pollution(data, datetime.utcnow())
                logger.info(f"Initial pollution: {len(data)} measurements")
    except Exception as e:
        logger.error(f"Initial pollution collection failed: {e}")
    
    logger.info("UrbanHub API server started")
    
    yield
    
    # Shutdown
    running = False
    logger.info("UrbanHub API server stopped")


# Create FastAPI app
app = FastAPI(
    title="UrbanHub API",
    description="Smart City Data Platform - Real-time Data API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "UrbanHub API",
        "version": "1.0.0",
        "description": "Smart City Data Platform",
        "endpoints": {
            "bikes": "/api/bikes",
            "bikes_stats": "/api/bikes/stats",
            "pollution": "/api/pollution",
            "pollution_stats": "/api/pollution/stats",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "bikes": data_store.bikes_timestamp.isoformat() if data_store.bikes_timestamp else None,
            "pollution": data_store.pollution_timestamp.isoformat() if data_store.pollution_timestamp else None
        }
    }


@app.get("/api/bikes")
async def get_bikes(
    city: Optional[str] = Query(None, description="Filter by city name"),
    limit: int = Query(5000, ge=1, le=10000)
):
    """Get current bike station data."""
    result = data_store.get_bikes()
    
    if not result['data']:
        raise HTTPException(status_code=404, detail="No bike data available")
    
    data = result['data']
    
    # Filter by city if specified
    if city:
        # Check both station_name and city fields
        data = [s for s in data if 
                city.lower() in s.get('station_name', '').lower() or
                city.lower() in s.get('city', '').lower()]
    
    # Limit results
    data = data[:limit]
    
    return {
        'success': True,
        'timestamp': result['timestamp'],
        'count': len(data),
        'data': data
    }


@app.get("/api/bikes/stats")
async def get_bikes_stats():
    """Get aggregated bike statistics."""
    result = data_store.get_bikes()
    
    if not result['data']:
        raise HTTPException(status_code=404, detail="No bike data available")
    
    data = result['data']
    
    # Calculate stats
    total_stations = len(data)
    total_bikes = sum(s.get('bikes_available', 0) for s in data)
    total_slots = sum(s.get('free_slots', 0) for s in data)
    
    # Find busiest stations
    stations_with_usage = [
        {
            'station_id': s.get('id'),
            'name': s.get('name'),
            'bikes': s.get('bikes_available', 0),
            'slots': s.get('free_slots', 0),
            'usage': s.get('bikes_available', 0) / (s.get('bikes_available', 0) + s.get('free_slots', 0)) * 100 if (s.get('bikes_available', 0) + s.get('free_slots', 0)) > 0 else 0
        }
        for s in data
    ]
    
    busiest = sorted(stations_with_usage, key=lambda x: x['usage'], reverse=True)[:10]
    
    return {
        'success': True,
        'timestamp': result['timestamp'],
        'stats': {
            'total_stations': total_stations,
            'total_bikes_available': total_bikes,
            'total_free_slots': total_slots,
            'utilization_rate': round(total_bikes / (total_bikes + total_slots) * 100, 2) if (total_bikes + total_slots) > 0 else 0
        },
        'busiest_stations': busiest
    }


@app.get("/api/pollution")
async def get_pollution(
    city: Optional[str] = Query(None, description="Filter by city name"),
    pollutant: Optional[str] = Query(None, description="Filter by pollutant type")
):
    """Get current pollution data."""
    result = data_store.get_pollution()
    
    if not result['data']:
        raise HTTPException(status_code=404, detail="No pollution data available")
    
    data = result['data']
    
    # Filter by city
    if city:
        data = [m for m in data if city.lower() in m.get('sensor_name', '').lower()]
    
    # Filter by pollutant
    if pollutant:
        data = [m for m in data if m.get('pollutant', '').upper() == pollutant.upper()]
    
    return {
        'success': True,
        'timestamp': result['timestamp'],
        'count': len(data),
        'data': data
    }


@app.get("/api/pollution/stats")
async def get_pollution_stats():
    """Get aggregated pollution statistics."""
    result = data_store.get_pollution()
    
    if not result['data']:
        raise HTTPException(status_code=404, detail="No pollution data available")
    
    data = result['data']
    
    # Group by pollutant
    pollutant_stats = {}
    for m in data:
        pollutant = m.get('pollutant', 'Unknown')
        if pollutant not in pollutant_stats:
            pollutant_stats[pollutant] = {'values': [], 'count': 0}
        
        value = m.get('value')
        if value is not None:
            pollutant_stats[pollutant]['values'].append(value)
            pollutant_stats[pollutant]['count'] += 1
    
    # Calculate stats per pollutant
    stats = {}
    for pollutant, info in pollutant_stats.items():
        values = info['values']
        if values:
            stats[pollutant] = {
                'count': info['count'],
                'min': round(min(values), 2),
                'max': round(max(values), 2),
                'avg': round(sum(values) / len(values), 2),
                'unit': 'μg/m³'
            }
    
    return {
        'success': True,
        'timestamp': result['timestamp'],
        'pollutants': stats,
        'total_measurements': len(data)
    }


@app.get("/api/history/bikes")
async def get_bikes_history():
    """Get bikes collection history."""
    return {
        'success': True,
        'history': data_store.get_bikes_history()
    }


@app.get("/api/history/pollution")
async def get_pollution_history():
    """Get pollution collection history."""
    return {
        'success': True,
        'history': data_store.get_pollution_history()
    }


@app.get("/api/weather")
async def get_weather(limit: int = Query(1000, ge=1, le=50000)):
    """Get weather data from parquet files."""
    try:
        weather_dir = Path(get_config().get_data_dir('bronze', 'weather'))
        if not weather_dir.exists():
            raise HTTPException(status_code=404, detail="No weather data available")
        
        all_dfs = []
        for f in weather_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(f)
                all_dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to read {f}: {e}")
        
        if not all_dfs:
            raise HTTPException(status_code=404, detail="No weather data found")
        
        df = pd.concat(all_dfs, ignore_index=True)
        df = df.head(limit)
        
        return {
            'success': True,
            'count': len(df),
            'data': df.to_dict('records')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading weather data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
