"""
Train Departure API - Flask Backend
====================================
This API fetches real-time train departures from Trafiklab (SL) and serves
them in a simplified format for the ESP32 to display on LED matrices.

NETWORKING CONCEPTS:
- REST API: Uses HTTP methods (GET) to expose resources
- JSON: Lightweight data format for API communication
- Caching: Reduces external API calls (saves quota and improves speed)

SECURITY CONCEPTS:
- API keys stored in environment variables (never hardcoded)
- Rate limiting to prevent abuse
- CORS enabled for cross-origin requests (ESP32 will call from different origin)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta
from functools import wraps
import time
import pytz  # For timezone handling

app = Flask(__name__)

# SECURITY: Enable CORS - allows ESP32 to call this API from a different domain
# In production, you'd restrict this to specific origins
CORS(app)

# CONFIGURATION: Load from environment variables (Docker will provide these)
TRAFIKLAB_API_KEY = os.environ.get('TRAFIKLAB_API_KEY', '')
TRAFIKLAB_API_URL = 'https://realtime-api.trafiklab.se/v1/departures'
DEFAULT_SITE_ID = os.environ.get('DEFAULT_SITE_ID', '740000701')  # Helenelund (6-digit format)

# DYNAMIC CACHE TTL: Different cache times based on time of day
# Night hours (less frequent trains) = longer cache
# Day hours (frequent trains) = shorter cache for fresher data
CACHE_TTL_NIGHT = int(os.environ.get('CACHE_TTL_NIGHT', '600'))  # 10 minutes (00:00-06:59)
CACHE_TTL_DAY = int(os.environ.get('CACHE_TTL_DAY', '120'))      # 2 minutes (07:00-23:59)
NIGHT_START_HOUR = 0   # Midnight
NIGHT_END_HOUR = 7     # 7 AM

# TIMEZONE: Sweden uses Europe/Stockholm timezone
STOCKHOLM_TZ = pytz.timezone('Europe/Stockholm')

# CACHING: Store fetched data temporarily to reduce API calls
cache = {
    'data': None,
    'timestamp': None,
    'ttl': CACHE_TTL_DAY  # Initial TTL (will be dynamic)
}


def get_current_ttl():
    """
    Get appropriate cache TTL based on current time
    
    OPTIMIZATION CONCEPT: Dynamic TTL based on time of day
    - Night (00:00-06:59): Longer cache (10 min) - trains less frequent
    - Day (07:00-23:59): Shorter cache (2 min) - want fresh data
    
    Returns:
        int: TTL in seconds
    """
    now = datetime.now(STOCKHOLM_TZ)
    current_hour = now.hour
    
    if NIGHT_START_HOUR <= current_hour < NIGHT_END_HOUR:
        return CACHE_TTL_NIGHT
    else:
        return CACHE_TTL_DAY

def rate_limit(max_calls=60, period=60):
    """
    SECURITY: Simple rate limiting decorator
    Prevents abuse by limiting requests per time period
    
    CONCEPT: This is a decorator - a function that wraps another function
    """
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls older than the period
            calls[:] = [call for call in calls if call > now - period]
            
            if len(calls) >= max_calls:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_calls} requests per {period} seconds'
                }), 429
            
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def is_cache_valid():
    """
    CACHING CONCEPT: Check if cached data is still fresh
    Uses dynamic TTL based on time of day
    Returns True if cache exists and hasn't expired
    """
    if cache['data'] is None or cache['timestamp'] is None:
        return False
    
    # Get appropriate TTL for current time
    current_ttl = get_current_ttl()
    
    age = (datetime.now(STOCKHOLM_TZ) - cache['timestamp']).total_seconds()
    is_valid = age < current_ttl
    
    if not is_valid:
        now = datetime.now(STOCKHOLM_TZ)
        period = "night" if NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR else "day"
        print(f"[CACHE EXPIRED] Age: {age:.1f}s, TTL: {current_ttl}s (period: {period})")
    
    return is_valid


def fetch_train_data(site_id, time_window=60):
    """
    Fetch real-time departures from Trafiklab API (v1)
    
    NETWORKING: Makes HTTP GET request to external API
    CACHING: Returns cached data if still valid
    
    Args:
        site_id: Station ID (e.g., 740000701 for Helenelund) - 6 digit format
        time_window: Minutes to look ahead (default 60)
    """
    # Return cached data if still valid
    if is_cache_valid():
        age = (datetime.now(STOCKHOLM_TZ) - cache['timestamp']).total_seconds()
        current_ttl = get_current_ttl()
        now = datetime.now(STOCKHOLM_TZ)
        period = "night" if NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR else "day"
        print(f"[CACHE HIT] Returning cached data (age: {age:.1f}s / {current_ttl}s, period: {period})")
        return cache['data']
    
    print(f"[CACHE MISS] Fetching fresh data from Trafiklab API")
    
    # NETWORKING: Build request URL - matches Trafiklab specs exactly
    url = f"{TRAFIKLAB_API_URL}/{site_id}"
    
    # NETWORKING: Add API key as query parameter (only required param)
    params = {
        'key': TRAFIKLAB_API_KEY
    }
    
    try:
        # NETWORKING: HTTP GET request with timeout (prevents hanging)
        print(f"[DEBUG] Requesting: {url}")
        print(f"[DEBUG] API Key present: {'Yes' if TRAFIKLAB_API_KEY else 'No'}")
        print(f"[DEBUG] API Key first 10 chars: {TRAFIKLAB_API_KEY[:10] if TRAFIKLAB_API_KEY else 'NONE'}...")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Full URL: {response.url}")
        
        # NETWORKING: Check HTTP status code
        if response.status_code == 200:
            data = response.json()
            print(f"[SUCCESS] Received {len(data.get('departures', []))} departures")
            
            # Update cache
            cache['data'] = data
            cache['timestamp'] = datetime.now(STOCKHOLM_TZ)
            
            return data
        elif response.status_code == 401:
            print(f"[ERROR] Unauthorized - Check your API key")
            print(f"[ERROR] Response: {response.text}")
            return None
        elif response.status_code == 400:
            print(f"[ERROR] Bad Request - Invalid parameters")
            print(f"[ERROR] Response: {response.text}")
            return None
        elif response.status_code == 404:
            print(f"[ERROR] Site ID {site_id} not found")
            print(f"[ERROR] Response: {response.text}")
            return None
        else:
            print(f"[ERROR] Trafiklab API returned status {response.status_code}")
            print(f"[ERROR] Response: {response.text[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        print("[ERROR] Request to Trafiklab timed out")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def format_for_esp32(raw_data):
    """
    Transform Trafiklab JSON into simplified format for ESP32
    
    WHY: ESP32 has limited memory - we send only essential data
    CONCEPT: Data transformation/filtering layer
    
    Actual API v1 structure from Trafiklab:
    {
        "departures": [
            {
                "scheduled": "2025-10-17T18:28:00",
                "realtime": "2025-10-17T18:28:00",
                "delay": 0,
                "canceled": false,
                "route": {
                    "designation": "41",
                    "transport_mode": "TRAIN",
                    "direction": "Märsta"
                },
                "is_realtime": true
            }
        ]
    }
    """
    if not raw_data or 'departures' not in raw_data:
        print("[ERROR] No departures found in API response")
        return []
    
    departures = []
    
    # Process all departures from new API
    for dep in raw_data.get('departures', [])[:10]:  # Limit to 10
        route = dep.get('route', {})
        
        # Calculate display time from realtime or scheduled
        realtime_str = dep.get('realtime', '')
        scheduled_str = dep.get('scheduled', '')
        delay = dep.get('delay', 0)
        
        # Use realtime if available, otherwise scheduled
        departure_time = realtime_str if realtime_str else scheduled_str
        
        # Calculate minutes until departure
        display_time = '?'
        if departure_time:
            try:
                # Parse the ISO datetime string
                # Trafiklab returns times in Swedish local time (no timezone suffix)
                # Example: "2025-10-17T18:28:00"
                departure_dt = datetime.fromisoformat(departure_time)
                
                # If no timezone info, assume it's already in Swedish time
                if departure_dt.tzinfo is None:
                    departure_dt = STOCKHOLM_TZ.localize(departure_dt)
                
                # Get current time in Stockholm timezone
                now = datetime.now(STOCKHOLM_TZ)
                
                # Calculate difference
                time_diff = (departure_dt - now).total_seconds()
                minutes_until = int(time_diff / 60)
                
                print(f"[DEBUG] Departure: {departure_dt}, Now: {now}, Diff: {minutes_until} min")
                
                if minutes_until <= 0:
                    display_time = 'Nu'
                elif minutes_until < 60:
                    display_time = f'{minutes_until} min'
                else:
                    # Show time instead of minutes for far future (>60 min)
                    display_time = departure_dt.strftime('%H:%M')
            except Exception as e:
                print(f"[ERROR] Failed to parse time '{departure_time}': {e}")
                display_time = '?'
        
        departures.append({
            'type': route.get('transport_mode', 'Unknown').title(),
            'line': route.get('designation', '?'),
            'destination': route.get('direction', 'Unknown'),
            'display_time': display_time,
            'scheduled': scheduled_str,
            'realtime': realtime_str,
            'delay': delay,
            'canceled': dep.get('canceled', False),
            'is_realtime': dep.get('is_realtime', False)
        })
    
    return departures


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/')
def home():
    """
    Health check endpoint
    CONCEPT: Always have a simple endpoint to verify service is running
    """
    return jsonify({
        'service': 'Train Departure API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            '/': 'Service information (this page)',
            '/health': 'Health check for container orchestration',
            '/departures': 'Get all departures from default station',
            '/departures?site_id=<id>': 'Get departures for specific station via query parameter',
            '/departures/<site_id>': 'Get departures for specific station via path parameter',
            '/departures/northbound': 'Get only northbound trains from default station',
            '/departures/southbound': 'Get only southbound trains from default station',
            '/departures/<site_id>/northbound': 'Get northbound trains from specific station',
            '/departures/<site_id>/southbound': 'Get southbound trains from specific station',
            '/cache/status': 'View cache status and TTL configuration (GET)',
            '/cache/clear': 'Clear cached data (POST request)'
        },
        'examples': {
            'all_departures': '/departures',
            'specific_station': '/departures/740000701',
            'northbound_only': '/departures/northbound',
            'southbound_only': '/departures/southbound',
            'station_northbound': '/departures/740000701/northbound',
            'cache_info': '/cache/status'
        }
    })


@app.route('/health')
def health():
    """
    DOCKER CONCEPT: Health check endpoint for container orchestration
    Kubernetes/Docker Swarm can use this to verify container is healthy
    """
    return jsonify({'status': 'healthy'}), 200


@app.route('/departures', methods=['GET'])
@rate_limit(max_calls=30, period=60)
def get_departures():
    """
    Get departures for default station
    
    NETWORKING: This is a REST API endpoint
    - URL: /departures
    - Method: GET
    - Returns: JSON array of departures
    """
    site_id = request.args.get('site_id', DEFAULT_SITE_ID)
    
    raw_data = fetch_train_data(site_id)
    
    if raw_data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    formatted = format_for_esp32(raw_data)
    
    # Get stop point name from API response - multiple stops can be returned
    stops = raw_data.get('stops', [])
    station_name = stops[0].get('name', 'Unknown') if stops else 'Unknown'
    
    return jsonify({
        'site_id': site_id,
        'station_name': station_name,
        'updated_at': datetime.now(STOCKHOLM_TZ).isoformat(),
        'total_departures': len(formatted),
        'departures': formatted
    })


@app.route('/departures/<site_id>', methods=['GET'])
@rate_limit(max_calls=30, period=60)
def get_departures_by_site(site_id):
    """
    Get departures for a specific station
    
    REST CONCEPT: URL parameter (/departures/740000701)
    This is called a "path parameter" or "URL parameter"
    """
    raw_data = fetch_train_data(site_id)
    
    if raw_data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    formatted = format_for_esp32(raw_data)
    
    # Get stop point name from API response - multiple stops can be returned
    stops = raw_data.get('stops', [])
    station_name = stops[0].get('name', 'Unknown') if stops else 'Unknown'
    
    return jsonify({
        'site_id': site_id,
        'station_name': station_name,
        'updated_at': datetime.now(STOCKHOLM_TZ).isoformat(),
        'total_departures': len(formatted),
        'departures': formatted
    })


@app.route('/departures/northbound', methods=['GET'])
@app.route('/departures/<site_id>/northbound', methods=['GET'])
@rate_limit(max_calls=30, period=60)
def get_northbound_departures(site_id=None):
    """
    Get only northbound departures (trains/buses heading north)
    
    REST CONCEPT: Resource filtering via URL path
    Example: /departures/northbound or /departures/740000701/northbound
    
    FILTERING LOGIC: Filters destinations typically north of Stockholm
    Common northbound destinations: Märsta, Uppsala, Upplands Väsby, Kungsängen
    """
    if site_id is None:
        site_id = DEFAULT_SITE_ID
    
    raw_data = fetch_train_data(site_id)
    
    if raw_data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    # Get all formatted departures
    all_departures = format_for_esp32(raw_data)
    
    # Define northbound destination keywords (case-insensitive)
    northbound_keywords = [
        'märsta', 'uppsala', 'upplands väsby', 'väsby', 
        'kungsängen', 'bålsta', 'arlanda', 'knivsta'
    ]
    
    # Filter for northbound trains only
    northbound = [
        dep for dep in all_departures 
        if any(keyword in dep['destination'].lower() for keyword in northbound_keywords)
    ]
    
    stops = raw_data.get('stops', [])
    station_name = stops[0].get('name', 'Unknown') if stops else 'Unknown'
    
    return jsonify({
        'site_id': site_id,
        'station_name': station_name,
        'direction': 'northbound',
        'updated_at': datetime.now(STOCKHOLM_TZ).isoformat(),
        'total_departures': len(northbound),
        'departures': northbound
    })


@app.route('/departures/southbound', methods=['GET'])
@app.route('/departures/<site_id>/southbound', methods=['GET'])
@rate_limit(max_calls=30, period=60)
def get_southbound_departures(site_id=None):
    """
    Get only southbound departures (trains/buses heading south)
    
    REST CONCEPT: Resource filtering via URL path
    Example: /departures/southbound or /departures/740000701/southbound
    
    FILTERING LOGIC: Filters destinations typically south of Stockholm
    Common southbound destinations: Stockholm, Södertälje, Tumba, City
    """
    if site_id is None:
        site_id = DEFAULT_SITE_ID
    
    raw_data = fetch_train_data(site_id)
    
    if raw_data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    # Get all formatted departures
    all_departures = format_for_esp32(raw_data)
    
    # Define southbound destination keywords (case-insensitive)
    southbound_keywords = [
        'stockholm', 'södertälje', 'tumba', 'city', 'centralen',
        't-centralen', 'huddinge', 'flemingsberg', 'älvsjö'
    ]
    
    # Filter for southbound trains only
    southbound = [
        dep for dep in all_departures 
        if any(keyword in dep['destination'].lower() for keyword in southbound_keywords)
    ]
    
    stops = raw_data.get('stops', [])
    station_name = stops[0].get('name', 'Unknown') if stops else 'Unknown'
    
    return jsonify({
        'site_id': site_id,
        'station_name': station_name,
        'direction': 'southbound',
        'updated_at': datetime.now(STOCKHOLM_TZ).isoformat(),
        'total_departures': len(southbound),
        'departures': southbound
    })


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    Manually clear the cache
    USEFUL: For testing or forcing fresh data fetch
    """
    cache['data'] = None
    cache['timestamp'] = None
    return jsonify({'message': 'Cache cleared'}), 200


