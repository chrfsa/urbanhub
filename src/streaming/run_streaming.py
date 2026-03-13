"""
UrbanHub - Run Streaming Collection
Smart City Data Platform

Main entry point for streaming data collection
"""

import time
import signal
import sys
from datetime import datetime
from typing import Optional

import schedule
from loguru import logger

from .collector_bikes import BikesCollector
from ..utils.config import get_config


class StreamingRunner:
    """Runner for streaming data collection."""
    
    def __init__(self):
        """Initialize streaming runner."""
        self.config = get_config()
        self.bikes_config = self.config.get("apis.citybikes", {})
        self.interval = self.bikes_config.get("collection_interval", 60)
        
        self.collector = BikesCollector()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.running = False
        
    def collect_bikes(self) -> None:
        """Collect bikes data."""
        logger.info("Starting bikes collection cycle")
        result = self.collector.run_collection()
        
        if result.get('success'):
            logger.info(
                f"Bikes collection complete: "
                f"{result.get('stations_collected')} stations in "
                f"{result.get('duration_seconds'):.2f}s"
            )
        else:
            logger.error(
                f"Bikes collection failed: {result.get('error')}"
            )
    
    def setup_schedule(self) -> None:
        """Setup scheduled jobs."""
        # Schedule bikes collection
        schedule.every(self.interval).seconds.do(self.collect_bikes)
        
        logger.info(f"Scheduled bikes collection every {self.interval} seconds")
    
    def run(self) -> None:
        """Run the streaming collector."""
        logger.info("Starting streaming data collection")
        
        self.running = True
        self.setup_schedule()
        
        # Run initial collection
        self.collect_bikes()
        
        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Streaming collection stopped")


def run_streaming(
    interval: Optional[int] = None,
    duration: Optional[int] = None
) -> None:
    """
    Run streaming data collection.
    
    Args:
        interval: Collection interval in seconds
        duration: Duration to run in seconds (None = infinite)
    """
    config = get_config()
    bikes_config = config.get("apis.citybikes", {})
    
    interval = interval or bikes_config.get("collection_interval", 60)
    duration = duration
    
    runner = StreamingRunner()
    runner.interval = interval
    
    if duration:
        # Run for specified duration
        start_time = time.time()
        
        runner.setup_schedule()
        runner.collect_bikes()
        
        while time.time() - start_time < duration:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info(f"Streaming collection completed after {duration} seconds")
    else:
        # Run indefinitely
        runner.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run streaming data collection")
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
    
    logger.info("Starting streaming data collector")
    run_streaming(interval=args.interval, duration=args.duration)
