#!/usr/bin/env python
"""
UrbanHub - Pollution Data Collector Script
Run this to collect air pollution data from OpenAQ API
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.iot.collector_pollution import PollutionCollector
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger("pollution_collector")

# Run collector
logger.info("Starting pollution data collection")
collector = PollutionCollector()

# Run one collection cycle
result = collector.run_collection(latest_only=True)

logger.info(f"Collection complete: {result}")
print(f"\n✅ Results: {result}")
print(f"📁 Files saved to: {collector.output_dir}")
