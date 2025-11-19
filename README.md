# CollabTract

**Smart Door-to-Door and Flyering Route Planner**

CollabTract is a web application designed to help optimize door-to-door distribution routes and flyering campaigns. It provides advanced city search functionality, interactive mapping capabilities, and intelligent clustering for route optimization in French cities and addresses.

## 🚀 Features

### Core Functionality

- **City Search**: Search for French cities by name or postal code
- **Interactive Maps**: Generate detailed maps with address markers for selected cities
- **Address Visualization**: Display all addresses within a city with precise location markers
- **Route Clustering**: Intelligent K-means clustering for optimal route planning
- **Color-coded Routes**: Automatic generation of distinct colors for different routes
- **Fuzzy Search**: Intelligent city name matching with similarity scoring
- **Department Support**: Full support for all French departments including overseas territories

### Technical Features

- **FastAPI Backend**: Modern, fast web framework with automatic API documentation
- **Machine Learning**: Scikit-learn integration for K-means clustering algorithms
- **Interactive Web Interface**: Bootstrap-based responsive UI
- **Real-time Data**: Automatic download of latest address data from official French sources
- **Caching**: Local storage of downloaded data for improved performance
- **Error Handling**: Comprehensive error handling and logging
- **Color Generation**: HSV-based distinct color generation for route visualization

## 🏗️ Architecture

### Project Structure

```
CollabTract/
├── src/
│   ├── __init__.py            # Package initialization with version
│   ├── app.py                 # FastAPI application and routes
│   ├── settings.py            # Configuration settings
│   ├── requirements.txt       # Production dependencies
│   ├── requirements-dev.txt   # Development dependencies
│   └── tools/
│       ├── __init__.py            # Package initialization
│       ├── get_city.py            # City search functionality with fuzzy matching
│       ├── map.py                 # Map generation with Folium and clustering
│       ├── csv_loading.py         # Address data loading and caching
│       ├── validation.py          # Input validation utilities
│       ├── color_code.py          # Color generation for route visualization
│       ├── clustering.py          # Clustering algorithms and processing
│       ├── capacitated_kmeans.py  # Capacitated K-means implementation
│       ├── route_types.py         # Pydantic models for API requests
│       └── health.py              # Health check functionality
├── data/
│   ├── communes-france-2025.parquet  # French municipalities database
│   └── csv/                          # Local data storage
│       └── adresses-*.csv.gz         # Address data by department
├── Dockerfile                        # Docker container configuration
├── LICENSE                           # Project license
└── README.md                         # This file
```

### API Endpoints

#### `GET /get_city`

- **Description**: Search for cities by name or postal code
- **Parameters**:
  - `city` (optional): City name to search for
  - `postal_code` (optional): Postal code to search for
- **Response**: JSON with matching cities and department codes

#### `GET /health`

- **Description**: Health check endpoint to verify API and dependencies status
- **Response**: JSON with health status including:
  - `status`: Overall status ("healthy" or "unhealthy")
  - `timestamp`: Current timestamp in ISO format
  - `version`: Application version
  - `uptime`: Application uptime in seconds
  - `checks`: Dictionary of individual component checks (database, etc.)

#### `POST /map`

- **Description**: Generate interactive map with clustering for route optimization
- **Request Body**: MapRequest object with the following fields:
  - `city_name` (string, required): Name of the city to map
  - `department_code` (int|string, required): Department code
  - `cluster_count` (int, optional): Number of clusters for route optimization (default: 1, minimum: 1)
  - `clustering_method` (string, optional): Clustering algorithm - one of:
    - `"kmeans"`: Standard K-means clustering based on geographic coordinates (default)
    - `"balanced_length"`: Capacitated K-means balancing street lengths
    - `"balanced_count"`: Capacitated K-means balancing address counts
  - `cluster_colors` (list[string], optional): Custom hex colors for clusters (must be valid hex codes like "#ff0000")
  - `cluster_id` (int, optional): Filter to show only a specific cluster (0-indexed, must be less than cluster_count)
  - `seed` (int, optional): Random seed for reproducible clustering results (default: 42)
