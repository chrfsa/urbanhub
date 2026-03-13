#!/usr/bin/env python
"""
UrbanHub - Bikes Data Collector Script
Run this to collect bike sharing data from CityBikes API
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.streaming.collector_bikes import BikesCollector
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger("bikes_collector")

# Run collector
logger.info("Starting bikes data collection")
collector = BikesCollector()

# Run one collection cycle
result = collector.run_collection()

logger.info(f"Collection complete: {result}")
print(f"\n✅ Results: {result}")
print(f"📁 Files saved to: {collector.output_dir}")
