#!/usr/bin/env python3
import requests
import json
import uuid
from datetime import datetime, timedelta
import random
import time
import sys

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://15a1ce0c-cabd-48d9-a032-5878e23cc80e.preview.emergentagent.com/api"

# Test results tracking
test_results = {
    "total_tests": 0,
    "passed_tests": 0,
    "failed_tests": 0,
    "failures": []
}

def print_header(message):
    """Print a header message."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80, "="))
    print("=" * 80)

def print_subheader(message):
    """Print a subheader message."""
    print("\n" + "-" * 80)
    print(f" {message} ".center(80, "-"))
    print("-" * 80)

def test_endpoint(description, method, endpoint, data=None, expected_status=200, expected_keys=None):
    """Test an API endpoint and track results."""
    test_results["total_tests"] += 1
    
    print(f"\nTesting: {description}")
    print(f"  {method} {endpoint}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(f"{BACKEND_URL}{endpoint}")
        elif method.upper() == "POST":
            response = requests.post(f"{BACKEND_URL}{endpoint}", json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"  Status: {response.status_code}")
        
        # Check status code
        if response.status_code != expected_status:
            test_results["failed_tests"] += 1
            error_msg = f"Expected status {expected_status}, got {response.status_code}"
            test_results["failures"].append({
                "description": description,
                "error": error_msg,
                "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            })
            print(f"  FAILED: {error_msg}")
            return None
        
        # Parse response
        if response.text:
            try:
                result = response.json()
                print(f"  Response: {json.dumps(result, indent=2)[:200]}...")
                
                # Check expected keys
                if expected_keys:
                    missing_keys = [key for key in expected_keys if key not in result]
                    if missing_keys:
                        test_results["failed_tests"] += 1
                        error_msg = f"Missing expected keys: {missing_keys}"
                        test_results["failures"].append({
                            "description": description,
                            "error": error_msg
                        })
                        print(f"  FAILED: {error_msg}")
                        return result
                
                test_results["passed_tests"] += 1
                print("  PASSED")
                return result
            except json.JSONDecodeError:
                test_results["failed_tests"] += 1
                error_msg = "Invalid JSON response"
                test_results["failures"].append({
                    "description": description,
                    "error": error_msg,
                    "response": response.text[:200]
                })
                print(f"  FAILED: {error_msg}")
                return None
        else:
            test_results["passed_tests"] += 1
            print("  PASSED (Empty response)")
            return {}
    
    except Exception as e:
        test_results["failed_tests"] += 1
        error_msg = f"Exception: {str(e)}"
        test_results["failures"].append({
            "description": description,
            "error": error_msg
        })
        print(f"  FAILED: {error_msg}")
        return None

def print_summary():
    """Print a summary of test results."""
    print_header("TEST SUMMARY")
    print(f"Total tests: {test_results['total_tests']}")
    print(f"Passed: {test_results['passed_tests']}")
    print(f"Failed: {test_results['failed_tests']}")
    
    if test_results["failures"]:
        print("\nFailures:")
        for i, failure in enumerate(test_results["failures"], 1):
            print(f"\n{i}. {failure['description']}")
            print(f"   Error: {failure['error']}")
            if "response" in failure:
                print(f"   Response: {failure['response']}")

def generate_random_date(start_date, end_date):
    """Generate a random date between start_date and end_date."""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def main():
    print_header("HOTEL REVENUE MANAGEMENT SYSTEM API TESTS")
    
    # Step 1: Create a sample hotel
    print_subheader("1. Creating Sample Hotel")
    
    hotel_data = {
        "name": "Grand Test Hotel",
        "location": "Test City, Test Country",
        "total_rooms": 100,
        "room_types": {
            "standard": 50,
            "deluxe": 30,
            "suite": 15,
            "presidential": 5
        }
    }
    
    hotel = test_endpoint(
        "Create Hotel", 
        "POST", 
        "/hotels", 
        data=hotel_data,
        expected_keys=["id", "name", "location", "total_rooms", "room_types"]
    )
    
    if not hotel:
        print("Failed to create hotel. Cannot continue tests.")
        print_summary()
        return
    
    hotel_id = hotel["id"]
    print(f"Created hotel with ID: {hotel_id}")
    
    # Step 2: Get hotel details
    print_subheader("2. Getting Hotel Details")
    
    test_endpoint(
        "Get All Hotels", 
        "GET", 
        "/hotels"
    )
    
    test_endpoint(
        "Get Hotel by ID", 
        "GET", 
        f"/hotels/{hotel_id}",
        expected_keys=["id", "name", "location", "total_rooms", "room_types"]
    )
    
    # Step 3: Get hotel rooms
    print_subheader("3. Getting Hotel Rooms")
    
    rooms = test_endpoint(
        "Get Hotel Rooms", 
        "GET", 
        f"/hotels/{hotel_id}/rooms"
    )
    
    if not rooms or not isinstance(rooms, list) or len(rooms) == 0:
        print("Failed to get hotel rooms. Cannot continue tests.")
        print_summary()
        return
    
    # Step 4: Create sample bookings (at least 10 for historical data)
    print_subheader("4. Creating Sample Bookings")
    
    # Get room IDs for each room type
    room_ids_by_type = {}
    for room in rooms:
        room_type = room["room_type"]
        if room_type not in room_ids_by_type:
            room_ids_by_type[room_type] = []
        room_ids_by_type[room_type].append(room["id"])
    
    # Create at least 10 bookings with different check-in dates
    bookings = []
    channels = ["direct", "booking.com", "expedia", "airbnb", "walk-in"]
    
    # Create historical bookings (past 60 days)
    for i in range(15):
        # Select a random room type and room ID
        room_type = random.choice(list(room_ids_by_type.keys()))
        room_id = random.choice(room_ids_by_type[room_type])
        
        # Generate random dates in the past
        check_in_date = generate_random_date(
            datetime.utcnow() - timedelta(days=60),
            datetime.utcnow() - timedelta(days=1)
        )
        check_out_date = check_in_date + timedelta(days=random.randint(1, 5))
        
        booking_data = {
            "hotel_id": hotel_id,
            "room_id": room_id,
            "guest_name": f"Test Guest {i+1}",
            "guest_email": f"guest{i+1}@example.com",
            "check_in_date": check_in_date.isoformat(),
            "check_out_date": check_out_date.isoformat(),
            "room_type": room_type,
            "channel": random.choice(channels),
            "rate": random.uniform(100, 500),
            "status": "confirmed"
        }
        
        booking = test_endpoint(
            f"Create Historical Booking {i+1}", 
            "POST", 
            "/bookings", 
            data=booking_data,
            expected_keys=["id", "hotel_id", "room_id", "guest_name", "check_in_date"]
        )
        
        if booking:
            bookings.append(booking)
    
    # Create future bookings (next 30 days)
    for i in range(5):
        # Select a random room type and room ID
        room_type = random.choice(list(room_ids_by_type.keys()))
        room_id = random.choice(room_ids_by_type[room_type])
        
        # Generate random dates in the future
        check_in_date = generate_random_date(
            datetime.utcnow() + timedelta(days=1),
            datetime.utcnow() + timedelta(days=30)
        )
        check_out_date = check_in_date + timedelta(days=random.randint(1, 5))
        
        booking_data = {
            "hotel_id": hotel_id,
            "room_id": room_id,
            "guest_name": f"Future Guest {i+1}",
            "guest_email": f"future{i+1}@example.com",
            "check_in_date": check_in_date.isoformat(),
            "check_out_date": check_out_date.isoformat(),
            "room_type": room_type,
            "channel": random.choice(channels),
            "rate": random.uniform(100, 500),
            "status": "confirmed"
        }
        
        booking = test_endpoint(
            f"Create Future Booking {i+1}", 
            "POST", 
            "/bookings", 
            data=booking_data,
            expected_keys=["id", "hotel_id", "room_id", "guest_name", "check_in_date"]
        )
        
        if booking:
            bookings.append(booking)
    
    # Step 5: Get bookings
    print_subheader("5. Getting Bookings")
    
    test_endpoint(
        "Get All Bookings", 
        "GET", 
        "/bookings"
    )
    
    test_endpoint(
        "Get Hotel Bookings", 
        "GET", 
        f"/bookings?hotel_id={hotel_id}"
    )
    
    # Step 6: Generate demand forecasts
    print_subheader("6. Generating Demand Forecasts")
    
    forecast_result = test_endpoint(
        "Generate Demand Forecast", 
        "POST", 
        f"/forecast/{hotel_id}",
        expected_keys=["message", "forecasts"]
    )
    
    # Step 7: Get demand forecasts
    print_subheader("7. Getting Demand Forecasts")
    
    forecasts = test_endpoint(
        "Get Demand Forecasts", 
        "GET", 
        f"/forecast/{hotel_id}"
    )
    
    # Step 8: Create inventory allocations
    print_subheader("8. Creating Inventory Allocations")
    
    # Create a sample allocation
    allocation_data = {
        "hotel_id": hotel_id,
        "room_type": "standard",
        "date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "channel": "direct",
        "allocated_rooms": 10,
        "rate": 150.0
    }
    
    allocation = test_endpoint(
        "Create Inventory Allocation", 
        "POST", 
        "/allocations", 
        data=allocation_data,
        expected_keys=["id", "hotel_id", "room_type", "channel", "allocated_rooms", "rate"]
    )
    
    # Step 9: Get allocations
    print_subheader("9. Getting Inventory Allocations")
    
    test_endpoint(
        "Get Inventory Allocations", 
        "GET", 
        f"/allocations/{hotel_id}"
    )
    
    # Step 10: Optimize inventory allocation
    print_subheader("10. Optimizing Inventory Allocation")
    
    optimize_result = test_endpoint(
        "Optimize Inventory Allocation", 
        "POST", 
        f"/allocations/{hotel_id}/optimize",
        expected_keys=["message", "allocations"]
    )
    
    # Step 11: Optimize rates
    print_subheader("11. Optimizing Rates")
    
    rate_optimize_result = test_endpoint(
        "Optimize Rates", 
        "POST", 
        f"/rates/{hotel_id}/optimize",
        expected_keys=["message", "recommendations"]
    )
    
    # Step 12: Get rate recommendations
    print_subheader("12. Getting Rate Recommendations")
    
    recommendations = test_endpoint(
        "Get Rate Recommendations", 
        "GET", 
        f"/rates/{hotel_id}/recommendations"
    )
    
    # Step 13: Get revenue analytics dashboard
    print_subheader("13. Getting Revenue Analytics Dashboard")
    
    dashboard = test_endpoint(
        "Get Revenue Dashboard", 
        "GET", 
        f"/analytics/{hotel_id}/dashboard",
        expected_keys=["hotel_name", "total_rooms", "metrics"]
    )
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()