- **Response**: JSON with:
  - `map_html`: HTML content of the interactive Folium map
  - `cluster_stats`: Statistics for each cluster including count, length, and center coordinates

#### `POST /cluster`

- **Description**: Generate clusters for a city and return the dataframe with cluster assignments
- **Request Body**: MapRequest object with the following fields:
  - `city_name` (string, required): Name of the city to cluster
  - `department_code` (int|string, required): Department code
  - `cluster_count` (int, optional): Number of clusters for route optimization (default: 1, minimum: 1)
  - `clustering_method` (string, optional): Clustering algorithm - one of:
    - `"kmeans"`: Standard K-means clustering based on geographic coordinates (default)
    - `"balanced_length"`: Capacitated K-means balancing street lengths
    - `"balanced_count"`: Capacitated K-means balancing address counts
  - `cluster_colors` (list[string], optional): Custom hex colors for clusters (not used in this endpoint but validated)
  - `cluster_id` (int, optional): Filter to return only addresses from a specific cluster (0-indexed, must be less than cluster_count)
  - `seed` (int, optional): Random seed for reproducible clustering results (default: 42)
- **Response**: JSON with:
  - `dataframe`: Array of address records with cluster assignments
  - `cluster_stats`: Dictionary with cluster statistics including count, length, and center coordinates

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd CollabTract
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r src/requirements.txt
   ```

   **Key Dependencies:**

   - `fastapi`: Modern web framework for building APIs
   - `uvicorn`: ASGI server for running FastAPI applications
   - `folium`: Interactive map generation
   - `scikit-learn`: Machine learning library for clustering algorithms
   - `pandas`: Data manipulation and analysis
   - `structlog`: Structured logging
   - `thefuzz`: Fuzzy string matching for city search

4. **Run the application**

   ```bash
   uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - Open your browser and navigate to `http://localhost:8000`
   - API documentation available at `http://localhost:8000/docs`
   - Health check endpoint: `http://localhost:8000/health`

### Docker Deployment

1. **Build the Docker image**

   ```bash
   docker build -t collabtract .
   ```

2. **Run the container**

   ```bash
   docker run -d -p 8000:8000 --name collabtract collabtract
   ```

3. **Access the application**
   - API available at `http://localhost:8000`
   - Health check: `http://localhost:8000/health`

**Note**: Ensure the `data/` directory contains the required data files before building the Docker image, or mount it as a volume.

## 📊 Data Sources

### French Address Database (Base Adresse Locale)

