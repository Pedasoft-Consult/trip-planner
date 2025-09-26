# ELD Trip Planner - System Overview

## 1. System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  Django Backend │    │   External APIs │
│                 │    │                 │    │                 │
│ • Trip Input    │◄──►│ • Route Logic   │◄──►│ • Mapping API   │
│ • Map Display   │    │ • ELD Calc      │    │ • Geocoding     │
│ • Log Sheets    │    │ • Data Models   │    │ • Routing       │
│ • UI/UX         │    │ • REST API      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Frontend**: React 18+ with TypeScript
- **Backend**: Django 4+ with Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Mapping**: MapBox API (free tier)
- **Deployment**: Vercel (frontend) + Railway/Heroku (backend)
- **Styling**: Tailwind CSS + shadcn/ui components

## 2. Core Components

### 2.1 Frontend (React)
- **Trip Input Form**: Collects current location, pickup, dropoff, current cycle hours
- **Interactive Map**: Displays route, stops, rest areas using MapBox
- **ELD Log Generator**: Renders digital daily log sheets
- **Route Summary**: Shows trip details, driving time, rest requirements

### 2.2 Backend (Django)
- **Trip Planning Service**: Calculates optimal routes and stops
- **ELD Compliance Engine**: Enforces Hours of Service (HOS) regulations
- **Route Optimization**: Determines fuel stops and mandatory rest periods
- **Log Sheet Generator**: Creates compliant daily log entries

### 2.3 External Integrations
- **MapBox API**: Route calculation, geocoding, map rendering
- **Fuel Stop API**: Locates truck stops along route
- **Weather API**: Basic weather info for trip planning

## 3. Data Models

### Trip Model
```python
class Trip(models.Model):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_hours = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class RouteSegment(models.Model):
    trip = models.ForeignKey(Trip)
    start_point = models.JSONField()  # lat, lng
    end_point = models.JSONField()    # lat, lng
    distance_miles = models.FloatField()
    estimated_time_hours = models.FloatField()
    
class ELDLogEntry(models.Model):
    trip = models.ForeignKey(Trip)
    date = models.DateField()
    driver_name = models.CharField(max_length=100)
    duty_status = models.CharField(max_length=20)  # ON, OFF, D, SB
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255)
```

## 4. Business Logic

### 4.1 Hours of Service (HOS) Rules Implementation
- **Property-carrying drivers**: 70 hours in 8 consecutive days
- **Daily driving limit**: 11 hours maximum
- **On-duty limit**: 14 hours maximum
- **Required rest**: 10 consecutive hours off duty
- **34-hour restart**: Reset weekly cycle

### 4.2 Route Calculation Algorithm
```
1. Geocode all locations (current, pickup, dropoff)
2. Calculate base route using MapBox Directions API
3. Determine total driving time and distance
4. Calculate mandatory rest stops based on HOS rules
5. Insert fuel stops every 1000 miles maximum
6. Add 1-hour buffers for pickup/dropoff
7. Generate compliant ELD log entries
8. Return optimized route with all stops
```

### 4.3 ELD Log Generation Logic
- Creates daily log sheets for multi-day trips
- Automatically fills duty status changes
- Includes location information for each status change
- Ensures compliance with FMCSA regulations
- Generates printable/digital log formats

## 5. API Endpoints

### RESTful API Design
```
POST /api/trips/                    # Create new trip
GET  /api/trips/{id}/              # Get trip details
GET  /api/trips/{id}/route/        # Get route information
GET  /api/trips/{id}/logs/         # Get ELD log sheets
POST /api/geocode/                 # Geocode address
GET  /api/fuel-stops/              # Find fuel stops along route
```

## 6. User Interface Flow

### 6.1 Input Phase
1. User enters current location
2. User enters pickup location  
3. User enters dropoff location
4. User enters current cycle hours used
5. System validates inputs and geocodes locations

### 6.2 Processing Phase
1. System calculates optimal route
2. Determines required rest stops
3. Identifies fuel stop locations
4. Generates ELD log entries
5. Prepares map visualization

### 6.3 Output Phase
1. Interactive map shows complete route
2. Route summary displays key information
3. Digital ELD logs are rendered
4. User can download/print logs
5. Trip details are saved for reference

## 7. Compliance Features

### FMCSA Regulation Compliance
- Accurate Hours of Service calculations
- Proper duty status classifications
- Required rest period enforcement
- Location tracking for log entries
- 34-hour restart provisions

### ELD Log Requirements
- Driver identification
- Date and time stamps
- Duty status (ON, OFF, D, SB)
- Location information
- Odometer readings
- Vehicle information

## 8. Performance Considerations

### Frontend Optimization
- Lazy loading for map components
- Efficient state management with Context API
- Optimized re-renders for map updates
- Progressive Web App (PWA) capabilities

### Backend Optimization
- Database query optimization
- API response caching
- Asynchronous processing for route calculations
- Rate limiting for external API calls

## 9. Security & Privacy

### Data Protection
- No persistent storage of personal information
- Secure API communication (HTTPS)
- Input validation and sanitization
- CORS configuration for API access

### Privacy Considerations
- Minimal data collection
- No location tracking beyond trip planning
- Clear data usage policies
- Option to clear trip history

## 10. Testing Strategy

### Frontend Testing
- Unit tests for components (Jest/React Testing Library)
- Integration tests for user flows
- E2E tests for critical paths (Cypress)

### Backend Testing
- Unit tests for business logic
- API endpoint testing
- HOS compliance validation tests
- Route calculation accuracy tests

## 11. Deployment Architecture

### Production Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Vercel      │    │   Railway/      │    │   PostgreSQL    │
│                 │    │   Heroku        │    │   Database      │
│ • React Build   │◄──►│ • Django API    │◄──►│ • Trip Data     │
│ • Static Assets │    │ • Background    │    │ • Log Entries   │
│ • CDN           │    │   Tasks         │    │ • Cache         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### CI/CD Pipeline
- GitHub Actions for automated testing
- Automated deployment on merge to main
- Environment-specific configurations
- Database migration automation

This system provides a comprehensive solution for truck drivers to plan compliant trips while maintaining accurate ELD logs according to federal regulations.