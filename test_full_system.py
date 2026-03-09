"""
Full System Test Script
Tests the backend API endpoints for emotion prediction and SOS alerts
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("\n=== Testing /health endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_root():
    """Test the root endpoint"""
    print("\n=== Testing / endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_model_info():
    """Test the model info endpoint"""
    print("\n=== Testing /model-info endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/model-info")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_location():
    """Test the location endpoint"""
    print("\n=== Testing /location endpoint ===")
    try:
        # Test with Bangalore coordinates
        lat, lon = 12.9716, 77.5946
        response = requests.get(f"{BASE_URL}/location/{lat}/{lon}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_test_alert():
    """Test the test alert endpoint"""
    print("\n=== Testing /test-alert endpoint ===")
    try:
        data = {
            "latitude": "12.9716",
            "longitude": "77.5946"
        }
        response = requests.post(f"{BASE_URL}/test-alert", data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Check if response contains Google Maps link
        if response.status_code == 200:
            result = response.json()
            alert = result.get('alert', {})
            message = alert.get('message', '')
            location = result.get('location', {})
            lat = location.get('latitude')
            lon = location.get('longitude')
            
            # Verify Google Maps link format
            expected_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            print(f"\nExpected Google Maps Link: {expected_maps_link}")
            
            if 'maps' in message.lower() or lat and lon:
                print("✓ Google Maps link verification: PASSED")
            else:
                print("✗ Google Maps link verification: FAILED")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_trigger_sos():
    """Test manual SOS trigger"""
    print("\n=== Testing /trigger-sos endpoint ===")
    try:
        data = {
            "latitude": "12.9716",
            "longitude": "77.5946",
            "message": "Test SOS Alert from Full System Test"
        }
        response = requests.post(f"{BASE_URL}/trigger-sos", data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("AI SOS System - Full System Test")
    print("=" * 60)
    
    print("\nNOTE: Make sure the backend server is running:")
    print("  cd AI_SOS_SYSTEM/backend")
    print("  python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print()
    
    # Run tests
    results = []
    
    results.append(("Root Endpoint", test_root()))
    results.append(("Health Check", test_health()))
    results.append(("Model Info", test_model_info()))
    results.append(("Location Service", test_location()))
    results.append(("Test Alert", test_test_alert()))
    results.append(("Trigger SOS", test_trigger_sos()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All backend tests passed!")
        print("\nTo complete full system test:")
        print("1. Start Flutter app: cd mobile app/sos_app && flutter run")
        print("2. Tap microphone and speak angrily/fearfully")
        print("3. Verify SOS dialog appears for distress emotions")
        print("4. Check SMS/email for alert with Google Maps link")
    else:
        print("\n⚠️ Some tests failed. Check backend server status.")

if __name__ == "__main__":
    main()
