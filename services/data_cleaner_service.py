"""
Data Cleaner Service.

This module provides functions to filter and clean OWID datasets
based on user-specified criteria.
"""
import io
import logging
from typing import List, Dict, Optional
import requests
import pandas as pd


logger = logging.getLogger(__name__)


def load_data_from_json(slug: str, sample_size: Optional[int] = None) -> pd.DataFrame:
    """
    Load dataset from OWID grapher JSON endpoint as fallback when CSV is not available.

    Args:
        slug: Dataset identifier (e.g., 'ipcc-scenarios')
        sample_size: Maximum number of rows to return (None for all)

    Returns:
        Pandas DataFrame with loaded data

    Raises:
        DataCleanerError: If loading fails or data format is unsupported
    """
    try:
        json_url = f"https://ourworldindata.org/grapher/{slug}.json"
        logger.info(f"Attempting to load data from JSON endpoint: {json_url}")

        response = requests.get(json_url, timeout=15)
        if response.status_code == 404:
            raise DataCleanerError(f"JSON data not found for dataset: {slug}")
        response.raise_for_status()

        data = response.json()

        # Extract data from JSON structure
        # OWID grapher JSON has a specific structure with 'data' or 'values' field
        df = None

        # Try different data structures
        if 'data' in data:
            # Standard grapher format with 'data' array
            df = pd.DataFrame(data['data'])
        elif 'values' in data:
            # Alternative format with 'values'
            df = pd.DataFrame(data['values'])
        elif 'table' in data and 'data' in data['table']:
            # Table-based format
            table_data = data['table']['data']
            if isinstance(table_data, dict):
                # Convert dict of arrays to DataFrame
                df = pd.DataFrame(table_data)
            elif isinstance(table_data, list):
                df = pd.DataFrame(table_data)
        else:
            # Try to find any array field that could be data
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    df = pd.DataFrame(value)
                    logger.info(f"Found data in field '{key}'")
                    break

        if df is None or df.empty:
            raise DataCleanerError(
                f"Could not extract data from JSON for {slug}. "
                "The dataset may have an unsupported format."
            )

        # Rename common columns to standard names
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['entity', 'country', 'location']:
                column_mapping[col] = 'Entity'
            elif col_lower in ['year', 'date', 'time']:
                column_mapping[col] = 'Year'
            elif col_lower in ['value', 'values', 'y']:
                # Try to use the chart title or slug as column name
                title = data.get('title', slug)
                column_mapping[col] = title

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # Apply sample size limit
        if sample_size and len(df) > sample_size:
            df = df.head(sample_size)

        logger.info(f"Successfully loaded {len(df)} rows from JSON for {slug}")
        return df

    except DataCleanerError:
        raise
    except requests.RequestException as e:
        logger.error(f"Failed to load JSON data for {slug}: {e}")
        raise DataCleanerError(f"Failed to load dataset data: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to parse JSON data for {slug}: {e}")
        raise DataCleanerError(f"Failed to parse dataset data: {str(e)}")


class DataCleanerError(Exception):
    """Custom exception for data cleaning operations."""
    pass


def load_csv_stream(url: str, sample_size: Optional[int] = 10000) -> pd.DataFrame:
    """
    Load CSV data from URL with optional sampling.
    
    Args:
        url: Direct URL to CSV file
        sample_size: Number of rows to load (None for all)
        
    Returns:
        Pandas DataFrame with loaded data
        
    Raises:
        DataCleanerError: If loading fails
    """
    try:
        headers = {
            "User-Agent": "OWIDCleaner/1.0 (+https://ourworldindata.org)"
        }
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 403:
            raise DataCleanerError(
                "Dataset CSV access denied (HTTP 403)."
            )
        response.raise_for_status()

        buffer = io.BytesIO(response.content)
        if sample_size:
            df = pd.read_csv(buffer, nrows=sample_size)
        else:
            df = pd.read_csv(buffer)
        
        logger.info(f"Loaded {len(df)} rows from {url}")
        return df
        
    except DataCleanerError:
        raise
    except requests.RequestException as e:
        logger.error(f"Failed to load CSV from {url}: {e}")
        raise DataCleanerError(f"Failed to load dataset: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to load CSV from {url}: {e}")
        raise DataCleanerError(f"Failed to load dataset: {str(e)}")


def filter_countries(
    df: pd.DataFrame, 
    countries: List[str],
    country_col: Optional[str] = None
) -> pd.DataFrame:
    """
    Filter dataframe to include only specified countries.
    
    Args:
        df: Input dataframe
        countries: List of country names to include
        country_col: Name of country column (auto-detected if None)
        
    Returns:
        Filtered dataframe
        
    Raises:
        DataCleanerError: If country column not found
    """
    if not countries:
        return df
    
    # Auto-detect country column
    if country_col is None:
        country_col = _find_country_column(df)
    
    if country_col not in df.columns:
        raise DataCleanerError(f"Country column '{country_col}' not found")
    
    # Filter by countries (case-insensitive)
    countries_lower = [c.lower() for c in countries]
    mask = df[country_col].str.lower().isin(countries_lower)
    filtered = df[mask].copy()
    
    logger.info(f"Filtered to {len(filtered)} rows for {len(countries)} countries")
    return filtered


