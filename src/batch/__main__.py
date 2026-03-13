#!/usr/bin/env python
"""
UrbanHub - Batch Weather Download Entry Point
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.batch.download_weather import WeatherDownloader, run_download
from src.utils.logger import setup_logger

if __name__ == "__main__":
    logger = setup_logger("weather_download")
    logger.info("Starting weather data download")
    results = run_download()
    logger.info(f"Download complete: {results}")
