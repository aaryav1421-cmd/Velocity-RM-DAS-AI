from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import json
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class RoomType(str, Enum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    SUITE = "suite"
    PRESIDENTIAL = "presidential"

class BookingChannel(str, Enum):
    DIRECT = "direct"
    BOOKING_COM = "booking.com"
    EXPEDIA = "expedia"
    AIRBNB = "airbnb"
    WALK_IN = "walk-in"

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"

# Data Models
class Hotel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: str
    total_rooms: int
    room_types: Dict[str, int]  # room_type -> count
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hotel_id: str
    room_number: str
    room_type: RoomType
    base_rate: float
    is_available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hotel_id: str
    room_id: str
    guest_name: str
    guest_email: str
    check_in_date: datetime
    check_out_date: datetime
    room_type: RoomType
    channel: BookingChannel
    rate: float
    status: BookingStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DemandForecast(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hotel_id: str
    date: datetime
    room_type: RoomType
    predicted_demand: float
    predicted_adr: float  # Average Daily Rate
    confidence_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InventoryAllocation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hotel_id: str
    room_type: RoomType
    date: datetime
    channel: BookingChannel
    allocated_rooms: int
    rate: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RateRecommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hotel_id: str
    room_type: RoomType
    date: datetime
    current_rate: float
    recommended_rate: float
    expected_revenue_lift: float
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Request Models
class HotelCreate(BaseModel):
    name: str
    location: str
    total_rooms: int
    room_types: Dict[str, int]

class BookingCreate(BaseModel):
    hotel_id: str
    room_id: str
    guest_name: str
    guest_email: str
    check_in_date: datetime
    check_out_date: datetime
    room_type: RoomType
    channel: BookingChannel
    rate: float
    status: BookingStatus = BookingStatus.CONFIRMED

class AllocationCreate(BaseModel):
    hotel_id: str
    room_type: RoomType
    date: datetime
    channel: BookingChannel
    allocated_rooms: int
    rate: float

# Hotel Management
@api_router.post("/hotels", response_model=Hotel)
async def create_hotel(hotel: HotelCreate):
    hotel_dict = hotel.dict()
    hotel_obj = Hotel(**hotel_dict)
    await db.hotels.insert_one(hotel_obj.dict())
    
    # Create rooms for the hotel
    for room_type, count in hotel.room_types.items():
        for i in range(count):
            room = Room(
                hotel_id=hotel_obj.id,
                room_number=f"{room_type.upper()}-{i+1:03d}",
                room_type=room_type,
                base_rate=100.0 + (i * 10)  # Base rate calculation
            )
            await db.rooms.insert_one(room.dict())
    
    return hotel_obj

@api_router.get("/hotels", response_model=List[Hotel])
async def get_hotels():
    hotels = await db.hotels.find().to_list(1000)
    return [Hotel(**hotel) for hotel in hotels]

@api_router.get("/hotels/{hotel_id}", response_model=Hotel)
async def get_hotel(hotel_id: str):
    hotel = await db.hotels.find_one({"id": hotel_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return Hotel(**hotel)

# Room Management
@api_router.get("/hotels/{hotel_id}/rooms", response_model=List[Room])
async def get_hotel_rooms(hotel_id: str):
    rooms = await db.rooms.find({"hotel_id": hotel_id}).to_list(1000)
    return [Room(**room) for room in rooms]

# Booking Management
@api_router.post("/bookings", response_model=Booking)
async def create_booking(booking: BookingCreate):
    booking_dict = booking.dict()
    booking_obj = Booking(**booking_dict)
    await db.bookings.insert_one(booking_obj.dict())
    return booking_obj

@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(hotel_id: Optional[str] = None, days_ahead: int = 30):
    filter_dict = {}
    if hotel_id:
        filter_dict["hotel_id"] = hotel_id
    
    # Get bookings for the next N days
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    filter_dict["check_in_date"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(filter_dict).to_list(1000)
    return [Booking(**booking) for booking in bookings]

# Demand Forecasting
@api_router.post("/forecast/{hotel_id}")
async def generate_demand_forecast(hotel_id: str, days_ahead: int = 30):
    # Get historical booking data
    historical_bookings = await db.bookings.find({
        "hotel_id": hotel_id,
        "check_in_date": {"$gte": datetime.utcnow() - timedelta(days=90)}
    }).to_list(1000)
    
    if len(historical_bookings) < 10:
        raise HTTPException(status_code=400, detail="Insufficient historical data for forecasting")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(historical_bookings)
    df['check_in_date'] = pd.to_datetime(df['check_in_date'])
    
    # Group by date and room type
    daily_demand = df.groupby([df['check_in_date'].dt.date, 'room_type']).agg({
        'id': 'count',
        'rate': 'mean'
    }).reset_index()
    daily_demand.columns = ['date', 'room_type', 'demand', 'avg_rate']
    
    forecasts = []
    
    for room_type in [RoomType.STANDARD, RoomType.DELUXE, RoomType.SUITE, RoomType.PRESIDENTIAL]:
        room_data = daily_demand[daily_demand['room_type'] == room_type]
        
        if len(room_data) < 5:
            continue
            
        # Simple linear regression for demand forecasting
        X = np.array(range(len(room_data))).reshape(-1, 1)
        y_demand = room_data['demand'].values
        y_rate = room_data['avg_rate'].values
        
        # Fit models
        demand_model = LinearRegression()
        rate_model = LinearRegression()
        
        demand_model.fit(X, y_demand)
        rate_model.fit(X, y_rate)
        
        # Generate forecasts
        for i in range(days_ahead):
            future_date = datetime.utcnow() + timedelta(days=i)
            future_x = np.array([[len(room_data) + i]])
            
            predicted_demand = max(0, demand_model.predict(future_x)[0])
            predicted_rate = max(50, rate_model.predict(future_x)[0])
            
            # Add seasonality and randomness
            day_of_week = future_date.weekday()
            weekend_multiplier = 1.3 if day_of_week >= 5 else 1.0
            
            predicted_demand *= weekend_multiplier
            predicted_rate *= weekend_multiplier
            
            confidence = max(0.3, 0.9 - (i * 0.01))  # Confidence decreases with time
            
            forecast = DemandForecast(
                hotel_id=hotel_id,
                date=future_date,
                room_type=room_type,
                predicted_demand=round(predicted_demand, 2),
                predicted_adr=round(predicted_rate, 2),
                confidence_score=confidence
            )
            
            forecasts.append(forecast)
    
    # Save forecasts to database
    for forecast in forecasts:
        await db.demand_forecasts.insert_one(forecast.dict())
    
    return {"message": f"Generated {len(forecasts)} demand forecasts", "forecasts": len(forecasts)}

@api_router.get("/forecast/{hotel_id}", response_model=List[DemandForecast])
async def get_demand_forecast(hotel_id: str, days_ahead: int = 30):
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    forecasts = await db.demand_forecasts.find({
        "hotel_id": hotel_id,
        "date": {"$gte": datetime.utcnow(), "$lte": end_date}
    }).to_list(1000)
    return [DemandForecast(**forecast) for forecast in forecasts]

# Inventory Allocation
@api_router.post("/allocations", response_model=InventoryAllocation)
async def create_allocation(allocation: AllocationCreate):
    allocation_dict = allocation.dict()
    allocation_obj = InventoryAllocation(**allocation_dict)
    await db.inventory_allocations.insert_one(allocation_obj.dict())
    return allocation_obj

@api_router.get("/allocations/{hotel_id}", response_model=List[InventoryAllocation])
async def get_allocations(hotel_id: str, days_ahead: int = 30):
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    allocations = await db.inventory_allocations.find({
        "hotel_id": hotel_id,
        "date": {"$gte": datetime.utcnow(), "$lte": end_date}
    }).to_list(1000)
    return [InventoryAllocation(**allocation) for allocation in allocations]

@api_router.post("/allocations/{hotel_id}/optimize")
async def optimize_inventory_allocation(hotel_id: str, days_ahead: int = 30):
    # Get hotel information
    hotel = await db.hotels.find_one({"id": hotel_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Get demand forecasts
    forecasts = await db.demand_forecasts.find({
        "hotel_id": hotel_id,
        "date": {"$gte": datetime.utcnow(), "$lte": datetime.utcnow() + timedelta(days=days_ahead)}
    }).to_list(1000)
    
    if not forecasts:
        raise HTTPException(status_code=400, detail="No demand forecasts available. Generate forecasts first.")
    
    allocations = []
    
    for forecast in forecasts:
        room_type = forecast['room_type']
        available_rooms = hotel['room_types'].get(room_type, 0)
        predicted_demand = forecast['predicted_demand']
        predicted_adr = forecast['predicted_adr']
        
        # Channel allocation strategy
        channels = [
            (BookingChannel.DIRECT, 0.4, 1.0),  # 40% allocation, full rate
            (BookingChannel.BOOKING_COM, 0.3, 0.9),  # 30% allocation, 10% commission
            (BookingChannel.EXPEDIA, 0.2, 0.85),  # 20% allocation, 15% commission
            (BookingChannel.WALK_IN, 0.1, 1.1)  # 10% allocation, walk-in premium
        ]
        
        for channel, allocation_ratio, rate_multiplier in channels:
            allocated_rooms = min(
                int(available_rooms * allocation_ratio),
                int(predicted_demand * allocation_ratio)
            )
            
            if allocated_rooms > 0:
                allocation = InventoryAllocation(
                    hotel_id=hotel_id,
                    room_type=room_type,
                    date=forecast['date'] if isinstance(forecast['date'], datetime) else datetime.fromisoformat(str(forecast['date']).replace('Z', '+00:00')),
                    channel=channel,
                    allocated_rooms=allocated_rooms,
                    rate=round(predicted_adr * rate_multiplier, 2)
                )
                allocations.append(allocation)
    
    # Save allocations to database
    for allocation in allocations:
        await db.inventory_allocations.insert_one(allocation.dict())
    
    return {"message": f"Optimized inventory allocation for {len(allocations)} entries", "allocations": len(allocations)}

# Revenue Analytics
@api_router.get("/analytics/{hotel_id}/dashboard")
async def get_revenue_dashboard(hotel_id: str):
    # Get current bookings
    today = datetime.utcnow().date()
    bookings = await db.bookings.find({
        "hotel_id": hotel_id,
        "check_in_date": {"$gte": datetime.combine(today, datetime.min.time())}
    }).to_list(1000)
    
    # Get hotel info
    hotel = await db.hotels.find_one({"id": hotel_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    total_rooms = hotel['total_rooms']
    
    # Calculate key metrics
    total_revenue = sum(booking['rate'] for booking in bookings)
    total_bookings = len(bookings)
    occupancy_rate = (total_bookings / total_rooms) * 100 if total_rooms > 0 else 0
    adr = total_revenue / total_bookings if total_bookings > 0 else 0
    revpar = total_revenue / total_rooms if total_rooms > 0 else 0
    
    # Channel performance
    channel_performance = {}
    for booking in bookings:
        channel = booking['channel']
        if channel not in channel_performance:
            channel_performance[channel] = {'bookings': 0, 'revenue': 0}
        channel_performance[channel]['bookings'] += 1
        channel_performance[channel]['revenue'] += booking['rate']
    
    # Room type performance
    room_type_performance = {}
    for booking in bookings:
        room_type = booking['room_type']
        if room_type not in room_type_performance:
            room_type_performance[room_type] = {'bookings': 0, 'revenue': 0}
        room_type_performance[room_type]['bookings'] += 1
        room_type_performance[room_type]['revenue'] += booking['rate']
    
    return {
        "hotel_name": hotel['name'],
        "total_rooms": total_rooms,
        "metrics": {
            "total_revenue": round(total_revenue, 2),
            "total_bookings": total_bookings,
            "occupancy_rate": round(occupancy_rate, 2),
            "adr": round(adr, 2),
            "revpar": round(revpar, 2)
        },
        "channel_performance": channel_performance,
        "room_type_performance": room_type_performance
    }

# Rate Optimization
@api_router.post("/rates/{hotel_id}/optimize")
async def optimize_rates(hotel_id: str, days_ahead: int = 7):
    # Get demand forecasts
    forecasts = await db.demand_forecasts.find({
        "hotel_id": hotel_id,
        "date": {"$gte": datetime.utcnow(), "$lte": datetime.utcnow() + timedelta(days=days_ahead)}
    }).to_list(1000)
    
    if not forecasts:
        raise HTTPException(status_code=400, detail="No demand forecasts available")
    
    # Get current rates
    rooms = await db.rooms.find({"hotel_id": hotel_id}).to_list(1000)
    current_rates = {room['room_type']: room['base_rate'] for room in rooms}
    
    recommendations = []
    
    for forecast in forecasts:
        room_type = forecast['room_type']
        current_rate = current_rates.get(room_type, 100)
        predicted_demand = forecast['predicted_demand']
        predicted_adr = forecast['predicted_adr']
        confidence = forecast['confidence_score']
        
        # Rate optimization logic
        if predicted_demand > 8:  # High demand
            recommended_rate = current_rate * 1.2
            reason = "High demand predicted - increase rate by 20%"
        elif predicted_demand > 5:  # Medium demand
            recommended_rate = current_rate * 1.1
            reason = "Medium demand predicted - increase rate by 10%"
        elif predicted_demand < 2:  # Low demand
            recommended_rate = current_rate * 0.9
            reason = "Low demand predicted - decrease rate by 10%"
        else:
            recommended_rate = current_rate
            reason = "Maintain current rate"
        
        # Calculate expected revenue lift
        expected_revenue_lift = (recommended_rate - current_rate) * predicted_demand
        
        recommendation = RateRecommendation(
            hotel_id=hotel_id,
            room_type=room_type,
            date=forecast['date'] if isinstance(forecast['date'], datetime) else datetime.fromisoformat(str(forecast['date']).replace('Z', '+00:00')),
            current_rate=current_rate,
            recommended_rate=round(recommended_rate, 2),
            expected_revenue_lift=round(expected_revenue_lift, 2),
            reason=reason
        )
        
        recommendations.append(recommendation)
    
    # Save recommendations
    for recommendation in recommendations:
        await db.rate_recommendations.insert_one(recommendation.dict())
    
    return {"message": f"Generated {len(recommendations)} rate recommendations", "recommendations": len(recommendations)}

@api_router.get("/rates/{hotel_id}/recommendations", response_model=List[RateRecommendation])
async def get_rate_recommendations(hotel_id: str, days_ahead: int = 7):
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    recommendations = await db.rate_recommendations.find({
        "hotel_id": hotel_id,
        "date": {"$gte": datetime.utcnow(), "$lte": end_date}
    }).to_list(1000)
    return [RateRecommendation(**rec) for rec in recommendations]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()