- **Source**: [adresse.data.gouv.fr](https://adresse.data.gouv.fr)
- **Format**: CSV files compressed with gzip
- **Coverage**: All French departments and overseas territories
- **Update Frequency**: Automatic download of latest data

### French Municipalities Database

- **Source**: Official French municipalities data
- **Format**: CSV with postal codes and department codes
- **Coverage**: All French municipalities

## 🔧 Configuration

### Environment Variables

The application uses the following configuration (defined in `src/settings.py`):

- `CSV_FOLDER`: Path to local data storage (default: `./data/csv`)
- `COMMUNES_FRANCE_FILENAME`: Name of the municipalities file

### Data Management

- Address data is automatically downloaded when first requested
- Data is cached locally for improved performance
- Supports all French departments including overseas territories (971-989, 2A, 2B)

## 🎯 Usage

### Basic Workflow

1. **Search for a City**

   ```bash
   curl "http://localhost:8000/get_city?city=Paris"
   ```

2. **Generate a Map with Clustering**

   ```bash
   curl -X POST "http://localhost:8000/map" \
        -H "Content-Type: application/json" \
        -d '{
          "city_name": "Paris",
          "department_code": 75,
          "cluster_count": 5,
          "clustering_method": "kmeans"
        }'
   ```

3. **Custom Route Colors**

   ```bash
   curl -X POST "http://localhost:8000/map" \
        -H "Content-Type: application/json" \
        -d '{
          "city_name": "Lyon",
          "department_code": 69,
          "cluster_count": 3,
          "cluster_colors": ["#ff0000", "#00ff00", "#0000ff"]
        }'
   ```

### Advanced Features

- **Route Clustering**: Automatically groups addresses into optimal delivery routes using multiple clustering algorithms:
  - **K-means**: Standard geographic clustering based on coordinates
  - **Balanced Length**: Capacitated K-means that balances total street length across routes
  - **Balanced Count**: Capacitated K-means that balances address counts across routes
- **Capacitated Clustering**: Advanced algorithm using min-cost flow optimization to ensure balanced route capacities
- **Color Generation**: Automatic generation of distinct colors for different routes using HSV color space
- **Fuzzy Search**: Intelligent matching to find cities even with slight spelling variations using thefuzz library
- **Department Validation**: Automatic validation of department codes including overseas territories
- **Street Analysis**: Automatic detection of street types (center-city vs. side streets) and length estimation
- **Error Handling**: Comprehensive error messages for invalid inputs
- **Reproducible Results**: Seed parameter for consistent clustering results across runs

### Clustering Methods

The application supports three clustering methods:

1. **kmeans** (default): Standard K-means clustering based on geographic coordinates. Uses scikit-learn's KMeans algorithm with k-means++ initialization.

2. **balanced_length**: Capacitated K-means that balances total street length across routes. Uses network flow optimization to ensure routes have similar total street lengths while minimizing geographic distance.

3. **balanced_count**: Capacitated K-means that balances address counts across routes. Uses network flow optimization to ensure routes contain similar numbers of addresses while minimizing geographic distance.

The capacitated methods (`balanced_length` and `balanced_count`) use NetworkX min-cost flow algorithms to solve the assignment problem, ensuring balanced route capacities while minimizing geographic distance. The algorithm automatically adjusts capacity tolerance to find feasible solutions.

## 🧪 Development

### Development Dependencies

```bash
pip install -r src/requirements-dev.txt
```

### Code Quality

- **Logging**: Structured logging with `structlog` for better observability
- **Type Hints**: Full type annotation support using Python 3.8+ syntax
- **Error Handling**: Comprehensive exception handling with detailed error messages
- **Validation**: Input validation using Pydantic models for all API endpoints
- **Code Organization**: Modular design with clear separation of concerns

### Testing

The application includes comprehensive testing and validation:

- **Jupyter Notebooks**: Located in `notebooks/` directory:
  - `test_api.ipynb`: Interactive API endpoint testing
  - `test_cluster_methods.ipynb`: Testing different clustering algorithms
  - `test_spopt.ipynb`: Spatial optimization algorithm testing
  - `make_pdf.ipynb`: PDF report generation testing
- **Validation Functions**: Department code validation, file path validation, color format validation
- **City Search Testing**: Fuzzy matching algorithms and postal code lookup
- **Map Generation Testing**: Clustering algorithms and color generation
- **API Testing**: Endpoint validation and error handling

## 📝 API Documentation

When running the application, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔮 Future Versions

Version 0.2.1 includes route clustering and optimization with capacitated K-means algorithms. Planned features for future versions include:

- Advanced route optimization algorithms (TSP, genetic algorithms)
- Multi-city campaign planning
- Export functionality for GPS devices (GPX, KML formats)
- Team coordination features
- Performance analytics and route efficiency metrics
- Real-time traffic integration
- Delivery time estimation
- PDF report generation with route visualizations
- Batch processing for multiple cities
- Custom route constraints and preferences

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🤝 Contributing

Contributions are welcome! Please ensure:

- Code follows Python best practices
- Type hints are included
- Error handling is comprehensive
- Documentation is updated

## 📞 Support

For issues, questions, or contributions, please refer to the project repository or contact the development team.
