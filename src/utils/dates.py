"""
UrbanHub - Date Utility
Smart City Data Platform
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import pandas as pd


def parse_noaa_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse NOAA date string to datetime.
    
    NOAA format: YYYYMMDDTHHMMZ
    
    Args:
        date_str: Date string from NOAA
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        # Format: YYYYMMDDTHHMMZ
        date_str = str(date_str).strip()
        if 'T' in date_str:
            date_str = date_str.replace('T', ' ')
        if 'Z' in date_str:
            date_str = date_str.replace('Z', '')
        
        return datetime.strptime(date_str, '%Y%m%d %H%M')
    except ValueError:
        try:
            # Try alternate format
            return datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        except ValueError:
            return None


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse ISO format datetime string.
    
    Args:
        date_str: ISO format date string
        
    Returns:
        Datetime object or None
    """
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
    except ValueError:
        return None


def to_utc(dt: Union[datetime, str], tz: Optional[str] = None) -> datetime:
    """
    Convert datetime to UTC.
    
    Args:
        dt: Datetime object or string
        tz: Source timezone (None = assume UTC)
        
    Returns:
        UTC datetime
    """
    if isinstance(dt, str):
        dt = parse_iso_datetime(dt) or parse_noaa_datetime(dt)
    
    if dt is None:
        return datetime.now(timezone.utc)
    
    if dt.tzinfo is None:
        if tz:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo(tz))
        else:
            dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(timezone.utc)


def format_timestamp(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime as string.
    
    Args:
        dt: Datetime object (default: now)
        fmt: Format string
        
    Returns:
        Formatted date string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def get_year_from_filename(filename: str) -> Optional[int]:
    """
    Extract year from NOAA filename.
    
    Args:
        filename: NOAA filename (e.g., 076900-99999-1990.csv)
        
    Returns:
        Year or None
    """
    try:
        # Extract year from filename
        parts = filename.split('-')
        for part in parts:
            if len(part) == 4 and part.isdigit():
                year = int(part)
                if 1900 <= year <= 2100:
                    return year
        return None
    except Exception as e:
        logger.warning(f"Failed to extract year from {filename}: {e}")
        return None


def get_date_range(
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    years: Optional[list] = None
) -> list:
    """
    Get list of years or dates between start and end.
    
    Args:
        start_date: Start date
        end_date: End date
        years: Specific list of years
        
    Returns:
        List of years or dates
    """
    if years:
        return list(range(min(years), max(years) + 1))
    
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)
    
    start_year = start_date.year if start_date else 1990
    end_year = end_date.year if end_date else datetime.now().year
    
    return list(range(start_year, end_year + 1))


def get_season(dt: Optional[datetime] = None) -> str:
    """
    Get season for a given date.
    
    Args:
        dt: Datetime (default: now)
        
    Returns:
        Season name (winter, spring, summer, autumn)
    """
    if dt is None:
        dt = datetime.now()
    
    month = dt.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"


def get_hour_bucket(hour: int) -> str:
    """
    Get time bucket for hour.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        Time bucket name
    """
    if 6 <= hour < 9:
        return "morning_peak"
    elif 9 <= hour < 12:
        return "morning"
    elif 12 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 20:
        return "evening_peak"
    elif 20 <= hour < 23:
        return "evening"
    else:
        return "night"


def timestamp_to_datehour(ts: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to datetime.
    
    Args:
        ts: Unix timestamp
        
    Returns:
        Datetime object
    """
    return datetime.fromtimestamp(ts)


def datehour_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: Datetime object
        
    Returns:
        Unix timestamp
    """
    return int(dt.timestamp())
