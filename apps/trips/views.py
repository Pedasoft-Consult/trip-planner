"""
Views for the trips app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from .models import Trip, RouteSegment, Stop, FuelStop
from .serializers import (
    TripSerializer, TripCreateSerializer, TripSummarySerializer,
    RouteSegmentSerializer, StopSerializer
)
from .services import TripPlanningService
from apps.core.models import Location, Driver, Vehicle
import logging

logger = logging.getLogger(__name__)


class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trips.
    """
    queryset = Trip.objects.all().select_related(
        'driver', 'vehicle', 'current_location',
        'pickup_location', 'dropoff_location'
    ).prefetch_related('route_segments', 'stops')

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        elif self.action == 'list':
            return TripSummarySerializer
        return TripSerializer

    @transaction.atomic
    def create(self, request):
        """
        Create a new trip with route planning and ELD compliance.
        """
        serializer = TripCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Use the trip planning service to create the complete trip
                trip_service = TripPlanningService()
                trip = trip_service.create_trip(serializer.validated_data)

                # Return the complete trip data
                response_serializer = TripSerializer(trip)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                logger.error(f"Error creating trip: {str(e)}")
                return Response(
                    {'error': f'Failed to create trip: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def route(self, request, pk=None):
        """
        Get detailed route information for a trip.
        """
        trip = self.get_object()
        segments = trip.route_segments.all()
        serializer = RouteSegmentSerializer(segments, many=True)

        return Response({
            'trip_id': trip.id,
            'total_distance': trip.total_distance_miles,
            'estimated_duration': trip.estimated_duration_hours,
            'segments': serializer.data
        })

    @action(detail=True, methods=['get'])
    def stops(self, request, pk=None):
        """
        Get all stops for a trip.
        """
        trip = self.get_object()
        stops = trip.stops.all().select_related('location')
        serializer = StopSerializer(stops, many=True)

        return Response({
            'trip_id': trip.id,
            'stops': serializer.data
        })

    @action(detail=True, methods=['get'])
    def eld_logs(self, request, pk=None):
        """
        Generate ELD log sheets for the trip.
        """
        trip = self.get_object()

        # Import here to avoid circular imports
        from apps.eld.services import ELDLogService

        eld_service = ELDLogService()
        logs = eld_service.generate_logs_for_trip(trip)

        return Response({
            'trip_id': trip.id,
            'logs': logs
        })

    @action(detail=True, methods=['post'])
    def start_trip(self, request, pk=None):
        """
        Start a planned trip.
        """
        trip = self.get_object()

        if trip.status != 'planning':
            return Response(
                {'error': 'Trip must be in planning status to start'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip.status = 'in_progress'
        trip.save()

        return Response(
            {'message': 'Trip started successfully', 'status': trip.status}
        )

    @action(detail=True, methods=['post'])
    def complete_trip(self, request, pk=None):
        """
        Mark a trip as completed.
        """
        trip = self.get_object()

        if trip.status != 'in_progress':
            return Response(
                {'error': 'Trip must be in progress to complete'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip.status = 'completed'
        trip.save()

        return Response(
            {'message': 'Trip completed successfully', 'status': trip.status}
        )

    @action(detail=True, methods=['post'])
    def cancel_trip(self, request, pk=None):
        """
        Cancel a trip.
        """
        trip = self.get_object()

        if trip.status == 'completed':
            return Response(
                {'error': 'Cannot cancel a completed trip'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip.status = 'cancelled'
        trip.save()

        return Response(
            {'message': 'Trip cancelled successfully', 'status': trip.status}
        )
