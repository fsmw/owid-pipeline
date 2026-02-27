# OWID Dataset Cleaner

A modern web application for searching, filtering, and downloading datasets from Our World in Data (OWID).

## Features

- 🔍 **Search** through all OWID datasets by keywords
- 🌍 **Filter by countries** using preset groups (G7, G20, EU, etc.) or custom selection
- 📅 **Filter by time** using preset periods or custom year ranges
- 📊 **Preview** filtered data before downloading
- ⬇️ **Download** cleaned CSV files ready for analysis
- ✨ **Clean, modern UI** built with Tailwind CSS and Alpine.js

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Installation

1. Clone the repository or navigate to the project directory:

```bash
cd owid-cleaner
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

#### Development Mode

```bash
python app.py
```

The application will be available at `http://localhost:5000`

#### Production Mode

```bash
export FLASK_ENV=production
export SECRET_KEY="your-secret-key-here"
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Production Deployment (Ubuntu + Nginx)

### Prerequisites

- Ubuntu 20.04+ server
- Domain name (optional but recommended)
- SSH access with sudo privileges

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx
```

### Step 2: Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/owid-cleaner
sudo chown $USER:$USER /opt/owid-cleaner

# Copy application files (from your local machine or git clone)
cp -r . /opt/owid-cleaner/

# Create virtual environment and install dependencies
cd /opt/owid-cleaner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Step 3: Create Environment File

```bash
sudo nano /opt/owid-cleaner/.env
```

Add the following:

```env
FLASK_ENV=production
SECRET_KEY=your-secure-random-secret-key-here
APPLICATION_ROOT=/pipeline
PORT=5050
GITHUB_TOKEN=your_github_token_optional
```

**Environment Variables:**
- `FLASK_ENV`: Set to `production` for deployment
- `SECRET_KEY`: Random secret key for session security
- `APPLICATION_ROOT`: Base URL path (e.g., `/pipeline`) when behind reverse proxy
- `PORT`: Port for gunicorn (default: 5000)
- `GITHUB_TOKEN`: Optional, increases GitHub API rate limits

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4: Install Systemd Service

```bash
# Copy the service file
sudo cp /opt/owid-cleaner/owid-cleaner.service /etc/systemd/system/

# Edit if needed (user, paths, etc.)
sudo nano /etc/systemd/system/owid-cleaner.service

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable owid-cleaner
sudo systemctl start owid-cleaner

# Check status
sudo systemctl status owid-cleaner
```

### Step 5: Configure Nginx

```bash
# Copy nginx configuration
sudo cp /opt/owid-cleaner/nginx.conf.example /etc/nginx/sites-available/owid-cleaner

# Edit configuration (change server_name to your domain)
sudo nano /etc/nginx/sites-available/owid-cleaner
```

Update `server_name` to your domain:
```nginx
server_name your-domain.com;
```

Enable the site:
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/owid-cleaner /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 6: Firewall (Optional but Recommended)

```bash
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Step 7: SSL with Let's Encrypt (Optional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Verify Installation

Visit `http://your-domain.com/pipeline` (or `http://your-ip/pipeline`)

### Useful Commands

```bash
# View application logs
sudo journalctl -u owid-cleaner -f

# Restart application
sudo systemctl restart owid-cleaner

# Reload nginx
sudo systemctl reload nginx

# Check application status
sudo systemctl status owid-cleaner
```

### Troubleshooting

**502 Bad Gateway:**
- Check if the Flask app is running: `sudo systemctl status owid-cleaner`
- Check logs: `sudo journalctl -u owid-cleaner -n 50`

**Static files not loading:**
- Ensure nginx configuration has correct paths
- Check nginx error logs: `sudo tail -f /var/log/nginx/error.log`

**Permission denied:**
- Ensure files are owned by correct user: `sudo chown -R www-data:www-data /opt/owid-cleaner`
- Check file permissions: `ls -la /opt/owid-cleaner`

## Usage

### 1. Search for Datasets

- Visit the home page
- Enter search terms (e.g., "climate", "population", "covid")
- Browse results and click on a dataset to view details

### 2. Apply Filters

**Country Groups** (Presets):
- G7: United States, Canada, UK, France, Germany, Italy, Japan
- G20: All G20 member countries
- EU: European Union member states
- BRICS: Brazil, Russia, India, China, South Africa
- Latin America, South America, Africa, Asia-Pacific

**Time Periods** (Presets):
- Last 5/10/20 years
- 21st Century (2000-present)
- By decade (2020s, 2010s, 2000s)
- Custom year range

### 3. Preview and Download

- Click "Apply Filters" to see a preview of the filtered data
- Review all rows and column statistics with interactive table (search, sort)
- Click "Download CSV" to get the complete filtered dataset

