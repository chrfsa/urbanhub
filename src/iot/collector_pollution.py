"""
UrbanHub - Collect Pollution Data
Smart City Data Platform

Collect air pollution data from OpenAQ API or use simulated data
"""

import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

import requests
import pandas as pd
from loguru import logger

from ..utils.config import get_config
from ..utils.dates import format_timestamp


@dataclass
class PollutionCollector:
    """Collect air pollution data from OpenAQ API or simulated."""
    
    def __init__(self, config: Optional[Dict] = None, use_simulation: bool = True):
        """
        Initialize pollution collector.
        
        Args:
            config: Configuration dictionary
            use_simulation: Use simulated data if API fails
        """
        self.config = config or get_config().get("apis.openaq", {})
        self.base_url = self.config.get("base_url", "https://api.openaq.org/v3/")
        self.timeout = self.config.get("timeout", 15)
        self.countries = self.config.get("countries", ["FR"])
        self.pollutants = self.config.get("pollutants", ["PM2.5", "PM10", "O3", "NO2", "CO"])
        self.limit = self.config.get("limit", 1000)
        self.use_simulation = use_simulation
        
        self.output_dir = Path(get_config().get_data_dir("raw", "pollution"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        
        api_key = self.config.get("api_key")
        if api_key:
            # OpenAQ v3 uses X-API-Key header
            self.session.headers.update({"X-API-Key": api_key})
            logger.info(f"Using OpenAQ API key: {api_key[:10]}...")
        else:
            logger.warning("No OpenAQ API key found in config")
        
        # French cities with coordinates for simulation
        self.french_cities = {
            "Paris": {"lat": 48.8566, "lon": 2.3522},
            "Lyon": {"lat": 45.7640, "lon": 4.8357},
            "Marseille": {"lat": 43.2965, "lon": 5.3698},
            "Toulouse": {"lat": 43.6047, "lon": 1.4442},
            "Bordeaux": {"lat": 44.8378, "lon": -0.5792},
            "Nantes": {"lat": 47.2184, "lon": -1.5536},
            "Strasbourg": {"lat": 48.5734, "lon": 7.7521},
            "Montpellier": {"lat": 43.6108, "lon": 3.8767},
            "Nice": {"lat": 43.7102, "lon": 7.2620},
            "Lille": {"lat": 50.6292, "lon": 3.0573},
        }
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make API request."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"API request failed: {e}")
            return None
    
    def _generate_simulated_measurements(self) -> List[Dict]:
        """Generate realistic simulated pollution data for French cities."""
        measurements = []
        now = datetime.utcnow()
        
        for city, coords in self.french_cities.items():
            # Base pollution levels (vary by city type)
            base_levels = {
                "PM2.5": random.uniform(5, 35),
                "PM10": random.uniform(10, 50),
                "O3": random.uniform(20, 80),
                "NO2": random.uniform(10, 45),
                "CO": random.uniform(200, 800),
            }
            
            # Add some randomness
            for pollutant, base_value in base_levels.items():
                value = base_value * random.uniform(0.8, 1.5)
                
                measurements.append({
                    "location": f"{city} - {pollutant}",
                    "city": city,
                    "country": "FR",
                    "coordinates": {
                        "latitude": coords["lat"] + random.uniform(-0.05, 0.05),
                        "longitude": coords["lon"] + random.uniform(-0.05, 0.05),
                    },
                    "parameter": {
                        "id": hash(pollutant) % 1000,
                        "name": pollutant,
                        "unit": "μg/m³" if pollutant != "CO" else "μg/m³",
                        "average": True,
                    },
                    "value": round(value, 2),
                    "datetime": now.isoformat() + "Z",
                    "timestamp": now.timestamp(),
                })
        
        return measurements
    
    def get_measurements(
        self,
        country: str = "FR",
        city: Optional[str] = None,
        pollutant: Optional[str] = None,
        limit: int = 1000,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """Get measurements from OpenAQ API."""
        params = {
            "country": country,
            "limit": limit,
            "order_by": "datetime",
            "sort": "desc"
        }
        
        if city:
            params["city"] = city
        
        if pollutant:
            params["pollutant"] = pollutant
        
        if date_from:
            params["date_from"] = date_from.isoformat()
        
        if date_to:
            params["date_to"] = date_to.isoformat()
        
        data = self._make_request("measurements", params)
        
        if data and 'results' in data:
            return data['results']
        
        # Fallback to simulation
        if self.use_simulation:
            logger.info("Using simulated pollution data")
            return self._generate_simulated_measurements()
        
        return []
    
    def get_latest_measurements(
        self,
        country: str = "FR",
        limit: int = 1000
    ) -> List[Dict]:
        """Get latest measurements."""
        params = {
            "country": country,
            "limit": limit
        }
        
        data = self._make_request("latest", params)
        
        if data and 'results' in data:
            return data['results']
        
        # Fallback to simulation
        if self.use_simulation:
            logger.info("Using simulated pollution data")
            return self._generate_simulated_measurements()
        
        return []
    
    def get_locations(
        self,
        country: str = "FR",
        limit: int = 1000
    ) -> List[Dict]:
        """Get sensor locations."""
        params = {
            "country": country,
            "limit": limit
        }
        
        data = self._make_request("locations", params)
        
        if data and 'results' in data:
            return data['results']
        
        # Return simulated locations
        if self.use_simulation:
            return [
                {
                    "location": f"{city} - Sensor",
                    "city": city,
                    "country": "FR",
                    "coordinates": coords,
                    "parameters": ["PM2.5", "PM10", "O3", "NO2", "CO"],
                }
                for city, coords in self.french_cities.items()
            ]
        
        return []
    
    def collect_measurement_data(self, measurement: Dict) -> Dict:
        """Extract relevant data from a measurement."""
        location = measurement.get('location', 'Unknown')
        coordinates = measurement.get('coordinates', {})
        parameter = measurement.get('parameter', {})
        datetime_str = measurement.get('datetime', '')
        
        return {
            'sensor_id': measurement.get('id', location),
            'sensor_name': location,
            'latitude': coordinates.get('latitude') if coordinates else None,
            'longitude': coordinates.get('longitude') if coordinates else None,
            'pollutant': parameter.get('name', 'Unknown') if parameter else 'Unknown',
            'value': measurement.get('value'),
            'unit': parameter.get('unit', 'μg/m³') if parameter else 'μg/m³',
            'timestamp': datetime_str,
        }
    
    def collect_all_data(
        self,
        countries: Optional[List[str]] = None,
        use_simulation: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Collect all pollution data."""
        countries = countries or self.countries
        use_simulation = use_simulation if use_simulation is not None else self.use_simulation
        
        all_measurements = []
        
        for country in countries:
            logger.info(f"Collecting pollution data for: {country}")
            
            measurements = self.get_latest_measurements(country=country, limit=self.limit)
            
            if not measurements and use_simulation:
                logger.info(f"Using simulated data for {country}")
                measurements = self._generate_simulated_measurements()
            
            all_measurements.extend(measurements)
        
        # Convert to DataFrame
        if all_measurements:
            df = pd.DataFrame([
                self.collect_measurement_data(m) for m in all_measurements
            ])
        else:
            df = pd.DataFrame()
        
        # Save raw data
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_file = self.output_dir / f"pollution_{timestamp}.json"
        
        import json
        with open(raw_file, 'w') as f:
            json.dump(all_measurements, f, indent=2)
        
        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'measurements_collected': len(all_measurements),
            'file': str(raw_file),
            'dataframe': df,
        }
    
    def run_collection(self, latest_only: bool = True) -> Dict[str, Any]:
        """Run collection and return results."""
        start_time = time.time()
        
        if latest_only:
            result = self.collect_all_data()
        else:
            result = self.collect_all_data()
        
        duration = time.time() - start_time
        
        result['duration_seconds'] = duration
        
        return result


# Keep backward compatibility
class PollutionCollectorOriginal:
    """Original collector - now just uses PollutionCollector with simulation."""
    
    def __init__(self, *args, **kwargs):
        self.collector = PollutionCollector(*args, **kwargs)
    
    def __getattr__(self, name):
        return getattr(self.collector, name)
