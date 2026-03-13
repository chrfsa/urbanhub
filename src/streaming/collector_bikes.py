"""
UrbanHub - Collect Bikes Data
Smart City Data Platform

Collect real-time bike sharing data from CityBikes API
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

import requests
import pandas as pd
from loguru import logger

from ..utils.config import get_config
from ..utils.dates import format_timestamp


class BikesCollector:
    """Collect bike sharing data from CityBikes API."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize bikes collector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config().get("apis.citybikes", {})
        self.base_url = self.config.get("base_url", "https://api.citybik.es/v2/")
        self.timeout = self.config.get("timeout", 10)
        self.cities = self.config.get("cities", [])
        self.output_dir = Path(get_config().get_data_dir("raw", "bikes"))
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for connection pooling
        self.session = requests.Session()
        
    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """
        Make API request.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            JSON response
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def get_networks(self) -> List[Dict]:
        """
        Get all bike networks.
        
        Returns:
            List of network dictionaries
        """
        data = self._make_request("networks")
        
        if data and 'networks' in data:
            return data['networks']
        
        return []
    
    def get_france_networks(self) -> List[Dict]:
        """
        Get bike networks in France.
        
        Returns:
            List of French networks
        """
        all_networks = self.get_networks()
        
        france_networks = [
            n for n in all_networks 
            if n.get('location', {}).get('country', '').upper() == 'FR'
        ]
        
        logger.info(f"Found {len(france_networks)} French bike networks")
        return france_networks
    
    def get_network_stations(self, network_id: str) -> List[Dict]:
        """
        Get stations for a specific network.
        
        Args:
            network_id: Network ID
            
        Returns:
            List of station dictionaries
        """
        endpoint = f"networks/{network_id}?fields=stations"
        data = self._make_request(endpoint)
        
        if data and 'network' in data:
            return data['network'].get('stations', [])
        
        return []
    
    def collect_station_data(self, station: Dict, network_info: Dict) -> Dict:
        """
        Extract relevant data from a station.
        
        Args:
            station: Station dictionary from API
            network_info: Network information
            
        Returns:
            Extracted station data
        """
        # Extract location
        location = station.get('location', {})
        position = station.get('position', {})
        
        # Extract timestamp
        timestamp = datetime.now()
        
        return {
            'station_id': station.get('id', ''),
            'station_name': station.get('name', ''),
            'network_id': network_info.get('id', ''),
            'network_name': network_info.get('name', ''),
            'city': network_info.get('location', {}).get('city', ''),
            'country': network_info.get('location', {}).get('country', ''),
            'latitude': position.get('latitude') or location.get('latitude'),
            'longitude': position.get('longitude') or location.get('longitude'),
            'bikes_available': station.get('free_bikes', 0),
            'empty_slots': station.get('empty_slots', 0),
            'free_slots': station.get('empty_slots', 0),
            'total_slots': station.get('free_bikes', 0) + station.get('empty_slots', 0),
            'timestamp': timestamp.isoformat(),
            'timestamp_unix': int(timestamp.timestamp())
        }
    
    def collect_all_data(self, cities: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Collect data from all or specific cities.
        
        Args:
            cities: List of cities to collect from (None = all France)
            
        Returns:
            DataFrame with all station data
        """
        target_cities = cities or self.cities
        
        logger.info(f"Collecting bike data for: {target_cities}")
        
        all_stations = []
        france_networks = self.get_france_networks()
        
        for network in france_networks:
            city = network.get('location', {}).get('city', '')
            
            # Filter by cities if specified - use case-insensitive partial match
            if target_cities:
                city_match = any(city.lower() in c.lower() or c.lower() in city.lower() for c in target_cities)
                if not city_match:
                    continue
            
            logger.debug(f"Fetching network: {network.get('name')} - {city}")
            
            stations = self.get_network_stations(network.get('id', ''))
            
            for station in stations:
                station_data = self.collect_station_data(station, network)
                all_stations.append(station_data)
        
        df = pd.DataFrame(all_stations)
        
        logger.info(f"Collected {len(df)} stations")
        return df
    
    def save_raw_data(self, df: pd.DataFrame) -> Path:
        """
        Save raw data to JSON.
        
        Args:
            df: DataFrame to save
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bikes_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Save as JSON
        df.to_json(filepath, orient='records', lines=True)
        
        logger.info(f"Saved raw data to {filepath}")
        return filepath
    
    def append_to_parquet(self, df: pd.DataFrame) -> None:
        """
        Append data to Parquet file.
        
        Args:
            df: DataFrame to append
        """
        if df.empty:
            return
        
        silver_dir = get_config().get_data_dir("silver", "bikes")
        silver_dir.mkdir(parents=True, exist_ok=True)
        
        # Partition by date
        date = datetime.now().strftime("%Y-%m-%d")
        filepath = silver_dir / f"date={date}" / "bikes.parquet"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if filepath.exists():
            # Append to existing file
            existing = pd.read_parquet(filepath)
            combined = pd.concat([existing, df], ignore_index=True)
            combined.to_parquet(filepath, index=False)
        else:
            df.to_parquet(filepath, index=False)
        
        logger.debug(f"Appended {len(df)} rows to {filepath}")
    
    def get_current_state(self) -> pd.DataFrame:
        """
        Get current state of all stations.
        
        Returns:
            DataFrame with latest state
        """
        return self.collect_all_data()
    
    def run_collection(self) -> Dict[str, Any]:
        """
        Run one collection cycle.
        
        Returns:
            Collection results
        """
        start_time = datetime.now()
        
        try:
            df = self.collect_all_data()
            
            if not df.empty:
                self.save_raw_data(df)
                # Skip parquet for now (PyArrow bug)
                # try:
                #     self.append_to_parquet(df)
                # except Exception as e:
                #     logger.warning(f"Parquet save failed: {e}")
                
            return {
                "success": True,
                "timestamp": start_time.isoformat(),
                "stations_collected": len(df),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            return {
                "success": False,
                "timestamp": start_time.isoformat(),
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }


def run_collector() -> Dict[str, Any]:
    """
    Run bikes data collector.
    
    Returns:
        Collection results
    """
    collector = BikesCollector()
    return collector.run_collection()


if __name__ == "__main__":
    logger.info("Starting bikes data collection")
    results = run_collector()
    logger.info(f"Collection complete: {results}")
