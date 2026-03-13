"""
UrbanHub - Smart City Data Platform

A platform for collecting, processing, and analyzing urban data.
"""

__version__ = "1.0.0"
__author__ = "UrbanHub Team"

from . import batch
from . import streaming
from . import iot
from . import analysis
from . import visualization
from . import utils

__all__ = [
    "batch",
    "streaming",
    "iot",
    "analysis",
    "visualization",
    "utils",
]
