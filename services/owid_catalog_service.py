"""
OWID Catalog Service.

This module provides functions to interact with the OWID datasets catalog
via GitHub API and retrieve dataset information.
"""
import re
import logging
from time import time
from typing import List, Dict, Optional, Tuple, Any
from urllib.error import HTTPError as UrlHttpError
import requests
from flask import current_app


logger = logging.getLogger(__name__)

_CATALOG_CACHE: Dict[str, Dict[str, Any]] = {}


class OWIDCatalogError(Exception):
    """Custom exception for OWID catalog operations."""
    pass


def search_datasets(query: str, limit: int = 50, check_availability: bool = False) -> List[Dict[str, str]]:
    """
    Search OWID charts using the official Search API.
    
    Uses https://ourworldindata.org/api/search which indexes all charts
    and pages with full-text search powered by Algolia.
    
    Args:
        query: Search term (e.g., "population", "climate", "2024")
        limit: Maximum number of results to return
        check_availability: If True, check data availability for each result (slower)
        
    Returns:
        List of chart dictionaries with keys: slug, title, description, url, data_available
        
    Raises:
        OWIDCatalogError: If API request fails
    """
    try:
        # Check cache first
        cache_key = f"search:{query}:{limit}"
        if check_availability:
            cache_key += ":checked"
        cached = _get_cached_value(cache_key)
        
        if cached is not None:
            logger.info(f"Returning {len(cached)} cached results for '{query}'")
            return cached
        
        # Use official OWID Search API
        search_url = "https://ourworldindata.org/api/search"
        params = {
            'q': query,
            'type': 'charts',
            'hitsPerPage': min(limit, 100),
            'page': 0
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        # Transform API response to our format
        datasets = []
        for chart in results:
            slug = chart.get('slug', '')
            dataset = {
                'slug': slug,
                'title': chart.get('title', ''),
                'description': chart.get('subtitle', ''),
                'url': f"https://ourworldindata.org/grapher/{slug}",
                'data_available': None  # Will be populated if check_availability is True
            }
            
            # Check availability if requested (slower but informative)
            if check_availability and slug:
                csv_available, json_available = check_csv_availability(slug)
                dataset['data_available'] = csv_available or json_available
                dataset['csv_available'] = csv_available
                dataset['json_available'] = json_available
            
            datasets.append(dataset)
        
        # Limit to requested number
        datasets = datasets[:limit]
        
        # Cache results
        _set_cached_value(cache_key, datasets, 3600)  # 1 hour cache
        
        logger.info(f"Found {len(datasets)} charts matching '{query}' via OWID Search API")
        return datasets
        
    except requests.RequestException as e:
        logger.error(f"Failed to search OWID API: {e}")
        raise OWIDCatalogError(f"Failed to search OWID: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise OWIDCatalogError(f"Search failed: {str(e)}")


def _get_datasets_index() -> List[Dict[str, Any]]:
    """
    Get list of all datasets from GitHub repository.
    Uses caching to minimize API calls.
    """
    cached = _get_cached_value('datasets_index')
    
    if cached is not None:
        return cached
    
    try:
        api_url = f"{current_app.config['OWID_GITHUB_API']}/contents/datasets"
        headers = _get_request_headers()
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 403:
            logger.error("GitHub API rate limit exceeded")
            return []
        
        response.raise_for_status()
        
        # Filter only directories
        datasets = [d for d in response.json() if d['type'] == 'dir']
        
        _set_cached_value('datasets_index', datasets, 3600)  # Cache for 1 hour
        
        logger.info(f"Loaded {len(datasets)} datasets from GitHub")
        return datasets
        
    except Exception as e:
        logger.error(f"Failed to load datasets index: {e}")
        return []


def _get_dataset_metadata(slug: str) -> Dict[str, Any]:
    """
    Get metadata from datapackage.json for a dataset.
    Uses caching to avoid repeated API calls.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Dictionary with title, description, keywords
    """
    cache_key = f"metadata:{slug}"
    cached = _get_cached_value(cache_key)
    
    if cached is not None:
        return cached
    
    try:
        # Try to get datapackage.json
        datapackage_url = (
            f"https://raw.githubusercontent.com/owid/owid-datasets/master"
            f"/datasets/{slug}/datapackage.json"
        )
        headers = _get_request_headers()
        response = requests.get(datapackage_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract metadata
            metadata = {
                'description': data.get('description', ''),
                'keywords': data.get('keywords', []),
                'title': data.get('title', ''),
                'sources': data.get('sources', [])
            }
            
            # Cache for longer since it changes rarely
            _set_cached_value(cache_key, metadata, 86400)  # 24 hours
            
            return metadata
        
    except Exception as e:
        logger.debug(f"Could not fetch metadata for {slug}: {e}")
    
    # Return empty metadata on error
    return {'description': '', 'keywords': [], 'title': '', 'sources': []}


def check_csv_availability(slug: str) -> tuple[bool, bool]:
    """
    Check if data files are available for a dataset.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Tuple of (csv_available, json_available)
    """
    csv_url = f"https://ourworldindata.org/grapher/{slug}.csv"
    json_url = f"https://ourworldindata.org/grapher/{slug}.json"
    
    csv_available = False
    json_available = False
    
    try:
        # Check CSV availability
        response = requests.head(csv_url, timeout=5, allow_redirects=True)
        csv_available = response.status_code == 200
    except requests.RequestException:
        pass
    
    try:
        # Check JSON availability
        response = requests.head(json_url, timeout=5, allow_redirects=True)
        json_available = response.status_code == 200
    except requests.RequestException:
        pass
    
    return csv_available, json_available


def get_dataset_info(slug: str) -> Dict[str, Any]:
    """
    Get chart information from OWID.
    
    Args:
        slug: Chart identifier (e.g., 'gdp-per-capita-worldbank')
        
    Returns:
        Dictionary with chart metadata including csv_available flag
        
    Raises:
        OWIDCatalogError: If chart not found
    """
    try:
        cache_key = f"chart_info:{slug}"
        cached = _get_cached_value(cache_key)
        
        if cached is not None:
            return cached
        
        # Try to get data from the chart's JSON endpoint
        chart_url = f"https://ourworldindata.org/grapher/{slug}.json"
        response = requests.get(chart_url, timeout=10)

        # Check data availability (CSV and JSON)
        csv_available, json_available = check_csv_availability(slug)
        data_available = csv_available or json_available

        if response.status_code == 404:
            logger.warning(f"Chart JSON not found for {slug}, using fallback info")
            info = {
                'slug': slug,
                'title': _format_title(slug),
                'description': (
                    "Chart data from Our World in Data. "
                    "Visit ourworldindata.org to explore."
                ),
                'csv_url': f"https://ourworldindata.org/grapher/{slug}.csv",
                'json_url': f"https://ourworldindata.org/grapher/{slug}.json",
                'github_url': f"https://github.com/owid/owid-datasets/tree/master/datasets/{slug}",
                'csv_available': csv_available,
                'json_available': json_available,
                'data_available': data_available
            }
        else:
            response.raise_for_status()
            data = response.json()
            info = {
                'slug': slug,
                'title': data.get('title', slug),
                'description': data.get('subtitle', ''),
                'csv_url': f"https://ourworldindata.org/grapher/{slug}.csv",
                'json_url': f"https://ourworldindata.org/grapher/{slug}.json",
                'github_url': f"https://github.com/owid/owid-datasets/tree/master/datasets/{slug}",
                'csv_available': csv_available,
                'json_available': json_available,
                'data_available': data_available
            }
        
        _set_cached_value(cache_key, info, 86400)  # 24 hour cache
        
        return info
        
    except requests.RequestException as e:
        logger.error(f"Failed to get chart info for {slug}: {e}")
        raise OWIDCatalogError(f"Failed to retrieve chart info: {str(e)}")


def get_dataset_url(slug: str) -> str:
    """
    Get direct URL to download dataset CSV.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Direct download URL for CSV file
    """
    # Use dataset metadata to resolve CSV download URL.
    info = get_dataset_info(slug)
    return info['csv_url']


def list_countries(slug: str) -> List[str]:
    """
    Extract list of unique countries from a dataset.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Sorted list of country names (empty list if unavailable)
        
    Note:
        This function loads the dataset to extract countries.
        Returns empty list if CSV is not accessible.
    """
    from services.data_cleaner_service import load_csv_stream, DataCleanerError
    
    try:
        # Load a sample to infer country column values.
        csv_url = get_dataset_url(slug)
        
        try:
            # Read only first chunk to get countries
            df = load_csv_stream(csv_url, sample_size=10000)
        except (
            FileNotFoundError,
            requests.RequestException,
            UrlHttpError,
            DataCleanerError,
        ) as e:
            # CSV not available - return empty list
            logger.warning(f"CSV not accessible for {slug}: {e}")
            return []
        
        # Common column names for country/entity
        country_cols = ['Entity', 'Country', 'country', 'entity']
        
        for col in country_cols:
            if col in df.columns:
                countries = sorted(df[col].dropna().unique().tolist())
                logger.info(f"Found {len(countries)} countries in {slug}")
                return countries
        
        logger.warning(f"No country column found in {slug}")
        return []
        
    except Exception as e:
        logger.error(f"Failed to list countries for {slug}: {e}")
        return []


def list_years(slug: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Get the year range available in a dataset.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Tuple of (min_year, max_year) or (None, None) if unavailable
    """
    import pandas as pd
    from services.data_cleaner_service import load_csv_stream, DataCleanerError
    
    try:
        # Load a sample to infer year range.
        csv_url = get_dataset_url(slug)
        
        try:
            # Read sample to determine year range
            df = load_csv_stream(csv_url, sample_size=10000)
        except (
            FileNotFoundError,
            requests.RequestException,
            UrlHttpError,
            DataCleanerError,
        ) as e:
            # CSV not available - return None
            logger.warning(f"CSV not accessible for {slug}: {e}")
            return None, None
        
        # Common column names for year
        year_cols = ['Year', 'year', 'date', 'Date']
        
        for col in year_cols:
            if col in df.columns:
                years = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(years) > 0:
                    min_year = int(years.min())
                    max_year = int(years.max())
                    logger.info(f"Year range for {slug}: {min_year}-{max_year}")
                    return min_year, max_year
        
        logger.warning(f"No year column found in {slug}")
        return None, None
        
    except Exception as e:
        logger.error(f"Failed to get year range for {slug}: {e}")
        return None, None


def _format_title(slug: str) -> str:
    """
    Convert dataset slug to readable title.
    
    Args:
        slug: Dataset identifier (e.g., 'co2-emissions-by-country')
        
    Returns:
        Formatted title (e.g., 'CO2 Emissions by Country')
    """
    # Replace hyphens and underscores with spaces.
    title = re.sub(r'[-_]', ' ', slug)
    
    # Capitalize each word.
    title = title.title()
    
    return title


def _get_request_headers() -> Dict[str, str]:
    """
    Build GitHub API headers with optional authentication.
    """
    # Use token-based auth to increase rate limits when configured.
    headers = {'Accept': 'application/vnd.github.v3+json'}
    token = current_app.config.get('GITHUB_TOKEN')

    if token:
        headers['Authorization'] = f"Bearer {token}"

    return headers


def _get_cache_ttl() -> int:
    """
    Read cache TTL for catalog responses.
    """
    # Default to a short TTL to balance freshness and rate limits.
    return int(current_app.config.get('OWID_CATALOG_CACHE_TTL', 300))


def _get_cached_value(key: str) -> Optional[Any]:
    """
    Retrieve cached value if it is still valid.
    """
    # Return cached data only while within TTL.
    entry = _CATALOG_CACHE.get(key)

    if not entry:
        return None

    if time() >= entry['expires_at']:
        _CATALOG_CACHE.pop(key, None)
        return None

    return entry['value']


def _set_cached_value(key: str, value: Any, ttl_seconds: int) -> None:
    """
    Store value in cache with expiration.
    """
    # Cache responses to reduce repeated GitHub API calls.
    _CATALOG_CACHE[key] = {
        'value': value,
        'expires_at': time() + ttl_seconds,
    }
