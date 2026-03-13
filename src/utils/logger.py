"""
UrbanHub - Logger Utility
Smart City Data Platform
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(
    name: str = "urbanhub",
    log_dir: str = "./logs",
    log_level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: Optional[str] = None
) -> "logger":
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        rotation: Log file rotation size
        retention: Log file retention period
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()
    
    # Default format
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
    
    # Console handler
    logger.add(
        sys.stdout,
        format=format_string,
        level=log_level,
        colorize=True
    )
    
    # File handler
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_path / f"{name}.log",
        format=format_string,
        level=log_level,
        rotation=rotation,
        retention=retention,
        compression="zip"
    )
    
    return logger


def get_logger(name: str = "urbanhub") -> "logger":
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Default logger instance
default_logger = setup_logger()
