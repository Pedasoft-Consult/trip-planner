"""
Views for the routes app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import RouteTemplate, RestArea, RouteAlert
from .serializers import RouteTemplateSerializer, RestAreaSerializer, RouteAlertSerializer
from mapping.services import calculate_route_service, get_weather_info
import logging

logger = logging.getLogger(__name__)


class RouteTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route templates.
    """
    queryset = RouteTemplate.objects.filter(is_active=True)
    serializer_class = RouteTemplateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by start/end locations if provided
        start_location = self.request.query_params.get('start_location')
        end_location = self.request.query_params.get('end_location')

        if start_location:
            queryset = queryset.filter(start_location__address__icontains=start_location)
        if end_location:
            queryset = queryset.filter(end_location__address__icontains=end_location)

        return queryset.order_by('-times_used', 'name')


class RestAreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing rest areas.
    """
    queryset = RestArea.objects.filter(is_active=True)
    serializer_class = RestAreaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by amenities if provided
        amenities = self.request.query_params.get('amenities')
        if amenities:
            amenity_list = amenities.split(',')
            for amenity in amenity_list:
                queryset = queryset.filter(amenities__contains=amenity.strip())

        # Filter by location if provided
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(location__state__iexact=state)

        return queryset.order_by('name')


class RouteAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route alerts.
    """
    queryset = RouteAlert.objects.filter(is_active=True)
    serializer_class = RouteAlertSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by alert type if provided
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        # Filter by severity if provided
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset.order_by('-start_time', '-severity')


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_route(request):
    """
    Calculate route between waypoints.
    """
    try:
        data = request.data
        waypoints = data.get('waypoints', [])

        if not waypoints or len(waypoints) < 2:
            return Response(
                {'error': 'At least 2 waypoints are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert waypoints to proper format
        waypoint_coords = []
        for waypoint in waypoints:
            if isinstance(waypoint, dict):
                lat = waypoint.get('latitude') or waypoint.get('lat')
                lng = waypoint.get('longitude') or waypoint.get('lng')
            elif isinstance(waypoint, (list, tuple)) and len(waypoint) >= 2:
                lat, lng = waypoint[0], waypoint[1]
            else:
                return Response(
                    {'error': 'Invalid waypoint format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            waypoint_coords.append((lat, lng))

        # Calculate route
        route_data = calculate_route_service(waypoint_coords)

        if route_data:
            return Response(route_data)
        else:
            return Response(
                {'error': 'Could not calculate route'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error calculating route: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def optimize_route(request):
    """
    Optimize route with multiple stops.
    """
    try:
        data = request.data
        stops = data.get('stops', [])

        if len(stops) < 3:
            return Response(
                {'error': 'At least 3 stops are required for optimization'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simple optimization - this is a placeholder
        # In production, you would use proper route optimization algorithms
        optimized_stops = stops.copy()  # Placeholder - no actual optimization

        return Response({
            'original_stops': stops,
            'optimized_stops': optimized_stops,
            'optimization_message': 'Route optimization not implemented yet'
        })

    except Exception as e:
        logger.error(f"Error optimizing route: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_traffic_data(request):
    """
    Get traffic data for a location or route.
    """
    try:
        latitude = request.query_params.get('lat')
        longitude = request.query_params.get('lng')

        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # This is a placeholder - in production you would integrate with
        # traffic APIs like Google Traffic, MapBox Traffic, etc.
        traffic_data = {
            'latitude': float(latitude),
            'longitude': float(longitude),
            'traffic_status': 'moderate',
            'average_speed': 45,  # mph
            'congestion_level': 'medium',
            'message': 'Traffic data not implemented yet'
        }

        return Response(traffic_data)

    except ValueError:
        return Response(
            {'error': 'Invalid coordinate format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting traffic data: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_restrictions(request):
    """
    Check for truck restrictions along a route.
    """
    try:
        waypoints = request.query_params.get('waypoints', '')

        if not waypoints:
            return Response(
                {'error': 'Waypoints parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # This is a placeholder - in production you would check against
        # truck restriction databases and APIs
        restrictions = {
            'height_restrictions': [],
            'weight_restrictions': [],
            'hazmat_restrictions': [],
            'bridge_restrictions': [],
            'tunnel_restrictions': [],
            'message': 'Truck restrictions checking not implemented yet'
        }

        return Response(restrictions)

    except Exception as e:
        logger.error(f"Error checking restrictions: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
