#!/usr/bin/env python3
"""
UrbanHub - Complete Weather Data Downloader
Downloads ALL French weather station data from 1990-2024

Usage:
    python download_all_france_weather.py
"""

import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configuration
BASE_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/"
OUTPUT_DIR = Path("data/raw/weather")
START_YEAR = 1990
END_YEAR = 2024
MAX_WORKERS = 10  # Parallel downloads
TIMEOUT = 60


def get_available_years():
    """Get list of available years from NOAA."""
    print("📡 Fetching available years from NOAA...")
    response = requests.get(BASE_URL, timeout=TIMEOUT)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    years = []
    for link in soup.find_all('a'):
        href = link.get('href', '')
        if href.strip('/').isdigit():
            year = int(href.strip('/'))
            if START_YEAR <= year <= END_YEAR:
                years.append(str(year))
    
    print(f"   Found {len(years)} years: {min(years)}-{max(years)}")
    return sorted(years)


def get_french_stations_for_year(year):
    """Get list of French stations for a specific year."""
    url = f"{BASE_URL}{year}/"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        french_stations = set()
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.endswith('.csv'):
                station_id = href.replace('.csv', '')
                # French metropolitan stations start with '07'
                if station_id.startswith('07'):
                    french_stations.add(station_id)
        
        return french_stations
    except Exception as e:
        print(f"   ⚠ Error fetching {year}: {e}")
        return set()


def get_all_french_stations(years):
    """Get all unique French stations across all years."""
    print("\n📡 Collecting French stations from all years...")
    all_stations = set()
    
    for year in tqdm(years, desc="Scanning years"):
        stations = get_french_stations_for_year(year)
        all_stations.update(stations)
        print(f"   {year}: {len(stations)} stations")
    
    print(f"\n   Total unique French stations: {len(all_stations)}")
    return all_stations


def download_file(args):
    """Download a single file."""
    station_id, year = args
    filename = f"{station_id}.csv"
    url = f"{BASE_URL}{year}/{filename}"
    output_path = OUTPUT_DIR / filename
    
    # Skip if already exists
    if output_path.exists():
        return station_id, year, True, "exists"
    
    try:
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            size = len(response.content) / 1024
            return station_id, year, True, f"{size:.1f} KB"
        else:
            return station_id, year, False, f"HTTP {response.status_code}"
    except Exception as e:
        return station_id, year, False, str(e)


def download_all_data(stations, years):
    """Download all station data for all years."""
    print(f"\n📥 Starting download of {len(stations)} stations × {len(years)} years")
    print(f"   Estimated files: ~{len(stations) * len(years)}")
    print(f"   This may take several hours...")
    
    # Create download tasks
    download_tasks = []
    for station_id in stations:
        for year in years:
            download_tasks.append((station_id, year))
    
    print(f"\n🚀 Starting {MAX_WORKERS} parallel downloads...")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_file, task): task for task in download_tasks}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            station_id, year, success, msg = future.result()
            if success:
                if msg == "exists":
                    skip_count += 1
                else:
                    success_count += 1
            else:
                fail_count += 1
    
    print(f"\n📊 Download Summary:")
    print(f"   ✅ New downloads: {success_count}")
    print(f"   ⏭️  Skipped (already exists): {skip_count}")
    print(f"   ❌ Failed: {fail_count}")
    
    return success_count, skip_count, fail_count


def main():
    print("=" * 60)
    print("UrbanHub - Complete French Weather Data Downloader")
    print("=" * 60)
    print(f"Period: {START_YEAR}-{END_YEAR}")
    print(f"Output: {OUTPUT_DIR}")
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get available years
    years = get_available_years()
    
    # Get all French stations
    stations = get_all_french_stations(years)
    
    if not stations:
        print("❌ No French stations found!")
        return
    
    # Show stations
    print(f"\n📍 Sample stations: {list(stations)[:10]}")
    
    # Download all data
    success, skipped, failed = download_all_data(stations, years)
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.csv"))
    print(f"\n💾 Total data size: {total_size / 1024 / 1024:.1f} MB")
    
    print("\n✅ Download complete!")
    print("\nNext steps:")
    print("  python src/batch/process_weather.py  # Process and clean data")


if __name__ == "__main__":
    main()