def filter_years(
    df: pd.DataFrame,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    year_col: Optional[str] = None
) -> pd.DataFrame:
    """
    Filter dataframe to include only specified year range.
    
    Args:
        df: Input dataframe
        start_year: Minimum year (inclusive)
        end_year: Maximum year (inclusive)
        year_col: Name of year column (auto-detected if None)
        
    Returns:
        Filtered dataframe
        
    Raises:
        DataCleanerError: If year column not found
    """
    if start_year is None and end_year is None:
        return df
    
    # Auto-detect year column
    if year_col is None:
        year_col = _find_year_column(df)
    
    if year_col not in df.columns:
        raise DataCleanerError(f"Year column '{year_col}' not found")
    
    # Convert to numeric
    df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
    
    # Apply filters
    mask = pd.Series([True] * len(df), index=df.index)
    
    if start_year is not None:
        mask &= df[year_col] >= start_year
    
    if end_year is not None:
        mask &= df[year_col] <= end_year
    
    filtered = df[mask].copy()
    
    logger.info(f"Filtered to {len(filtered)} rows for years {start_year}-{end_year}")
    return filtered


def filter_columns(
    df: pd.DataFrame,
    columns: List[str]
) -> pd.DataFrame:
    """
    Select specific columns from dataframe.
    
    Args:
        df: Input dataframe
        columns: List of column names to keep
        
    Returns:
        Dataframe with selected columns
        
    Raises:
        DataCleanerError: If any column not found
    """
    if not columns:
        return df
    
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise DataCleanerError(f"Columns not found: {', '.join(missing)}")
    
    filtered = df[columns].copy()
    
    logger.info(f"Selected {len(columns)} columns")
    return filtered


def apply_preset(
    df: pd.DataFrame,
    preset: str,
    presets_config: Dict
) -> pd.DataFrame:
    """
    Apply a preset filter configuration.
    
    Args:
        df: Input dataframe
        preset: Preset name
        presets_config: Dictionary of preset configurations
        
    Returns:
        Filtered dataframe
        
    Raises:
        DataCleanerError: If preset not found
    """
    if preset not in presets_config:
        raise DataCleanerError(f"Preset '{preset}' not found")
    
    config = presets_config[preset]
    result = df.copy()
    
    # Apply country filter if specified
    if 'countries' in config:
        result = filter_countries(result, config['countries'])
    
    # Apply year filter if specified
    if 'start_year' in config or 'end_year' in config:
        result = filter_years(
            result,
            config.get('start_year'),
            config.get('end_year')
        )
    
    # Apply column filter if specified
    if 'columns' in config:
        result = filter_columns(result, config['columns'])
    
    logger.info(f"Applied preset '{preset}': {len(result)} rows remaining")
    return result


def export_csv(df: pd.DataFrame) -> io.BytesIO:
    """
    Export dataframe to CSV in BytesIO buffer.
    
    Args:
        df: Dataframe to export
        
    Returns:
        BytesIO buffer containing CSV data
    """
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    
    logger.info(f"Exported {len(df)} rows to CSV")
    return buffer


def get_column_info(df: pd.DataFrame) -> List[Dict[str, any]]:
    """
    Get information about dataframe columns.
    
    Args:
        df: Input dataframe
        
    Returns:
        List of column info dictionaries with name, type, null_count
    """
    columns = []
    
    for col in df.columns:
        columns.append({
            'name': col,
            'type': str(df[col].dtype),
            'null_count': int(df[col].isnull().sum()),
            'unique_count': int(df[col].nunique())
        })
    
    return columns


def _find_country_column(df: pd.DataFrame) -> str:
    """
    Auto-detect country/entity column name.
    
    Args:
        df: Input dataframe
        
    Returns:
        Column name
        
    Raises:
        DataCleanerError: If no country column found
    """
    candidates = ['Entity', 'Country', 'country', 'entity', 'location', 'Location']
    
    for col in candidates:
        if col in df.columns:
            return col
    
    raise DataCleanerError("Could not find country/entity column")


def _find_year_column(df: pd.DataFrame) -> str:
    """
    Auto-detect year column name.
    
    Args:
        df: Input dataframe
        
    Returns:
        Column name
        
    Raises:
        DataCleanerError: If no year column found
    """
    candidates = ['Year', 'year', 'Date', 'date', 'time', 'Time']
    
    for col in candidates:
        if col in df.columns:
            return col
    
    raise DataCleanerError("Could not find year/date column")
