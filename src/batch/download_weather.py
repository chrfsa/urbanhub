"""
UrbanHub - Batch Download Weather Data
Smart City Data Platform

Download NOAA Global Hourly Weather Data for France stations
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from tqdm import tqdm
from loguru import logger

from ..utils.config import get_config
from ..utils.dates import get_year_from_filename


class WeatherDownloader:
    """Download weather data from NOAA."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize weather downloader.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or get_config().get("apis.noaa", {})
        self.base_url = self.config.get("base_url", "https://www.ncei.noaa.gov/data/global-hourly/access/")
        self.output_dir = Path(get_config().get_data_dir("raw", "weather"))
        self.max_workers = self.config.get("parallel_downloads", 20)
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_session(self) -> requests.Session:
        """Create HTTP session with retry adapter."""
        session = requests.Session()
        
        # Simple retry logic
        adapter = requests.adapters.HTTPAdapter(
            max_retries=self.max_retries,
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def list_available_files(self) -> List[str]:
        """
        List all available yearly directories from NOAA.
        
        Returns:
            List of years available
        """
        logger.info(f"Fetching directory list from {self.base_url}")
        
        try:
            response = requests.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links to year directories
            years = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                # Look for year directories like "2024/" - years are 4 digits
                if href.strip('/').isdigit() and len(href.strip('/')) == 4:
                    years.append(href.strip('/'))
                    years.append(href.strip('/'))
            
            logger.info(f"Found {len(years)} years: {sorted(years)}")
            return sorted(years)
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch file list: {e}")
            return []
    
    def list_france_stations(self, year: int) -> List[str]:
        """
        List station files for France for a specific year.
        
        Args:
            year: Year to fetch
            
        Returns:
            List of France station CSV files
        """
        # NOAA station file format for recent years: STATIONID.csv
        # French stations have WMO index starting with 07xxxx (France海外 territories also start with 6xxxxx)
        
        url = f"{self.base_url}{year}/"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all CSV files
            all_files = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.endswith('.csv'):
                    all_files.append(href)
            
            # Filter for French stations (WMO index 07xxx for metropolitan France)
            french_files = []
            for f in all_files:
                station_id = f.replace('.csv', '')
                # French metropolitan stations start with '07'
                if station_id.startswith('07'):
                    french_files.append(f)
            
            logger.info(f"Found {len(french_files)} French stations for year {year}: {french_files[:5]}")
            return french_files
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch stations for year {year}: {e}")
            return []
    
    def download_file(
        self,
        filename: str,
        year: int,
        session: Optional[requests.Session] = None
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Download a single file.
        
        Args:
            filename: File name to download
            year: Year of the file
            session: HTTP session
            
        Returns:
            Tuple of (filename, success, error_message)
        """
        url = f"{self.base_url}{year}/{filename}"
        output_path = self.output_dir / filename
        
        # Skip if already downloaded
        if output_path.exists():
            logger.debug(f"Skipping {filename} (already exists)")
            return filename, True, None
        
        try:
            if session is None:
                session = self._get_session()
            
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Save file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded {filename}")
            return filename, True, None
            
        except requests.RequestException as e:
            logger.warning(f"Failed to download {filename}: {e}")
            return filename, False, str(e)
    
    def download_year(
        self,
        year: int,
        progress: bool = True
    ) -> Dict[str, int]:
        """
        Download all France station files for a year.
        
        Args:
            year: Year to download
            progress: Show progress bar
            
        Returns:
            Dictionary with success/failure counts
        """
        logger.info(f"Starting download for year {year}")
        
        files = self.list_france_stations(year)
        
        if not files:
            logger.warning(f"No files found for year {year}")
            return {"success": 0, "failed": 0}
        
        session = self._get_session()
        
        results = {"success": 0, "failed": 0}
        
        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.download_file, f, year, session): f 
                for f in files
            }
            
            if progress:
                with tqdm(total=len(files), desc=f"Year {year}") as pbar:
                    for future in as_completed(futures):
                        filename, success, error = future.result()
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                        pbar.update(1)
            else:
                for future in as_completed(futures):
                    filename, success, error = future.result()
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
        
        logger.info(f"Year {year} complete: {results}")
        return results
    
    def download_range(
        self,
        start_year: int,
        end_year: int,
        progress: bool = True
    ) -> Dict[str, int]:
        """
        Download all France station files for a range of years.
        
        Args:
            start_year: Start year
            end_year: End year
            progress: Show progress bars
            
        Returns:
            Dictionary with total success/failure counts
        """
        logger.info(f"Downloading France weather data from {start_year} to {end_year}")
        
        total_results = {"success": 0, "failed": 0}
        
        for year in range(start_year, end_year + 1):
            year_results = self.download_year(year, progress=progress)
            total_results["success"] += year_results["success"]
            total_results["failed"] += year_results["failed"]
            
            # Small delay between years to avoid rate limiting
            if year < end_year:
                time.sleep(1)
        
        logger.info(f"Total downloads: {total_results}")
        return total_results
    
    def get_downloaded_files(self) -> List[Path]:
        """
        Get list of downloaded files.
        
        Returns:
            List of file paths
        """
        return list(self.output_dir.glob("*.csv"))
    
    def get_download_stats(self) -> Dict[str, any]:
        """
        Get statistics about downloaded files.
        
        Returns:
            Dictionary with download statistics
        """
        files = self.get_downloaded_files()
        
        total_size = sum(f.stat().st_size for f in files)
        
        # Get years from files
        years = set()
        for f in files:
            year = get_year_from_filename(f.name)
            if year:
                years.add(year)
        
        return {
            "file_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "years": sorted(list(years)),
            "directory": str(self.output_dir)
        }


def run_download(start_year: int = 1990, end_year: int = 2024) -> Dict[str, int]:
    """
    Run weather data download.
    
    Args:
        start_year: Start year
        end_year: End year
        
    Returns:
        Download results
    """
    config = get_config()
    noaa_config = config.get("apis.noaa", {})
    
    downloader = WeatherDownloader()
    
    return downloader.download_range(
        start_year=noaa_config.get("years", {}).get("start", start_year),
        end_year=noaa_config.get("years", {}).get("end", end_year)
    )


if __name__ == "__main__":
    logger.info("Starting weather data download")
    results = run_download()
    logger.info(f"Download complete: {results}")
