#!/usr/bin/env python
"""Test script to debug NOAA website structure."""

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/"

print(f"Fetching {BASE_URL}...")
response = requests.get(BASE_URL, timeout=30)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')

# Find all links
print("\nAll links in page:")
for link in soup.find_all('a')[:20]:
    href = link.get('href', '')
    if href and not href.startswith('?'):
        print(f"  {href}")

# Find year directories
print("\nYear directories:")
for link in soup.find_all('a'):
    href = link.get('href', '').strip('/')
    if href.isdigit() and len(href) == 4:
        print(f"  {href}")

# Try a specific year
year = 2024
year_url = f"{BASE_URL}{year}/"
print(f"\nFetching {year_url}...")
response2 = requests.get(year_url, timeout=30)
print(f"Status: {response2.status_code}")

soup2 = BeautifulSoup(response2.text, 'html.parser')
print(f"\nLinks in {year} directory:")
for link in soup2.find_all('a')[:10]:
    href = link.get('href', '')
    if href.endswith('.csv'):
        print(f"  {href}")
