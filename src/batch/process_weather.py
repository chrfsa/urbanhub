"""
UrbanHub - Process Weather Data
Smart City Data Platform

Process and clean NOAA weather data
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from tqdm import tqdm
from loguru import logger

from ..utils.config import get_config
from ..utils.storage import Storage
from ..utils.dates import parse_noaa_datetime


class WeatherProcessor:
    """Process NOAA weather data."""
    
    # NOAA column mapping
    COLUMN_MAPPING = {
        'STATION': 'station_id',
        'DATE': 'timestamp',
        'TMP': 'temperature',      # Temperature in tenths of °C
        'WND': 'wind_speed',        # Wind speed in m/s (tenths)
        'WDW': 'wind_direction',   # Wind direction in degrees
        'PRCP': 'precipitation',    # Precipitation in mm
        'SLP': 'pressure',          # Sea level pressure in hPa (tenths)
        'VIS': 'visibility',       # Visibility in meters
        'DEW': 'dew_point',        # Dew point
        'W1': 'weather_indicator',  # Weather indicator
        'AA1': 'atmospheric_pressure',  # Atmospheric pressure
    }
    
    def __init__(self):
        """Initialize weather processor."""
        self.config = get_config()
        self.raw_dir = self.config.get_data_dir("raw", "weather")
        self.bronze_dir = self.config.get_data_dir("bronze", "weather")
        self.silver_dir = self.config.get_data_dir("silver", "weather")
        
        # Ensure directories exist
        for d in [self.raw_dir, self.bronze_dir, self.silver_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.weather_columns = self.config.get("weather.columns_to_keep", list(self.COLUMN_MAPPING.keys()))
        
    def read_raw_file(self, filepath: Path) -> pd.DataFrame:
        """
        Read a raw NOAA CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with raw data
        """
        try:
            # Read with chunking for large files
            chunks = []
            for chunk in pd.read_csv(
                filepath,
                dtype=str,
                chunksize=10000,
                low_memory=False
            ):
                chunks.append(chunk)
            
            df = pd.concat(chunks, ignore_index=True)
            logger.debug(f"Read {len(df)} rows from {filepath.name}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return pd.DataFrame()
    
    def _parse_temperature(self, value: str) -> Optional[float]:
        """
        Parse NOAA temperature value.
        
        Args:
            value: Temperature string (e.g., "2506" = 25.06°C)
            
        Returns:
            Temperature in Celsius
        """
        if pd.isna(value) or value in ['9999', '99999', '']:
            return None
        
        try:
            temp = float(value)
            # Convert from tenths of degree
            return temp / 10.0
        except (ValueError, TypeError):
            return None
    
    def _parse_wind(self, value: str) -> Optional[Dict[str, float]]:
        """
        Parse NOAA wind value.
        
        Args:
            value: Wind string (e.g., "999,9,1,999" or "010,4,1,0")
            
        Returns:
            Dictionary with speed and direction
        """
        if pd.isna(value) or value in ['9999', '999,9', '']:
            return None, None
        
        try:
            parts = str(value).split(',')
            if len(parts) >= 1:
                speed = float(parts[0])
                if speed < 999:
                    speed = speed / 10.0  # Convert from tenths
                else:
                    speed = None
            else:
                speed = None
                
            if len(parts) >= 2:
                direction = float(parts[1])
                if direction >= 999:
                    direction = None
            else:
                direction = None
                
            return speed, direction
        except (ValueError, TypeError):
            return None, None
    
    def _parse_precipitation(self, value: str) -> Optional[float]:
        """
        Parse NOAA precipitation value.
        
        Args:
            value: Precipitation string (e.g., "0000" or "0004")
            
        Returns:
            Precipitation in mm
        """
        if pd.isna(value) or value in ['9999', '99999', '']:
            return None
        
        try:
            # Last character might be indicator
            precip = float(value[:-1] if len(value) > 1 and not value[-1].isdigit() else value)
            return precip / 10.0  # Convert from tenths
        except (ValueError, TypeError):
            return None
    
    def _parse_pressure(self, value: str) -> Optional[float]:
        """
        Parse NOAA pressure value.
        
        Args:
            value: Pressure string
            
        Returns:
            Pressure in hPa
        """
        if pd.isna(value) or value in ['9999', '99999', '']:
            return None
        
        try:
            pressure = float(value)
            if pressure < 99999:
                return pressure / 10.0  # Convert from tenths
            return None
        except (ValueError, TypeError):
            return None
    
    def _parse_visibility(self, value: str) -> Optional[float]:
        """
        Parse NOAA visibility value.
        
        Args:
            value: Visibility string
            
        Returns:
            Visibility in meters
        """
        if pd.isna(value) or value in ['999999', '']:
            return None
        
        try:
            vis = float(value)
            if vis < 999999:
                return vis  # Already in meters
            return None
        except (ValueError, TypeError):
            return None
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and transform weather DataFrame.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Select relevant columns
        cols = [c for c in self.weather_columns if c in df.columns]
        df = df[cols].copy()
        
        # Rename columns
        df = df.rename(columns=self.COLUMN_MAPPING)
        
        # Parse timestamp
        logger.debug("Parsing timestamps")
        df['timestamp'] = df['timestamp'].apply(parse_noaa_datetime)
        
        # Parse temperature
        logger.debug("Parsing temperature")
        df['temperature'] = df['temperature'].apply(self._parse_temperature)
        
        # Parse wind speed and direction (only if column exists)
        if 'wind_speed' in df.columns:
            logger.debug("Parsing wind data")
            wind_data = df['wind_speed'].apply(self._parse_wind)
            df['wind_speed'] = wind_data.apply(lambda x: x[0] if x else None)
            df['wind_direction'] = wind_data.apply(lambda x: x[1] if x else None)
        else:
            df['wind_speed'] = None
            df['wind_direction'] = None
        
        # Parse precipitation (only if column exists)
        if 'precipitation' in df.columns:
            logger.debug("Parsing precipitation")
            df['precipitation'] = df['precipitation'].apply(self._parse_precipitation)
        else:
            df['precipitation'] = None
        
        # Parse pressure (only if column exists)
        if 'pressure' in df.columns:
            logger.debug("Parsing pressure")
            df['pressure'] = df['pressure'].apply(self._parse_pressure)
        else:
            df['pressure'] = None
        
        # Parse visibility (only if column exists)
        if 'visibility' in df.columns:
            logger.debug("Parsing visibility")
            df['visibility'] = df['visibility'].apply(self._parse_visibility)
        else:
            df['visibility'] = None
        
        # Add metadata
        df['data_quality'] = 'good'  # Could add quality checks
        
        # Drop rows with no timestamp
        df = df.dropna(subset=['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        return df
    
    def process_file(self, filepath: Path) -> Tuple[Path, int]:
        """
        Process a single weather file.
        
        Args:
            filepath: Path to raw CSV file
            
        Returns:
            Tuple of (output path, row count)
        """
        logger.info(f"Processing {filepath.name}")
        
        # Read raw file
        df = self.read_raw_file(filepath)
        
        if df.empty:
            return filepath, 0
        
        # Clean data
        df = self.clean_dataframe(df)
        
        # Write to bronze layer
        bronze_path = self.bronze_dir / f"{filepath.stem}.parquet"
        df.to_parquet(bronze_path, index=False, compression='snappy')
        
        # Write to silver layer (partitioned by year)
        year = df['timestamp'].dt.year.iloc[0]
        silver_path = self.silver_dir / f"year={year}" / f"{filepath.stem}.parquet"
        silver_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(silver_path, index=False, compression='snappy')
        
        logger.info(f"Processed {len(df)} rows from {filepath.name}")
        return silver_path, len(df)
    
    def process_all(self) -> Dict[str, int]:
        """
        Process all raw weather files.
        
        Returns:
            Dictionary with processing statistics
        """
        logger.info("Processing all weather data files")
        
        raw_files = list(self.raw_dir.glob("*.csv"))
        
        if not raw_files:
            logger.warning("No raw weather files found")
            return {"files_processed": 0, "total_rows": 0}
        
        results = {"files_processed": 0, "total_rows": 0}
        
        for filepath in tqdm(raw_files, desc="Processing weather files"):
            try:
                _, row_count = self.process_file(filepath)
                results["files_processed"] += 1
                results["total_rows"] += row_count
            except Exception as e:
                logger.error(f"Failed to process {filepath.name}: {e}")
        
        logger.info(f"Processing complete: {results}")
        return results
    
    def load_silver_data(
        self,
        years: Optional[List[int]] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load processed weather data from silver layer.
        
        Args:
            years: Filter by years
            columns: Columns to load
            
        Returns:
            DataFrame with weather data
        """
        if years:
            # Load specific years
            dfs = []
            for year in years:
                year_dir = self.silver_dir / f"year={year}"
                if year_dir.exists():
                    year_files = list(year_dir.glob("*.parquet"))
                    for f in year_files:
                        df = pd.read_parquet(f, columns=columns)
                        dfs.append(df)
            
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()
        else:
            # Load all files
            files = list(self.silver_dir.rglob("*.parquet"))
            if files:
                return pd.concat(
                    [pd.read_parquet(f, columns=columns) for f in files],
                    ignore_index=True
                )
            return pd.DataFrame()


def run_processing() -> Dict[str, int]:
    """
    Run weather data processing.
    
    Returns:
        Processing results
    """
    processor = WeatherProcessor()
    return processor.process_all()


if __name__ == "__main__":
    logger.info("Starting weather data processing")
    results = run_processing()
    logger.info(f"Processing complete: {results}")
