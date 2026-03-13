"""
UrbanHub - Weather Data Analysis
Smart City Data Platform

Analyses for weather data
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from loguru import logger

from ..utils.config import get_config
from ..utils.dates import get_season


class WeatherAnalyzer:
    """Analyzer for weather data."""
    
    def __init__(self):
        """Initialize weather analyzer."""
        self.config = get_config()
        self.silver_dir = self.config.get_data_dir("silver", "weather")
    
    def load_data(
        self,
        years: Optional[List[int]] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load weather data.
        
        Args:
            years: Filter by years
            columns: Columns to load
            
        Returns:
            Weather DataFrame
        """
        if years:
            dfs = []
            for year in years:
                year_dir = self.silver_dir / f"year={year}"
                if year_dir.exists():
                    files = list(year_dir.glob("*.parquet"))
                    for f in files:
                        df = pd.read_parquet(f, columns=columns)
                        dfs.append(df)
            
            if dfs:
                df = pd.concat(dfs, ignore_index=True)
                return df
        
        # Load all
        files = list(self.silver_dir.rglob("*.parquet"))
        if files:
            return pd.concat(
                [pd.read_parquet(f, columns=columns) for f in files],
                ignore_index=True
            )
        
        return pd.DataFrame()
    
    def get_anomalies(
        self,
        df: pd.DataFrame,
        column: str = "temperature",
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Detect anomalies using Z-score.
        
        Args:
            df: Weather DataFrame
            column: Column to analyze
            threshold: Z-score threshold
            
        Returns:
            DataFrame with anomalies
        """
        if df.empty or column not in df.columns:
            return df
        
        # Calculate Z-score
        mean = df[column].mean()
        std = df[column].std()
        
        if std == 0:
            return pd.DataFrame()
        
        df = df.copy()
        df['z_score'] = (df[column] - mean) / std
        
        # Filter anomalies
        anomalies = df[abs(df['z_score']) > threshold]
        
        return anomalies
    
    def get_correlation_visibility(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate correlation between weather and visibility.
        
        Args:
            df: Weather DataFrame
            
        Returns:
            Dictionary of correlations
        """
        if df.empty:
            return {}
        
        # Select relevant columns
        cols = ['temperature', 'wind_speed', 'pressure', 'precipitation', 'visibility']
        cols = [c for c in cols if c in df.columns]
        
        if len(cols) < 2:
            return {}
        
        # Calculate correlations
        correlations = df[cols].corr()['visibility'].to_dict()
        
        return {k: v for k, v in correlations.items() if k != 'visibility'}
    
    def get_seasonal_temperature(
        self,
        df: pd.DataFrame,
        city: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get seasonal temperature trends.
        
        Args:
            df: Weather DataFrame
            city: Filter by city
            
        Returns:
            Seasonal temperature DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['month'] = df['timestamp'].dt.month
            df['season'] = df['month'].apply(lambda x: get_season(datetime(2000, x, 1)))
            df['year'] = df['timestamp'].dt.year
        
        if 'temperature' not in df.columns:
            return pd.DataFrame()
        
        # Group by season
        seasonal = df.groupby(['year', 'season'])['temperature'].agg([
            'mean', 'min', 'max', 'count'
        ]).reset_index()
        
        return seasonal
    
    def get_extreme_days(
        self,
        df: pd.DataFrame,
        column: str = "temperature",
        n: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """
        Identify extreme weather days.
        
        Args:
            df: Weather DataFrame
            column: Column to analyze
            n: Number of extremes to return
            
        Returns:
            Dictionary with hot and cold days
        """
        if df.empty or column not in df.columns:
            return {}
        
        df = df.copy()
        
        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
        
        # Daily aggregations
        daily = df.groupby('date')[column].agg(['mean', 'max', 'min']).reset_index()
        
        # Get extremes
        hottest = daily.nlargest(n, 'max')
        coldest = daily.nsmallest(n, 'min')
        
        return {
            'hottest_days': hottest,
            'coldest_days': coldest
        }
    
    def get_statistics(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Get summary statistics for weather data.
        
        Args:
            df: Weather DataFrame
            
        Returns:
            Dictionary with statistics
        """
        if df.empty:
            return {}
        
        stats = {}
        
        numeric_cols = ['temperature', 'wind_speed', 'pressure', 'precipitation', 'visibility']
        
        for col in numeric_cols:
            if col in df.columns:
                stats[col] = {
                    'count': int(df[col].count()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'q25': float(df[col].quantile(0.25)),
                    'q50': float(df[col].quantile(0.50)),
                    'q75': float(df[col].quantile(0.75)),
                    'missing': int(df[col].isna().sum())
                }
        
        return stats


def analyze_weather(years: Optional[List[int]] = None) -> Dict:
    """
    Run weather analysis.
    
    Args:
        years: Years to analyze
        
    Returns:
        Analysis results
    """
    analyzer = WeatherAnalyzer()
    
    df = analyzer.load_data(years=years)
    
    if df.empty:
        logger.warning("No weather data found")
        return {"status": "no_data"}
    
    results = {
        "status": "success",
        "row_count": len(df),
        "statistics": analyzer.get_statistics(df),
        "correlation_visibility": analyzer.get_correlation_visibility(df)
    }
    
    return results


if __name__ == "__main__":
    results = analyze_weather()
    print(f"Analysis complete: {results}")
