#!/usr/bin/env python
"""
UrbanHub - Weather Data Process Script
Run this to process downloaded NOAA weather data
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.batch.process_weather import WeatherProcessor
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger("weather_process")

# Run processing
logger.info("Starting weather data processing")
processor = WeatherProcessor()

# Process all downloaded files
results = processor.process_all()

logger.info(f"Processing complete: {results}")
print(f"\n✅ Results: {results}")
print(f"📁 Data saved to: {processor.silver_dir}")
