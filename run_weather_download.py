#!/usr/bin/env python
"""
UrbanHub - Weather Data Download Script
Run this to download NOAA weather data for France
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.batch.download_weather import WeatherDownloader
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger("weather_download")

# Run download
logger.info("Starting weather data download for France")
downloader = WeatherDownloader()

# Download for years 1990-2024 (full dataset)
results = downloader.download_range(start_year=1990, end_year=2024)

logger.info(f"Download complete: {results}")
print(f"\n✅ Results: {results}")
print(f"📁 Files saved to: {downloader.output_dir}")
