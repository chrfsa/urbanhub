"""
UrbanHub - Pollution Data Analysis
Smart City Data Platform

Analyses for air pollution data
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from loguru import logger

from ..utils.config import get_config


class PollutionAnalyzer:
    """Analyzer for air pollution data."""
    
    def __init__(self):
        """Initialize pollution analyzer."""
        self.config = get_config()
        self.silver_dir = self.config.get_data_dir("silver", "pollution")
    
    def load_data(
        self,
        date: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load pollution data.
        
        Args:
            date: Filter by date (YYYY-MM-DD)
            columns: Columns to load
            
        Returns:
            Pollution DataFrame
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
    
    def get_pollution_by_city(
        self,
        df: pd.DataFrame,
        pollutant: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get pollution levels by city.
        
        Args:
            df: Pollution DataFrame
            pollutant: Filter by pollutant
            
        Returns:
            City pollution DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        data = df.copy()
        
        if pollutant:
            data = data[data['pollutant'] == pollutant]
        
        if 'city' in data.columns and 'value' in data.columns:
            city_pollution = data.groupby(['city', 'pollutant'])['value'].agg([
                'mean', 'max', 'min', 'std', 'count'
            ]).reset_index()
            
            return city_pollution
        
        return pd.DataFrame()
    
    def get_pollution_zones(
        self,
        df: pd.DataFrame,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Identify highest pollution zones.
        
        Args:
            df: Pollution DataFrame
            top_n: Number of zones to return
            
        Returns:
            High pollution zones
        """
        if df.empty or 'city' not in df.columns:
            return pd.DataFrame()
        
        # Group by city and pollutant
        city_avg = df.groupby(['city', 'pollutant'])['value'].mean().reset_index()
        
        # Get top polluted
        top = city_avg.nlargest(top_n, 'value')
        
        return top
    
    def get_daily_variation(
        self,
        df: pd.DataFrame,
        city: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get daily pollution variation patterns.
        
        Args:
            df: Pollution DataFrame
            city: Filter by city
            
        Returns:
            Daily variation DataFrame
        """
        if df.empty or 'timestamp' not in df.columns:
            return pd.DataFrame()
        
        data = df.copy()
        
        if city:
            data = data[data['city'] == city]
        
        # Parse timestamp
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data['hour'] = data['timestamp'].dt.hour
        
        # Hourly aggregations
        hourly = data.groupby(['hour', 'pollutant'])['value'].mean().reset_index()
        
        return hourly
    
    def get_dominant_pollutants(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Get dominant pollutants by city.
        
        Args:
            df: Pollution DataFrame
            
        Returns:
            Dominant pollutants DataFrame
        """
        if df.empty or 'pollutant' not in df.columns:
            return pd.DataFrame()
        
        # Count occurrences
        pollutant_counts = df.groupby(['city', 'pollutant']).size().reset_index(name='count')
        
        # Get dominant (most frequent)
        dominant = pollutant_counts.loc[
            pollutant_counts.groupby('city')['count'].idxmax()
        ]
        
        return dominant
    
    def get_episodes(
        self,
        df: pd.DataFrame,
        thresholds: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Identify pollution episodes.
        
        Args:
            df: Pollution DataFrame
            thresholds: Pollutant thresholds
            
        Returns:
            Pollution episodes
        """
        if thresholds is None:
            thresholds = {
                "PM2.5": 25,
                "PM10": 50,
                "O3": 120,
                "NO2": 40,
                "CO": 10000
            }
        
        if df.empty:
            return pd.DataFrame()
        
        episodes = []
        
        for pollutant, threshold in thresholds.items():
            pollutant_data = df[df['pollutant'] == pollutant]
            
            if pollutant_data.empty:
                continue
            
            exceedances = pollutant_data[pollutant_data['value'] > threshold]
            
            if not exceedances.empty:
                for _, row in exceedances.iterrows():
                    episodes.append({
                        'city': row.get('city'),
                        'pollutant': pollutant,
                        'value': row['value'],
                        'threshold': threshold,
                        'exceedance_pct': ((row['value'] - threshold) / threshold) * 100,
                        'timestamp': row.get('timestamp')
                    })
        
        return pd.DataFrame(episodes)
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for pollution data.
        
        Args:
            df: Pollution DataFrame
            
        Returns:
            Statistics dictionary
        """
        if df.empty:
            return {}
        
        stats = {
            'total_records': len(df),
            'unique_sensors': int(df['sensor_id'].nunique()) if 'sensor_id' in df.columns else 0,
            'unique_cities': int(df['city'].nunique()) if 'city' in df.columns else 0,
            'unique_pollutants': int(df['pollutant'].nunique()) if 'pollutant' in df.columns else 0,
            'pollutants': {}
        }
        
        if 'pollutant' in df.columns and 'value' in df.columns:
            for pollutant in df['pollutant'].unique():
                pollutant_data = df[df['pollutant'] == pollutant]
                stats['pollutants'][pollutant] = {
                    'count': len(pollutant_data),
                    'mean': float(pollutant_data['value'].mean()),
                    'max': float(pollutant_data['value'].max()),
                    'min': float(pollutant_data['value'].min())
                }
        
        return stats


def analyze_pollution(date: Optional[str] = None) -> Dict:
    """
    Run pollution analysis.
    
    Args:
        date: Date to analyze
        
    Returns:
        Analysis results
    """
    analyzer = PollutionAnalyzer()
    
    df = analyzer.load_data(date=date)
    
    if df.empty:
        logger.warning("No pollution data found")
        return {"status": "no_data"}
    
    results = {
        "status": "success",
        "row_count": len(df),
        "statistics": analyzer.get_statistics(df),
        "dominant_pollutants": analyzer.get_dominant_pollutants(df).to_dict('records'),
        "pollution_zones": analyzer.get_pollution_zones(df).to_dict('records')
    }
    
    return results


if __name__ == "__main__":
    results = analyze_pollution()
    print(f"Analysis complete: {results}")
