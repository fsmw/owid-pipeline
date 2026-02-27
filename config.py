"""
Application configuration.

This module contains configuration settings for the Flask application.
"""
import os
from typing import Final


class Config:
    """Base configuration class with default settings."""
    
    # Flask settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG: bool = False
    TESTING: bool = False
    APPLICATION_ROOT: str = os.environ.get('APPLICATION_ROOT', '')  # e.g., '/pipeline'
    
    # Cache settings
    CACHE_TYPE: str = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT: int = 300  # 5 minutes
    CACHE_THRESHOLD: int = 100  # Max cached items

    # Catalog cache settings
    # Cache catalog index and metadata to minimize GitHub API calls
    OWID_CATALOG_CACHE_TTL: int = int(
        os.environ.get('OWID_CATALOG_CACHE_TTL', '3600')
    )  # 1 hour for dataset list
    OWID_METADATA_CACHE_TTL: int = int(
        os.environ.get('OWID_METADATA_CACHE_TTL', '86400')
    )  # 24 hours for metadata
    
    # OWID API settings
    OWID_GITHUB_API: Final[str] = 'https://api.github.com/repos/owid/owid-datasets'
    OWID_RAW_DATA: Final[str] = 'https://raw.githubusercontent.com/owid/owid-datasets/master'
    GITHUB_API_RATE_LIMIT: int = 60  # requests per hour for unauthenticated
    GITHUB_TOKEN: str = os.environ.get('GITHUB_TOKEN', '')
    
    # Application settings
    MAX_DATASET_SIZE_MB: int = 500  # Maximum dataset size to process
    CSV_CHUNK_SIZE: int = 10000  # Rows per chunk for streaming
    SEARCH_RESULT_LIMIT: int = 50  # Max search results


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG: bool = True
    CACHE_DEFAULT_TIMEOUT: int = 60  # Shorter cache for development


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG: bool = False
    CACHE_DEFAULT_TIMEOUT: int = 3600  # 1 hour
    
    # Override with environment variables in production
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or os.urandom(32).hex()


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING: bool = True
    CACHE_TYPE: str = 'NullCache'  # Disable caching for tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """
    Get configuration object based on environment.
    
    Args:
        env: Environment name (development, production, testing)
        
    Returns:
        Configuration object instance
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])
