"""
UrbanHub - Bikes Data Analysis
Smart City Data Platform

Analyses for bike sharing data
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from loguru import logger

from ..utils.config import get_config
from ..utils.dates import get_hour_bucket


class BikesAnalyzer:
    """Analyzer for bike sharing data."""
    
    def __init__(self):
        """Initialize bikes analyzer."""
        self.config = get_config()
        self.silver_dir = self.config.get_data_dir("silver", "bikes")
    
    def load_data(
        self,
        date: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load bikes data.
        
        Args:
            date: Filter by date (YYYY-MM-DD)
            columns: Columns to load
            
        Returns:
            Bikes DataFrame
        """
        if date:
            date_dir = self.silver_dir / f"date={date}"
            if date_dir.exists():
                files = list(date_dir.glob("*.parquet"))
                if files:
                    return pd.concat(
                        [pd.read_parquet(f, columns=columns) for f in files],
                        ignore_index=True
                    )
        
        # Load all recent
        files = list(self.silver_dir.rglob("*.parquet"))
        if files:
            return pd.concat(
                [pd.read_parquet(f, columns=columns) for f in files],
                ignore_index=True
            )
        
        return pd.DataFrame()
    
    def get_top_stations(
        self,
        df: pd.DataFrame,
        column: str = "bikes_available",
        n: int = 10
    ) -> pd.DataFrame:
        """
        Get top stations by usage.
        
        Args:
            df: Bikes DataFrame
            column: Column to rank by
            n: Number of stations
            
        Returns:
            Top stations DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        # Group by station
        if column in df.columns:
            top = df.groupby(['station_id', 'station_name', 'city'])[column].mean()
            top = top.sort_values(ascending=False).head(n)
            
            result = pd.DataFrame(top).reset_index()
            result.columns = ['station_id', 'station_name', 'city', 'avg_value']
            return result
        
        return pd.DataFrame()
    
    def get_low_supply_zones(
        self,
        df: pd.DataFrame,
        threshold: float = 0.2
    ) -> pd.DataFrame:
        """
        Identify zones with insufficient bike supply.
        
        Args:
            df: Bikes DataFrame
            threshold: Empty threshold ratio
            
        Returns:
            Low supply zones
        """
        if df.empty or 'bikes_available' not in df.columns:
            return pd.DataFrame()
        
        # Calculate empty ratio
        df = df.copy()
        df['empty_ratio'] = df['bikes_available'] / df['total_slots']
        
        # Group by station
        station_avg = df.groupby(['station_id', 'station_name', 'city']).agg({
            'empty_ratio': 'mean',
            'bikes_available': 'mean',
            'total_slots': 'mean'
        }).reset_index()
        
        # Filter low supply
        low_supply = station_avg[station_avg['empty_ratio'] < threshold]
        
        return low_supply.sort_values('empty_ratio')
    
    def get_hourly_usage(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Get hourly usage patterns.
        
        Args:
            df: Bikes DataFrame
            
        Returns:
            Hourly usage DataFrame
        """
        if df.empty or 'timestamp' not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['hour_bucket'] = df['hour'].apply(get_hour_bucket)
        
        # Group by hour
        hourly = df.groupby('hour').agg({
            'bikes_available': 'mean',
            'free_slots': 'mean'
        }).reset_index()
        
        return hourly
    
    def get_daily_patterns(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Get daily usage patterns.
        
        Args:
            df: Bikes DataFrame
            
        Returns:
            Daily patterns DataFrame
        """
        if df.empty or 'timestamp' not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        # Daily aggregations
        daily = df.groupby(['date', 'day_of_week']).agg({
            'bikes_available': 'mean',
            'free_slots': 'mean'
        }).reset_index()
        
        return daily
    
    def get_geographic_imbalance(
        self,
        df: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """
        Identify geographic imbalances.
        
        Args:
            df: Bikes DataFrame
            
        Returns:
            Dictionary with imbalance analysis
        """
        if df.empty:
            return {}
        
        # Group by city
        if 'city' in df.columns and 'bikes_available' in df.columns:
            city_stats = df.groupby('city').agg({
                'bikes_available': ['mean', 'std', 'sum'],
                'free_slots': ['mean', 'std', 'sum'],
                'station_id': 'count'
            }).reset_index()
            
            city_stats.columns = [
                'city', 'avg_bikes', 'std_bikes', 'total_bikes',
                'avg_slots', 'std_slots', 'total_slots', 'station_count'
            ]
            
            return {
                'city_stats': city_stats,
                'total_stations': int(df['station_id'].nunique()),
                'total_cities': int(df['city'].nunique())
            }
        
        return {}
    
    def get_critical_stations(
        self,
        df: pd.DataFrame,
        empty_threshold: float = 0.1,
        full_threshold: float = 0.9
    ) -> pd.DataFrame:
        """
        Identify stations that need rebalancing.
        
        Args:
            df: Bikes DataFrame
            empty_threshold: Threshold for empty stations
            full_threshold: Threshold for full stations
            
        Returns:
            Critical stations
        """
        if df.empty or 'bikes_available' not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        df['utilization'] = df['bikes_available'] / df['total_slots']
        
        # Find empty stations (need bikes)
        empty_stations = df[df['utilization'] < empty_threshold]
        
        # Find full stations (have excess bikes)
        full_stations = df[df['utilization'] > full_threshold]
        
        return {
            'empty_stations': empty_stations.groupby(
                ['station_id', 'station_name', 'city']
            ).size().reset_index(name='empty_occurrences'),
            'full_stations': full_stations.groupby(
                ['station_id', 'station_name', 'city']
            ).size().reset_index(name='full_occurrences')
        }
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for bikes data.
        
        Args:
            df: Bikes DataFrame
            
        Returns:
            Statistics dictionary
        """
        if df.empty:
            return {}
        
        stats = {
            'total_records': len(df),
            'unique_stations': int(df['station_id'].nunique()) if 'station_id' in df.columns else 0,
            'unique_cities': int(df['city'].nunique()) if 'city' in df.columns else 0,
            'time_range': {}
        }
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            stats['time_range'] = {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            }
        
        if 'bikes_available' in df.columns:
            stats['bikes_available'] = {
                'mean': float(df['bikes_available'].mean()),
                'min': float(df['bikes_available'].min()),
                'max': float(df['bikes_available'].max()),
                'total': float(df['bikes_available'].sum())
            }
        
        return stats


def analyze_bikes(date: Optional[str] = None) -> Dict:
    """
    Run bikes analysis.
    
    Args:
        date: Date to analyze
        
    Returns:
        Analysis results
    """
    analyzer = BikesAnalyzer()
    
    df = analyzer.load_data(date=date)
    
    if df.empty:
        logger.warning("No bikes data found")
        return {"status": "no_data"}
    
    results = {
        "status": "success",
        "row_count": len(df),
        "statistics": analyzer.get_statistics(df),
        "top_stations": analyzer.get_top_stations(df).to_dict('records'),
        "hourly_usage": analyzer.get_hourly_usage(df).to_dict('records')
    }
    
    return results


if __name__ == "__main__":
    results = analyze_bikes()
    print(f"Analysis complete: {results}")
