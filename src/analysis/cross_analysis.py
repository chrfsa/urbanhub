"""
UrbanHub - Cross-Analysis
Smart City Data Platform

Combined analyses across all data sources
"""

from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from loguru import logger

from ..utils.config import get_config


class CrossAnalyzer:
    """Analyzer for cross-source analysis."""
    
    def __init__(self):
        """Initialize cross analyzer."""
        self.config = get_config()
        self.weather_dir = self.config.get_data_dir("silver", "weather")
        self.bikes_dir = self.config.get_data_dir("silver", "bikes")
        self.pollution_dir = self.config.get_data_dir("silver", "pollution")
    
    def load_weather(
        self,
        years: Optional[List[int]] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """Load weather data."""
        files = list(self.weather_dir.rglob("*.parquet"))
        
        if not files:
            return pd.DataFrame()
        
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        
        if years:
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df[df['timestamp'].dt.year.isin(years)]
        
        if limit and len(df) > limit:
            df = df.sample(limit)
        
        return df
    
    def load_bikes(
        self,
        limit: int = 10000
    ) -> pd.DataFrame:
        """Load bikes data."""
        files = list(self.bikes_dir.rglob("*.parquet"))
        
        if not files:
            return pd.DataFrame()
        
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        
        if limit and len(df) > limit:
            df = df.sample(limit)
        
        return df
    
    def load_pollution(
        self,
        limit: int = 10000
    ) -> pd.DataFrame:
        """Load pollution data."""
        files = list(self.pollution_dir.rglob("*.parquet"))
        
        if not files:
            return pd.DataFrame()
        
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        
        if limit and len(df) > limit:
            df = df.sample(limit)
        
        return df
    
    def weather_pollution_correlation(
        self,
        weather_df: Optional[pd.DataFrame] = None,
        pollution_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Analyze correlation between weather and pollution.
        
        Args:
            weather_df: Weather DataFrame
            pollution_df: Pollution DataFrame
            
        Returns:
            Correlation results
        """
        if weather_df is None:
            weather_df = self.load_weather()
        if pollution_df is None:
            pollution_df = self.load_pollution()
        
        if weather_df.empty or pollution_df.empty:
            return {"status": "insufficient_data"}
        
        # This is a simplified analysis - in reality would need to join on time/location
        weather_cols = ['temperature', 'wind_speed', 'pressure', 'precipitation', 'visibility']
        weather_cols = [c for c in weather_cols if c in weather_df.columns]
        
        if 'value' in pollution_df.columns and 'pollutant' in pollution_df.columns:
            # Pivot pollution by pollutant
            pollution_pivot = pollution_df.pivot_table(
                index=pollution_df.index,
                columns='pollutant',
                values='value',
                aggfunc='mean'
            ).reset_index()
        
        # Simple correlation analysis
        results = {
            "status": "success",
            "message": "Correlation analysis requires temporal and spatial alignment",
            "weather_available": weather_cols,
            "pollutants_available": pollution_df['pollutant'].unique().tolist() if 'pollutant' in pollution_df.columns else []
        }
        
        return results
    
    def weather_bikes_correlation(
        self,
        weather_df: Optional[pd.DataFrame] = None,
        bikes_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Analyze correlation between weather and bike usage.
        
        Args:
            weather_df: Weather DataFrame
            bikes_df: Bikes DataFrame
            
        Returns:
            Correlation results
        """
        if weather_df is None:
            weather_df = self.load_weather()
        if bikes_df is None:
            bikes_df = self.load_bikes()
        
        if weather_df.empty or bikes_df.empty:
            return {"status": "insufficient_data"}
        
        # Parse timestamps
        if 'timestamp' in weather_df.columns:
            weather_df = weather_df.copy()
            weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
            weather_df['hour'] = weather_df['timestamp'].dt.hour
            weather_df['date'] = weather_df['timestamp'].dt.date
        
        if 'timestamp' in bikes_df.columns:
            bikes_df = bikes_df.copy()
            bikes_df['timestamp'] = pd.to_datetime(bikes_df['timestamp'])
            bikes_df['hour'] = bikes_df['timestamp'].dt.hour
            bikes_df['date'] = bikes_df['timestamp'].dt.date
        
        # Aggregate by date
        weather_daily = weather_df.groupby('date').agg({
            'temperature': 'mean',
            'precipitation': 'sum'
        }).reset_index() if 'temperature' in weather_df.columns else pd.DataFrame()
        
        bikes_daily = bikes_df.groupby('date').agg({
            'bikes_available': 'mean'
        }).reset_index() if 'bikes_available' in bikes_df.columns else pd.DataFrame()
        
        if not weather_daily.empty and not bikes_daily.empty:
            # Merge on date
            merged = weather_daily.merge(bikes_daily, on='date', how='inner')
            
            if len(merged) > 10 and 'temperature' in merged.columns:
                correlation = merged['temperature'].corr(merged['bikes_available'])
                
                return {
                    "status": "success",
                    "correlation_temp_bikes": float(correlation),
                    "data_points": len(merged)
                }
        
        return {
            "status": "insufficient_data",
            "message": "Not enough aligned data for correlation"
        }
    
    def favorable_weather_cycling(
        self,
        weather_df: Optional[pd.DataFrame] = None,
        bikes_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Identify favorable weather conditions for cycling.
        
        Args:
            weather_df: Weather DataFrame
            bikes_df: Bikes DataFrame
            
        Returns:
            Favorable conditions analysis
        """
        if weather_df is None:
            weather_df = self.load_weather(limit=5000)
        if bikes_df is None:
            bikes_df = self.load_bikes(limit=5000)
        
        if weather_df.empty or bikes_df.empty:
            return {"status": "insufficient_data"}
        
        # Parse timestamps
        if 'timestamp' in weather_df.columns and 'timestamp' in bikes_df.columns:
            weather_df = weather_df.copy()
            bikes_df = bikes_df.copy()
            
            weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
            bikes_df['timestamp'] = pd.to_datetime(bikes_df['timestamp'])
            
            # Define favorable conditions
            favorable = weather_df[
                (weather_df['temperature'] > 10) &  # Not too cold
                (weather_df['temperature'] < 30) &  # Not too hot
                (weather_df['precipitation'] < 1)    # No rain
            ]
            
            return {
                "status": "success",
                "total_weather_records": len(weather_df),
                "favorable_conditions": len(favorable),
                "favorable_pct": float(len(favorable) / len(weather_df) * 100),
                "avg_temp_favorable": float(favorable['temperature'].mean()) if len(favorable) > 0 else None
            }
        
        return {"status": "insufficient_data"}
    
    def interaction_periods(
        self,
        weather_df: Optional[pd.DataFrame] = None,
        bikes_df: Optional[pd.DataFrame] = None,
        pollution_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Identify periods with strong interactions.
        
        Args:
            weather_df: Weather DataFrame
            bikes_df: Bikes DataFrame
            pollution_df: Pollution DataFrame
            
        Returns:
            Interaction analysis
        """
        # Load data
        if weather_df is None:
            weather_df = self.load_weather(limit=5000)
        if bikes_df is None:
            bikes_df = self.load_bikes(limit=5000)
        if pollution_df is None:
            pollution_df = self.load_pollution(limit=5000)
        
        if weather_df.empty or bikes_df.empty or pollution_df.empty:
            return {"status": "insufficient_data"}
        
        # Simple summary
        return {
            "status": "success",
            "weather_records": len(weather_df),
            "bikes_records": len(bikes_df),
            "pollution_records": len(pollution_df),
            "message": "Full interaction analysis requires advanced ML models"
        }
    
    def run_full_analysis(self) -> Dict:
        """
        Run complete cross-analysis.
        
        Returns:
            Complete analysis results
        """
        logger.info("Running cross-analysis")
        
        weather_df = self.load_weather(limit=10000)
        bikes_df = self.load_bikes(limit=10000)
        pollution_df = self.load_pollution(limit=10000)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "weather_pollution": self.weather_pollution_correlation(weather_df, pollution_df),
            "weather_bikes": self.weather_bikes_correlation(weather_df, bikes_df),
            "favorable_cycling": self.favorable_weather_cycling(weather_df, bikes_df),
            "interaction_periods": self.interaction_periods(weather_df, bikes_df, pollution_df)
        }
        
        return results


def run_cross_analysis() -> Dict:
    """
    Run cross-analysis.
    
    Returns:
        Analysis results
    """
    analyzer = CrossAnalyzer()
    return analyzer.run_full_analysis()


if __name__ == "__main__":
    results = run_cross_analysis()
    print(f"Cross-analysis complete: {results}")
