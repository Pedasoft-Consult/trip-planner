"""
Celery tasks for trip processing.
"""
from celery import shared_task
from django.utils import timezone
from .models import Trip
from .services import TripPlanningService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_trip_async(self, trip_data):
    """
    Asynchronously process trip creation for heavy computations.
    """
    try:
        trip_service = TripPlanningService()
        trip = trip_service.create_trip(trip_data)

        logger.info(f"Successfully processed trip {trip.id} asynchronously")
        return {
            'success': True,
            'trip_id': trip.id,
            'message': 'Trip processed successfully'
        }

    except Exception as e:
        logger.error(f"Error processing trip: {str(e)}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)

        return {
            'success': False,
            'error': str(e),
            'message': 'Trip processing failed after retries'
        }


@shared_task
def update_trip_status():
    """
    Periodic task to update trip statuses based on time.
    """
    now = timezone.now()

    # Update trips that should have started
    planning_trips = Trip.objects.filter(
        status='planning',
        created_at__lt=now - timezone.timedelta(hours=24)
    )

    for trip in planning_trips:
        # Check if trip should auto-start or expire
        first_stop = trip.stops.filter(stop_type='pickup').first()
        if first_stop and first_stop.estimated_departure_time < now:
            trip.status = 'in_progress'
            trip.save()
            logger.info(f"Auto-started trip {trip.id}")

    # Update in-progress trips that should be completed
    in_progress_trips = Trip.objects.filter(status='in_progress')

    for trip in in_progress_trips:
        last_stop = trip.stops.filter(stop_type='dropoff').first()
        if last_stop and last_stop.estimated_departure_time < now:
            trip.status = 'completed'
            trip.save()
            logger.info(f"Auto-completed trip {trip.id}")

    return f"Updated trip statuses at {now}"


@shared_task
def cleanup_old_trips():
    """
    Clean up old completed trips to save storage.
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=90)

    # Delete completed trips older than 90 days
    old_trips = Trip.objects.filter(
        status='completed',
        updated_at__lt=cutoff_date
    )

    count = old_trips.count()
    old_trips.delete()

    logger.info(f"Cleaned up {count} old trips")
    return f"Cleaned up {count} old trips"


@shared_task
def generate_trip_reports():
    """
    Generate daily trip reports and statistics.
    """
    today = timezone.now().date()

    # Calculate daily statistics
    daily_trips = Trip.objects.filter(created_at__date=today)

    stats = {
        'date': today.isoformat(),
        'total_trips': daily_trips.count(),
        'planning_trips': daily_trips.filter(status='planning').count(),
        'in_progress_trips': daily_trips.filter(status='in_progress').count(),
        'completed_trips': daily_trips.filter(status='completed').count(),
        'cancelled_trips': daily_trips.filter(status='cancelled').count(),
        'total_miles': sum(
            float(trip.total_distance_miles or 0)
            for trip in daily_trips
            if trip.total_distance_miles
        ),
        'average_distance': 0,
    }

    if stats['total_trips'] > 0:
        stats['average_distance'] = stats['total_miles'] / stats['total_trips']

    logger.info(f"Generated daily report: {stats}")
    return stats
