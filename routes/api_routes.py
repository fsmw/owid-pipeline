"""
API routes.

This module defines the RESTful API endpoints.
"""
from typing import Optional
from flask import Blueprint, jsonify, request, send_file, current_app
from werkzeug.exceptions import BadRequest
import logging

from services.owid_catalog_service import (
    search_datasets, get_dataset_info, list_countries, list_years, check_csv_availability
)
from services.data_cleaner_service import (
    load_csv_stream, load_data_from_json, filter_countries, filter_years,
    filter_columns, export_csv, get_column_info, DataCleanerError
)
from models.presets import get_preset_config


logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/search')
def search():
    """
    Search for datasets by query string.
    
    Query params:
        q: Search query (required)
        limit: Maximum results (default: 50)
        
    Returns:
        JSON array of matching datasets
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        limit = int(request.args.get('limit', 50))
        results = search_datasets(query, limit)
        
        return jsonify({
            'query': query,
            'count': len(results),
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dataset/<slug>/info')
def dataset_info(slug: str):
    """
    Get dataset information and metadata.

    Args:
        slug: Dataset identifier

    Returns:
        JSON object with dataset info
    """
    try:
        info = get_dataset_info(slug)

        # Only try to get countries/years if data is available
        if info.get('data_available', False):
            countries = list_countries(slug)
            years = list_years(slug)
        else:
            countries = []
            years = (None, None)

        return jsonify({
            **info,
            'countries': countries,
            'year_range': years
        })

    except Exception as e:
        logger.error(f"Error getting dataset info: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dataset/<slug>/preview', methods=['POST'])
def dataset_preview(slug: str):
    """
    Get preview of filtered dataset.

    Args:
        slug: Dataset identifier

    Request body (JSON):
        countries: List of countries to include (optional)
        start_year: Start year (optional)
        end_year: End year (optional)
        columns: List of columns to include (optional)
        preset_country: Country preset name (optional)
        preset_time: Time preset name (optional)

    Returns:
        JSON with preview data and statistics
    """
    try:
        data = request.get_json()

        # Get dataset info first
        info = get_dataset_info(slug)

        # Check if any data is available (CSV or JSON)
        if not info.get('data_available', False):
            logger.warning(f"Data not available for dataset: {slug}")
            return jsonify({
                'error': 'Dataset not available for download',
                'message': 'This dataset does not have downloadable data. Please visit the Our World in Data website to explore this data.',
                'csv_available': False,
                'json_available': False,
                'dataset': info
            }), 404

        # Try to load data - prefer CSV, fallback to JSON
        df = None
        data_source = None

        if info.get('csv_available', False):
            try:
                df = load_csv_stream(info['csv_url'], sample_size=None)
                data_source = 'csv'
                logger.info(f"Loaded data from CSV for {slug}")
            except DataCleanerError as e:
                logger.warning(f"Failed to load CSV for {slug}: {e}")
                # Will try JSON fallback

        # Fallback to JSON if CSV failed or not available
        if df is None and info.get('json_available', False):
            try:
                df = load_data_from_json(slug, sample_size=None)
                data_source = 'json'
                logger.info(f"Loaded data from JSON fallback for {slug}")
            except DataCleanerError as e:
                logger.error(f"Failed to load JSON for {slug}: {e}")
                return jsonify({
                    'error': 'Dataset not available',
                    'message': str(e),
                    'csv_available': info.get('csv_available', False),
                    'json_available': info.get('json_available', False)
                }), 404

        if df is None:
            return jsonify({
                'error': 'Dataset not available',
                'message': 'Could not load dataset data from any source.',
                'csv_available': False,
                'json_available': False
            }), 404

        # Apply filters
        df = _apply_filters(df, data)

        # Get column info
        columns = get_column_info(df)

        # Return all data
        return jsonify({
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': columns,
            'preview': df.to_dict('records'),
            'data_source': data_source
        })

    except DataCleanerError as e:
        # Handle specific data cleaner errors
        logger.error(f"Preview data error for {slug}: {e}")
        return jsonify({
            'error': 'Dataset not available',
            'message': str(e),
            'csv_available': False
        }), 404

    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dataset/<slug>/download', methods=['POST'])
def dataset_download(slug: str):
    """
    Download filtered dataset as CSV.

    Args:
        slug: Dataset identifier

    Request body (JSON):
        Same as preview endpoint

    Returns:
        CSV file download
    """
    try:
        data = request.get_json()

        # Get dataset info first
        info = get_dataset_info(slug)

        # Check if any data is available
        if not info.get('data_available', False):
            logger.warning(f"Download requested but no data available for: {slug}")
            return jsonify({
                'error': 'Dataset not available for download',
                'message': 'This dataset does not have downloadable data.'
            }), 404

        # Try to load data - prefer CSV, fallback to JSON
        df = None

        if info.get('csv_available', False):
            try:
                df = load_csv_stream(info['csv_url'], sample_size=None)
                logger.info(f"Loaded data from CSV for download: {slug}")
            except DataCleanerError as e:
                logger.warning(f"Failed to load CSV for download {slug}: {e}")
                # Will try JSON fallback

        # Fallback to JSON if CSV failed or not available
        if df is None and info.get('json_available', False):
            try:
                df = load_data_from_json(slug, sample_size=None)
                logger.info(f"Loaded data from JSON fallback for download: {slug}")
            except DataCleanerError as e:
                logger.error(f"Failed to load JSON for download {slug}: {e}")
                return jsonify({
                    'error': 'Dataset not available',
                    'message': str(e)
                }), 404

        if df is None:
            return jsonify({
                'error': 'Dataset not available',
                'message': 'Could not load dataset data from any source.'
            }), 404

        # Apply filters
        df = _apply_filters(df, data)

        # Export to CSV
        csv_buffer = export_csv(df)

        # Create filename
        filename = f"{slug}_filtered.csv"

        logger.info(f"Downloading {len(df)} rows for {slug}")

        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except DataCleanerError as e:
        # Handle specific data cleaner errors
        logger.error(f"Download data error for {slug}: {e}")
        return jsonify({
            'error': 'Dataset not available',
            'message': str(e)
        }), 404

    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/presets')
def list_presets():
    """
    Get list of available filter presets.
    
    Returns:
        JSON with available presets by type
    """
    from models.presets import list_available_presets, get_preset_description
    
    presets = list_available_presets()
    
    # Add descriptions
    result = {}
    for preset_type, names in presets.items():
        result[preset_type] = [
            {
                'name': name,
                'description': get_preset_description(preset_type, name)
            }
            for name in names
        ]
    
    return jsonify(result)


def _is_valid_value(value) -> bool:
    """
    Check if a filter value is valid (not empty, null, or empty list).

    Args:
        value: Value to check

    Returns:
        True if value is valid and should be used
    """
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == '':
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True


def _to_int_or_none(value) -> Optional[int]:
    """
    Convert value to int or return None if invalid.

    Args:
        value: Value to convert

    Returns:
        Integer value or None
    """
    if not _is_valid_value(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _apply_filters(df, filters: dict):
    """
    Apply filter configuration to dataframe.

    Args:
        df: Input dataframe
        filters: Filter configuration dictionary

    Returns:
        Filtered dataframe
    """
    if not filters:
        return df

    # Apply preset filters first
    if _is_valid_value(filters.get('preset_country')):
        try:
            config = get_preset_config('country', filters['preset_country'])
            df = filter_countries(df, config['countries'])
        except ValueError as e:
            logger.warning(f"Invalid country preset: {e}")

    if _is_valid_value(filters.get('preset_time')):
        try:
            config = get_preset_config('time', filters['preset_time'])
            df = filter_years(df, config.get('start_year'), config.get('end_year'))
        except ValueError as e:
            logger.warning(f"Invalid time preset: {e}")

    # Apply custom filters
    if _is_valid_value(filters.get('countries')):
        df = filter_countries(df, filters['countries'])

    start_year = _to_int_or_none(filters.get('start_year'))
    end_year = _to_int_or_none(filters.get('end_year'))

    if start_year is not None or end_year is not None:
        df = filter_years(df, start_year, end_year)

    if _is_valid_value(filters.get('columns')):
        df = filter_columns(df, filters['columns'])

    return df