## Project Structure

```
owid-cleaner/
├── app.py                          # Flask application entry point
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── owid-cleaner.service            # Systemd service file
├── nginx.conf.example              # Nginx configuration example
├── .gitignore                      # Git ignore rules
├── services/
│   ├── owid_catalog_service.py    # OWID API interaction
│   └── data_cleaner_service.py    # Data filtering logic
├── routes/
│   ├── main_routes.py             # Web page routes
│   └── api_routes.py              # REST API endpoints
├── models/
│   └── presets.py                 # Filter preset definitions
├── templates/
│   ├── base.html                  # Base template
│   ├── index.html                 # Search page
│   ├── dataset.html               # Dataset detail page
│   ├── about.html                 # About page
│   └── *.html                     # Error pages
└── static/
    └── (static assets served via CDN)
```

## API Endpoints

### Search Datasets
```
GET /api/search?q=<query>&limit=<limit>
```

### Get Dataset Info
```
GET /api/dataset/<slug>/info
```

### Preview Filtered Data
```
POST /api/dataset/<slug>/preview
Content-Type: application/json

{
  "preset_country": "g7",
  "preset_time": "last_10_years",
  "countries": ["United States", "Canada"],
  "start_year": 2010,
  "end_year": 2020,
  "columns": ["Entity", "Year", "Value"]
}
```

### Download Filtered CSV
```
POST /api/dataset/<slug>/download
Content-Type: application/json

{
  "preset_country": "g7",
  "start_year": 2015,
  "end_year": 2023
}
```

### List Available Presets
```
GET /api/presets
```

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Tailwind CSS, Alpine.js, Grid.js
- **Data Processing**: Pandas
- **Caching**: Flask-Caching
- **Data Source**: OWID GitHub Repository

## Configuration

Environment variables (optional):

```bash
export FLASK_ENV=development|production
export SECRET_KEY=your-secret-key
export FLASK_DEBUG=1  # Development only
export APPLICATION_ROOT=/pipeline  # Base URL path when behind reverse proxy
export PORT=5050  # Port for gunicorn (production, default: 5000)
export GITHUB_TOKEN=your_github_personal_access_token  # Increases API rate limits
export OWID_CATALOG_CACHE_TTL=3600  # Cache dataset list for 1 hour
export OWID_METADATA_CACHE_TTL=86400  # Cache metadata for 24 hours
```

Configuration can also be modified in `config.py`:
- Cache timeout settings
- Catalog cache TTL and GitHub token
- Dataset size limits
- API rate limits
- Chunk sizes for streaming

## Development

### Code Style

This project follows PEP 8 Python coding standards:
- Type hints for all function signatures
- Docstrings for all public functions
- Maximum line length: 79 characters
- 4 spaces for indentation

### Adding New Presets

Edit `models/presets.py`:

```python
COUNTRY_GROUPS['my_group'] = ['Country1', 'Country2']

TIME_PRESETS['my_period'] = lambda: (start_year, end_year)
```

### Architecture

See `design-log/001-owid-dataset-cleaner.md` for detailed architecture documentation and design decisions.

## How Search Works

The search feature indexes datasets by:
- **Dataset name** (directory name in GitHub repo)
- **Title** (formatted from dataset name)
- **Metadata** from `datapackage.json` (title, description, keywords)
- **Full-text matching** with relevance scoring

Results are ranked by relevance:
1. Exact matches in dataset name
2. Matches in dataset title
3. Matches in description and keywords
4. Individual term matches

## Caching Strategy

To minimize GitHub API calls:
- Dataset catalog: cached for 1 hour (configurable via `OWID_CATALOG_CACHE_TTL`)
- Dataset metadata: cached for 24 hours (configurable via `OWID_METADATA_CACHE_TTL`)

## Limitations

- Datasets are loaded from OWID's GitHub repository
- GitHub API has rate limits (60 requests/hour unauthenticated, 5000/hour authenticated)
- Set `GITHUB_TOKEN` environment variable to increase rate limits
- Large datasets may take time to process and load in browser
- First search may take longer as metadata is fetched and cached

## Data Source

All data comes from [Our World in Data](https://ourworldindata.org), a scientific online publication that focuses on large global problems.

**Note**: This is an independent tool and is not officially affiliated with Our World in Data.

## License

This project is for educational and research purposes.

## Contributing

Contributions are welcome! Please follow:
1. PEP 8 coding standards
2. Add type hints and docstrings
3. Update design log for architectural changes
4. Test thoroughly before submitting

## Support

For issues or questions, please refer to the design log documentation or create an issue in the repository.

---

**Built with ❤️ for data researchers and analysts**
