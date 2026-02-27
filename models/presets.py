"""
Preset Filter Models.

This module defines preset filter configurations for common use cases.
"""
from datetime import datetime
from typing import Dict, List, Callable, Any


# Country groups
COUNTRY_GROUPS: Dict[str, List[str]] = {
    'g7': [
        'United States', 'Canada', 'United Kingdom', 'France', 
        'Germany', 'Italy', 'Japan'
    ],
    'g20': [
        'Argentina', 'Australia', 'Brazil', 'Canada', 'China', 'France',
        'Germany', 'India', 'Indonesia', 'Italy', 'Japan', 'Mexico',
        'Russia', 'Saudi Arabia', 'South Africa', 'South Korea',
        'Turkey', 'United Kingdom', 'United States'
    ],
    'eu': [
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czechia',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece',
        'Hungary', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg',
        'Malta', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia',
        'Slovenia', 'Spain', 'Sweden'
    ],
    'brics': [
        'Brazil', 'Russia', 'India', 'China', 'South Africa'
    ],
    'latam': [
        'Argentina', 'Bolivia', 'Brazil', 'Chile', 'Colombia', 'Costa Rica',
        'Cuba', 'Dominican Republic', 'Ecuador', 'El Salvador', 'Guatemala',
        'Haiti', 'Honduras', 'Mexico', 'Nicaragua', 'Panama', 'Paraguay',
        'Peru', 'Uruguay', 'Venezuela'
    ],
    'africa': [
        'Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso', 'Burundi',
        'Cameroon', 'Cape Verde', 'Central African Republic', 'Chad', 'Comoros',
        'Congo', 'Democratic Republic of Congo', 'Djibouti', 'Egypt',
        'Equatorial Guinea', 'Eritrea', 'Eswatini', 'Ethiopia', 'Gabon',
        'Gambia', 'Ghana', 'Guinea', 'Guinea-Bissau', 'Kenya', 'Lesotho',
        'Liberia', 'Libya', 'Madagascar', 'Malawi', 'Mali', 'Mauritania',
        'Mauritius', 'Morocco', 'Mozambique', 'Namibia', 'Niger', 'Nigeria',
        'Rwanda', 'Sao Tome and Principe', 'Senegal', 'Seychelles',
        'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan', 'Sudan',
        'Tanzania', 'Togo', 'Tunisia', 'Uganda', 'Zambia', 'Zimbabwe'
    ],
    'asia_pacific': [
        'Afghanistan', 'Australia', 'Bangladesh', 'Bhutan', 'Brunei',
        'Cambodia', 'China', 'Fiji', 'India', 'Indonesia', 'Japan',
        'Kazakhstan', 'Kyrgyzstan', 'Laos', 'Malaysia', 'Maldives',
        'Mongolia', 'Myanmar', 'Nepal', 'New Zealand', 'North Korea',
        'Pakistan', 'Papua New Guinea', 'Philippines', 'Samoa',
        'Singapore', 'Solomon Islands', 'South Korea', 'Sri Lanka',
        'Taiwan', 'Tajikistan', 'Thailand', 'Timor', 'Tonga',
        'Turkmenistan', 'Uzbekistan', 'Vanuatu', 'Vietnam'
    ],
    'south_america': [
        'Argentina', 'Bolivia', 'Brazil', 'Chile', 'Colombia', 'Ecuador',
        'Guyana', 'Paraguay', 'Peru', 'Suriname', 'Uruguay', 'Venezuela'
    ]
}


def _get_last_n_years(n: int) -> tuple:
    """Get year range for last N years."""
    current_year = datetime.now().year
    return (current_year - n, current_year)


def _get_century_21() -> tuple:
    """Get year range for 21st century."""
    return (2000, datetime.now().year)


# Time period presets
TIME_PRESETS: Dict[str, Callable[[], tuple]] = {
    'last_5_years': lambda: _get_last_n_years(5),
    'last_10_years': lambda: _get_last_n_years(10),
    'last_20_years': lambda: _get_last_n_years(20),
    'century_21': _get_century_21,
    'decade_2020s': lambda: (2020, datetime.now().year),
    'decade_2010s': lambda: (2010, 2019),
    'decade_2000s': lambda: (2000, 2009),
}


def get_preset_config(preset_type: str, preset_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific preset.
    
    Args:
        preset_type: Type of preset ('country' or 'time')
        preset_name: Name of the preset
        
    Returns:
        Configuration dictionary with filter parameters
        
    Raises:
        ValueError: If preset not found
    """
    if preset_type == 'country':
        if preset_name not in COUNTRY_GROUPS:
            raise ValueError(f"Country preset '{preset_name}' not found")
        
        return {
            'countries': COUNTRY_GROUPS[preset_name]
        }
    
    elif preset_type == 'time':
        if preset_name not in TIME_PRESETS:
            raise ValueError(f"Time preset '{preset_name}' not found")
        
        start_year, end_year = TIME_PRESETS[preset_name]()
        return {
            'start_year': start_year,
            'end_year': end_year
        }
    
    else:
        raise ValueError(f"Unknown preset type: {preset_type}")


def list_available_presets() -> Dict[str, List[str]]:
    """
    Get all available preset names organized by type.
    
    Returns:
        Dictionary with keys 'country' and 'time', each containing list of preset names
    """
    return {
        'country': sorted(COUNTRY_GROUPS.keys()),
        'time': sorted(TIME_PRESETS.keys())
    }


def get_preset_description(preset_type: str, preset_name: str) -> str:
    """
    Get human-readable description of a preset.
    
    Args:
        preset_type: Type of preset ('country' or 'time')
        preset_name: Name of the preset
        
    Returns:
        Description string
    """
    descriptions = {
        'country': {
            'g7': 'Group of Seven (G7) countries',
            'g20': 'Group of Twenty (G20) countries',
            'eu': 'European Union member states',
            'brics': 'BRICS countries (Brazil, Russia, India, China, South Africa)',
            'latam': 'Latin American countries',
            'africa': 'African countries',
            'asia_pacific': 'Asia-Pacific countries',
            'south_america': 'South American countries'
        },
        'time': {
            'last_5_years': 'Last 5 years',
            'last_10_years': 'Last 10 years',
            'last_20_years': 'Last 20 years',
            'century_21': '21st Century (2000-present)',
            'decade_2020s': '2020s decade',
            'decade_2010s': '2010s decade (2010-2019)',
            'decade_2000s': '2000s decade (2000-2009)'
        }
    }
    
    if preset_type in descriptions and preset_name in descriptions[preset_type]:
        return descriptions[preset_type][preset_name]
    
    return preset_name.replace('_', ' ').title()