@app.route('/cache/status', methods=['GET'])
def cache_status():
    """
    Get current cache status and configuration
    USEFUL: Debug endpoint to see cache state and TTL settings
    """
    now = datetime.now(STOCKHOLM_TZ)
    current_ttl = get_current_ttl()
    current_hour = now.hour
    period = "night" if NIGHT_START_HOUR <= current_hour < NIGHT_END_HOUR else "day"
    
    if cache['timestamp']:
        age = (now - cache['timestamp']).total_seconds()
        cache_info = {
            'cached': True,
            'age_seconds': round(age, 1),
            'valid': is_cache_valid(),
            'expires_in_seconds': round(max(0, current_ttl - age), 1)
        }
    else:
        cache_info = {
            'cached': False,
            'age_seconds': None,
            'valid': False,
            'expires_in_seconds': None
        }
    
    return jsonify({
        'current_time': now.isoformat(),
        'current_hour': current_hour,
        'period': period,
        'ttl_configuration': {
            'night_hours': f'{NIGHT_START_HOUR:02d}:00-{NIGHT_END_HOUR:02d}:00',
            'night_ttl_seconds': CACHE_TTL_NIGHT,
            'night_ttl_minutes': CACHE_TTL_NIGHT / 60,
            'day_hours': f'{NIGHT_END_HOUR:02d}:00-23:59',
            'day_ttl_seconds': CACHE_TTL_DAY,
            'day_ttl_minutes': CACHE_TTL_DAY / 60
        },
        'active_ttl_seconds': current_ttl,
        'active_ttl_minutes': current_ttl / 60,
        'cache': cache_info
    })


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    # SECURITY: Check if API key is configured
    if not TRAFIKLAB_API_KEY:
        print("WARNING: TRAFIKLAB_API_KEY not set!")
        print("Set it via environment variable: export TRAFIKLAB_API_KEY=your_key")
    
    # DOCKER CONCEPT: Listen on 0.0.0.0 to accept connections from outside container
    # Port 5000 is standard for Flask
    # debug=True provides helpful error messages (disable in production!)
    app.run(host='0.0.0.0', port=5000, debug=True)