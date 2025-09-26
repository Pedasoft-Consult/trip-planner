"""
Utility functions for mapping and geographic calculations.
"""
import math
from geopy.distance import geodesic
from typing import List, Tuple, Dict, Optional


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate distance between two points in miles.

    Args:
        point1: (latitude, longitude) tuple
        point2: (latitude, longitude) tuple

    Returns:
        Distance in miles
    """
    return geodesic(point1, point2).miles


def calculate_bearing(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate the initial bearing from point1 to point2.

    Args:
        point1: (latitude, longitude) tuple
        point2: (latitude, longitude) tuple

    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])

    dlon = lon2 - lon1

    y = math.sin(dlon) * math.cos(lat2)
    x = (math.cos(lat1) * math.sin(lat2) -
         math.sin(lat1) * math.cos(lat2) * math.cos(dlon))

    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)

    return (bearing + 360) % 360


def point_along_route(start: Tuple[float, float], end: Tuple[float, float],
                     fraction: float) -> Tuple[float, float]:
    """
    Calculate a point along the route at a given fraction of the total distance.

    Args:
        start: Starting point (lat, lng)
        end: Ending point (lat, lng)
        fraction: Fraction of distance (0.0 to 1.0)

    Returns:
        Point coordinates (lat, lng)
    """
    lat1, lon1 = math.radians(start[0]), math.radians(start[1])
    lat2, lon2 = math.radians(end[0]), math.radians(end[1])

    # Calculate intermediate point
    lat = lat1 + fraction * (lat2 - lat1)
    lon = lon1 + fraction * (lon2 - lon1)

    return (math.degrees(lat), math.degrees(lon))


def bounds_for_points(points: List[Tuple[float, float]], padding: float = 0.01) -> Dict[str, float]:
    """
    Calculate bounding box for a list of points.

    Args:
        points: List of (lat, lng) tuples
        padding: Additional padding around bounds

    Returns:
        Dict with north, south, east, west bounds
    """
    if not points:
        return {'north': 0, 'south': 0, 'east': 0, 'west': 0}

    lats = [point[0] for point in points]
    lngs = [point[1] for point in points]

    return {
        'north': max(lats) + padding,
        'south': min(lats) - padding,
        'east': max(lngs) + padding,
        'west': min(lngs) - padding
    }


def simplify_geometry(coordinates: List[List[float]], tolerance: float = 0.001) -> List[List[float]]:
    """
    Simplify route geometry using Douglas-Peucker algorithm.

    Args:
        coordinates: List of [lng, lat] coordinates
        tolerance: Simplification tolerance

    Returns:
        Simplified coordinates
    """
    if len(coordinates) <= 2:
        return coordinates

    def perpendicular_distance(point, line_start, line_end):
        """Calculate perpendicular distance from point to line."""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        if x1 == x2 and y1 == y2:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

        return abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / \
               math.sqrt((y2 - y1)**2 + (x2 - x1)**2)

    def douglas_peucker(points, epsilon):
        """Recursive Douglas-Peucker implementation."""
        if len(points) <= 2:
            return points

        # Find point with maximum distance
        dmax = 0
        index = 0
        for i in range(1, len(points) - 1):
            d = perpendicular_distance(points[i], points[0], points[-1])
            if d > dmax:
                index = i
                dmax = d

        # If max distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            rec_results1 = douglas_peucker(points[:index + 1], epsilon)
            rec_results2 = douglas_peucker(points[index:], epsilon)

            return rec_results1[:-1] + rec_results2
        else:
            return [points[0], points[-1]]

    return douglas_peucker(coordinates, tolerance)


def calculate_eta(distance_miles: float, average_speed: float = 60) -> float:
    """
    Calculate estimated time of arrival.

    Args:
        distance_miles: Distance in miles
        average_speed: Average speed in mph

    Returns:
        Time in hours
    """
    return distance_miles / average_speed


def format_distance(miles: float) -> str:
    """
    Format distance for display.

    Args:
        miles: Distance in miles

    Returns:
        Formatted string
    """
    if miles < 1:
        feet = miles * 5280
        return f"{feet:.0f} ft"
    elif miles < 10:
        return f"{miles:.1f} mi"
    else:
        return f"{miles:.0f} mi"


def format_duration(hours: float) -> str:
    """
    Format duration for display.

    Args:
        hours: Duration in hours

    Returns:
        Formatted string
    """
    if hours < 1:
        minutes = hours * 60
        return f"{minutes:.0f} min"
    elif hours < 24:
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}h {m}m" if m > 0 else f"{h}h"
    else:
        days = int(hours // 24)
        remaining_hours = int(hours % 24)
        return f"{days}d {remaining_hours}h" if remaining_hours > 0 else f"{days}d"


def is_point_in_bounds(point: Tuple[float, float], bounds: Dict[str, float]) -> bool:
    """
    Check if a point is within given bounds.

    Args:
        point: (lat, lng) tuple
        bounds: Dict with north, south, east, west keys

    Returns:
        True if point is within bounds
    """
    lat, lng = point
    return (bounds['south'] <= lat <= bounds['north'] and
            bounds['west'] <= lng <= bounds['east'])


def get_route_midpoint(coordinates: List[List[float]]) -> Optional[Tuple[float, float]]:
    """
    Get the midpoint of a route based on coordinates.

    Args:
        coordinates: List of [lng, lat] coordinates

    Returns:
        Midpoint (lat, lng) or None if no coordinates
    """
    if not coordinates:
        return None

    mid_index = len(coordinates) // 2
    lng, lat = coordinates[mid_index]
    return (lat, lng)


def calculate_fuel_consumption(distance_miles: float, mpg: float = 6.5) -> float:
    """
    Calculate fuel consumption for a truck.

    Args:
        distance_miles: Distance in miles
        mpg: Miles per gallon (truck average is ~6.5)

    Returns:
        Fuel consumption in gallons
    """
    return distance_miles / mpg


def calculate_fuel_cost(gallons: float, price_per_gallon: float) -> float:
    """
    Calculate total fuel cost.

    Args:
        gallons: Fuel consumption in gallons
        price_per_gallon: Price per gallon

    Returns:
        Total fuel cost
    """
    return gallons * price_per_gallon


def validate_coordinates(lat: float, lng: float) -> bool:
    """
    Validate latitude and longitude coordinates.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        True if coordinates are valid
    """
    return (-90 <= lat <= 90) and (-180 <= lng <= 180)


def haversine_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate the great circle distance between two points using Haversine formula.

    Args:
        point1: (latitude, longitude) tuple
        point2: (latitude, longitude) tuple

    Returns:
        Distance in miles
    """
    lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (math.sin(dlat/2)**2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in miles
    r = 3956

    return c * r
