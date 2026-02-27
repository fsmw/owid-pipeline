"""
Main application routes.

This module defines the main web page routes.
"""
from flask import Blueprint, render_template, request, current_app
import logging


logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Render the main search page.
    
    Returns:
        Rendered index template
    """
    return render_template('index.html')


@main_bp.route('/dataset/<slug>')
def dataset_detail(slug: str):
    """
    Render dataset detail page with filter options.
    
    Args:
        slug: Dataset identifier
        
    Returns:
        Rendered dataset detail template
    """
    from services.owid_catalog_service import get_dataset_info
    from models.presets import list_available_presets
    
    try:
        # Get dataset info
        dataset_info = get_dataset_info(slug)
        
        # Get available presets
        presets = list_available_presets()
        
        return render_template(
            'dataset.html',
            dataset=dataset_info,
            presets=presets
        )
    
    except Exception as e:
        logger.error(f"Error loading dataset {slug}: {e}")
        return render_template('error.html', error=str(e)), 404


@main_bp.route('/about')
def about():
    """
    Render about page.
    
    Returns:
        Rendered about template
    """
    return render_template('about.html')
