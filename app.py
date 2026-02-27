"""
Main Flask application entry point.

This module initializes and configures the Flask application.
"""
import logging
from flask import Flask, render_template
from flask_caching import Cache

from config import get_config


# Initialize Flask extensions
cache = Cache()


def create_app(config_name: str = 'development') -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config_name: Configuration environment (development, production, testing)
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    config_obj = get_config(config_name)
    app.config.from_object(config_obj)
    
    # Initialize extensions
    cache.init_app(app)
    
    # Setup logging
    _setup_logging(app)
    
    # Register blueprints
    from routes.main_routes import main_bp
    from routes.api_routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Context processor to make base_url available in templates
    @app.context_processor
    def inject_base_url():
        return dict(base_url=app.config.get('APPLICATION_ROOT', ''))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return render_template('500.html'), 500
    
    return app


def _setup_logging(app: Flask) -> None:
    """
    Configure application logging.
    
    Args:
        app: Flask application instance
    """
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set Flask logger level
    app.logger.setLevel(log_level)


# Create app instance for gunicorn (when imported as module)
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
