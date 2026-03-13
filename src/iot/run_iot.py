"""
UrbanHub - Run IoT Collection
Smart City Data Platform

Main entry point for IoT pollution data collection
"""

import time
import signal
import sys
from datetime import datetime
from typing import Optional

import schedule
from loguru import logger

from .collector_pollution import PollutionCollector
from ..utils.config import get_config


class IoTRunner:
    """Runner for IoT pollution data collection."""
    
    def __init__(self):
        """Initialize IoT runner."""
        self.config = get_config()
        self.openaq_config = self.config.get("apis.openaq", {})
        self.interval = self.openaq_config.get("collection_interval", 600)
        
        self.collector = PollutionCollector()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.running = False
        
    def collect_pollution(self) -> None:
        """Collect pollution data."""
        logger.info("Starting pollution collection cycle")
        
        # Collect latest data (more efficient)
        result = self.collector.run_collection(latest_only=True)
        
        if result.get('success'):
            logger.info(
                f"Pollution collection complete: "
                f"{result.get('measurements_collected')} measurements in "
                f"{result.get('duration_seconds'):.2f}s"
            )
            
            violations = result.get('threshold_violations', 0)
            if violations > 0:
                logger.warning(f"Found {violations} threshold violations")
        else:
            logger.error(
                f"Pollution collection failed: {result.get('error')}"
            )
    
    def setup_schedule(self) -> None:
        """Setup scheduled jobs."""
        # Schedule pollution collection
        schedule.every(self.interval).seconds.do(self.collect_pollution)
        
        logger.info(f"Scheduled pollution collection every {self.interval} seconds")
    
    def run(self) -> None:
        """Run the IoT collector."""
        logger.info("Starting IoT pollution data collection")
        
        self.running = True
        self.setup_schedule()
        
        # Run initial collection
        self.collect_pollution()
        
        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("IoT collection stopped")


def run_iot(
    interval: Optional[int] = None,
    duration: Optional[int] = None
) -> None:
    """
    Run IoT pollution data collection.
    
    Args:
        interval: Collection interval in seconds
        duration: Duration to run in seconds (None = infinite)
    """
    config = get_config()
    openaq_config = config.get("apis.openaq", {})
    
    interval = interval or openaq_config.get("collection_interval", 600)
    
    runner = IoTRunner()
    runner.interval = interval
    
    if duration:
        # Run for specified duration
        start_time = time.time()
        
        runner.setup_schedule()
        runner.collect_pollution()
        
        while time.time() - start_time < duration:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info(f"IoT collection completed after {duration} seconds")
    else:
        # Run indefinitely
        runner.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run IoT pollution data collection")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Collection interval in seconds"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration to run in seconds (default: infinite)"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting IoT data collector")
    run_iot(interval=args.interval, duration=args.duration)
