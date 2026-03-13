"""
UrbanHub - Configuration Utility
Smart City Data Platform
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Configuration manager for UrbanHub."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config YAML file
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        config_file = Path(self.config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                self._config = yaml.safe_load(f)
            # Replace environment variables
            self._config = self._replace_env_vars(self._config)
        else:
            # Use defaults if config file doesn't exist
            self._config = self._get_defaults()
    
    def _replace_env_vars(self, config: Any) -> Any:
        """Recursively replace environment variables in config."""
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            if config.startswith('${') and config.endswith('}'):
                env_var = config[2:-1]
                return os.getenv(env_var, config)
            return config
        return config
            
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app": {
                "name": "UrbanHub",
                "version": "1.0.0",
                "environment": "development"
            },
            "data": {
                "root": "./data",
                "raw": {
                    "weather": "./data/raw/weather",
                    "bikes": "./data/raw/bikes",
                    "pollution": "./data/raw/pollution"
                },
                "bronze": {
                    "weather": "./data/bronze/weather",
                    "bikes": "./data/bronze/bikes",
                    "pollution": "./data/bronze/pollution"
                },
                "silver": {
                    "weather": "./data/silver/weather",
                    "bikes": "./data/silver/bikes",
                    "pollution": "./data/silver/pollution"
                },
                "gold": {
                    "weather_daily": "./data/gold/weather_daily",
                    "bikes_hourly": "./data/gold/bikes_hourly",
                    "pollution_daily": "./data/gold/pollution_daily",
                    "cross_analysis": "./data/gold/cross_analysis"
                }
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "format": None,
                "file": {
                    "enabled": True,
                    "directory": "./logs",
                    "rotation": "10 MB",
                    "retention": "7 days"
                }
            },
            "database": {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "name": os.getenv("POSTGRES_DB", "urbanhub"),
                "user": os.getenv("POSTGRES_USER", "urbanhub"),
                "password": os.getenv("POSTGRES_PASSWORD", ""),
                "pool_size": 5,
                "echo": False
            },
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "db": int(os.getenv("REDIS_DB", "0")),
                "decode_responses": True
            },
            "apis": {
                "noaa": {
                    "base_url": "https://www.ncei.noaa.gov/data/global-hourly/access/",
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_delay": 5,
                    "parallel_downloads": 20,
                    "countries": ["FR"],
                    "years": {
                        "start": 1990,
                        "end": 2024
                    }
                },
                "citybikes": {
                    "base_url": "https://api.citybik.es/v2/",
                    "timeout": 10,
                    "cities": ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes"],
                    "collection_interval": 600
                },
                "openaq": {
                    "base_url": "https://api.openaq.org/v2/",
                    "timeout": 15,
                    "countries": ["FR"],
                    "pollutants": ["PM2.5", "PM10", "O3", "NO2", "CO"],
                    "collection_interval": 600,
                    "limit": 1000
                }
            },
            "etl": {
                "batch_size": 10000,
                "chunk_size": 5000,
                "compression": "snappy",
                "validation": {
                    "enabled": True,
                    "strict": False
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
                
        return value
    
    def get_data_dir(self, layer: str = "raw", category: str = "weather") -> Path:
        """
        Get a data directory path.
        
        Args:
            layer: Data layer (raw, bronze, silver, gold)
            category: Data category (weather, bikes, pollution)
            
        Returns:
            Path object
        """
        key = f"data.{layer}.{category}"
        path = self.get(key)
        if path:
            return Path(path)
        return Path(f"./data/{layer}/{category}")
    
    def get_api_config(self, api: str) -> Dict[str, Any]:
        """
        Get API configuration.
        
        Args:
            api: API name (noaa, citybikes, openaq)
            
        Returns:
            API configuration dictionary
        """
        return self.get(f"apis.{api}", {})
    
    def ensure_directories(self) -> None:
        """Create all necessary data directories."""
        for layer in ["raw", "bronze", "silver", "gold"]:
            for category in ["weather", "bikes", "pollution"]:
                if layer == "gold":
                    if category == "weather":
                        subcats = ["weather_daily", "bikes_hourly", "pollution_daily", "cross_analysis"]
                    else:
                        subcats = []
                else:
                    subcats = [category]
                
                for subcat in subcats:
                    if subcat:
                        path = self.get_data_dir(layer, subcat)
                    else:
                        path = self.get_data_dir(layer, category)
                    path.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
