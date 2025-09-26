"""
External mapping and geocoding services.
"""
import requests
from django.conf import settings
from geopy.geocoders import Nominatim
import logging

logger = logging.getLogger(__name__)


def geocode_address_service(address):
    """
    Geocode an address using MapBox Geocoding API with fallback to Nominatim.
    """
    try:
        # Try MapBox first if API key is available
        if settings.MAPBOX_API_KEY:
            return _geocode_with_mapbox(address)
        else:
            return _geocode_with_nominatim(address)
    except Exception as e:
        logger.error(f"Error geocoding address '{address}': {str(e)}")
        return None


def _geocode_with_mapbox(address):
    """
    Geocode address using MapBox Geocoding API.
    """
    url = "https://api.mapbox.com/geocoding/v5/mapbox.places/{}.json".format(
        requests.utils.quote(address)
    )

    params = {
        'access_token': settings.MAPBOX_API_KEY,
        'country': 'US',
        'types': 'address,poi',
        'limit': 1
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if data['features']:
        feature = data['features'][0]
        coordinates = feature['geometry']['coordinates']
        properties = feature.get('properties', {})
        context = feature.get('context', [])

        # Extract location components
        city = _extract_context_value(context, 'place')
        state = _extract_context_value(context, 'region')
        postal_code = _extract_context_value(context, 'postcode')

        return {
            'address': feature['place_name'],
            'latitude': coordinates[1],
            'longitude': coordinates[0],
            'city': city or '',
            'state': state or '',
            'country': 'USA',
            'postal_code': postal_code or ''
        }

    return None


def _extract_context_value(context, context_type):
    """
    Extract value from MapBox context array.
    """
    for item in context:
        if item.get('id', '').startswith(context_type):
            return item.get('text', '')
    return None


def _geocode_with_nominatim(address):
    """
    Fallback geocoding using Nominatim (OpenStreetMap).
    """
    geolocator = Nominatim(user_agent="eld_trip_planner")
    location = geolocator.geocode(f"{address}, USA", timeout=10)

    if location:
        return {
            'address': location.address,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'city': '',
            'state': '',
            'country': 'USA',
            'postal_code': ''
        }

    return None


def calculate_route_service(waypoints):
    """
    Calculate route between waypoints using MapBox Directions API.

    Args:
        waypoints: List of (lat, lng) tuples

    Returns:
        Dict with route information including distance, time, and geometry
    """
    try:
        if settings.MAPBOX_API_KEY:
            return _calculate_route_mapbox(waypoints)
        else:
            return _calculate_route_fallback(waypoints)
    except Exception as e:
        logger.error(f"Error calculating route: {str(e)}")
        return None


def _calculate_route_mapbox(waypoints):
    """
    Calculate route using MapBox Directions API.
    """
    # Convert waypoints to MapBox format
    coordinates = ";".join([f"{lng},{lat}" for lat, lng in waypoints])

    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}"

    params = {
        'access_token': settings.MAPBOX_API_KEY,
        'geometries': 'geojson',
        'overview': 'full',
        'steps': 'true',
        'annotations': 'distance,duration'
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if data['routes']:
        route = data['routes'][0]

        # Extract segments from legs
        segments = []
        for i, leg in enumerate(route['legs']):
            segments.append({
                'distance': leg['distance'] * 0.000621371,  # meters to miles
                'time': leg['duration'] / 3600,  # seconds to hours
                'geometry': leg.get('geometry')
            })

        return {
            'total_distance': route['distance'] * 0.000621371,  # meters to miles
            'total_time': route['duration'] / 3600,  # seconds to hours
            'geometry': route['geometry'],
            'segments': segments
        }

    return None


def _calculate_route_fallback(waypoints):
    """
    Fallback route calculation using simple distance calculation.
    """
    from geopy.distance import geodesic

    total_distance = 0
    segments = []

    for i in range(len(waypoints) - 1):
        start = waypoints[i]
        end = waypoints[i + 1]

        distance_miles = geodesic(start, end).miles
        time_hours = distance_miles / 60  # Assume 60 mph average

        total_distance += distance_miles

        segments.append({
            'distance': distance_miles,
            'time': time_hours,
            'geometry': None
        })

    return {
        'total_distance': total_distance,
        'total_time': total_distance / 60,  # Assume 60 mph average
        'geometry': None,
        'segments': segments
    }


def find_fuel_stops_service(route_geometry, interval_miles=1000):
    """
    Find fuel stops along a route at specified intervals.

    This is a simplified implementation. In production, you would use
    a real truck stop API like TruckStop.com or similar services.
    """
    fuel_stops = []

    try:
        # This is a placeholder implementation
        # In production, you would:
        # 1. Use the route geometry to find points along the route
        # 2. Query truck stop APIs for fuel stations near those points
        # 3. Return detailed fuel stop information

        # For now, return dummy fuel stops
        if route_geometry:
            # Simplified: create fuel stops at regular intervals
            coordinates = route_geometry.get('coordinates', [])

            if coordinates and len(coordinates) > 2:
                # Create fuel stops at 1/3 and 2/3 of the route
                third = len(coordinates) // 3
                two_thirds = (len(coordinates) * 2) // 3

                fuel_stops.append({
                    'name': 'Flying J Travel Center',
                    'brand': 'Flying J',
                    'latitude': coordinates[third][1],
                    'longitude': coordinates[third][0],
                    'diesel_price': 3.45,
                    'amenities': ['parking', 'restrooms', 'food', 'showers']
                })

                fuel_stops.append({
                    'name': 'Love\'s Travel Stop',
                    'brand': 'Love\'s',
                    'latitude': coordinates[two_thirds][1],
                    'longitude': coordinates[two_thirds][0],
                    'diesel_price': 3.52,
                    'amenities': ['parking', 'restrooms', 'food']
                })

    except Exception as e:
        logger.error(f"Error finding fuel stops: {str(e)}")

    return fuel_stops


def get_weather_info(latitude, longitude):
    """
    Get weather information for a location using OpenWeatherMap API.
    """
    try:
        if not settings.OPENWEATHER_API_KEY:
            return None

        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': settings.OPENWEATHER_API_KEY,
            'units': 'imperial'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        return {
            'temperature': data['main']['temp'],
            'description': data['weather'][0]['description'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed'],
            'visibility': data.get('visibility', 0) / 1609.34  # meters to miles
        }

    except Exception as e:
        logger.error(f"Error getting weather info: {str(e)}")
        return None
