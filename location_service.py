"""
Location Service Module
Handles reverse geocoding and location lookups
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LocationService:
    """
    Provides location services including reverse geocoding.
    """
    
    def __init__(self):
        """Initialize the location service."""
        # OpenCage or OpenStreetMap for reverse geocoding (free)
        self.geocode_api_key = os.getenv('GEOCODING_API_KEY')
        self.use_nominatim = True  # Use OpenStreetMap (free, no API key)
    
    def get_address(self, latitude, longitude):
        """
        Get address from coordinates using reverse geocoding.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        
        Returns:
            str: Address string or error message
        """
        if self.use_nominatim:
            return self._nominatim_reverse(latitude, longitude)
        elif self.geocode_api_key:
            return self._opencage_reverse(latitude, longitude)
        else:
            return f"Lat: {latitude}, Lon: {longitude}"
    
    def _nominatim_reverse(self, latitude, longitude):
        """
        Use OpenStreetMap Nominatim for reverse geocoding.
        
        Args:
            latitude: Latitude
            longitude: Longitude
        
        Returns:
            str: Address
        """
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'json',
                'lat': latitude,
                'lon': longitude,
                'zoom': 18,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'AI-SOS-System/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('display_name'):
                    return data['display_name']
                elif data.get('address'):
                    addr = data['address']
                    return addr.get('road', '') + ', ' + addr.get('city', '') + ', ' + addr.get('country', '')
            
            return f"Location: {latitude}, {longitude}"
            
        except Exception as e:
            print(f"Geocoding error: {e}")
            return f"Lat: {latitude}, Lon: {longitude}"
    
    def _opencage_reverse(self, latitude, longitude):
        """
        Use OpenCage for reverse geocoding.
        
        Args:
            latitude: Latitude
            longitude: Longitude
        
        Returns:
            str: Address
        """
        try:
            url = f"https://api.opencagedata.com/geocode/v1/json"
            params = {
                'key': self.geocode_api_key,
                'lat': latitude,
                'lon': longitude,
                'no_annotations': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    return data['results'][0]['formatted']
            
            return f"Location: {latitude}, {longitude}"
            
        except Exception as e:
            print(f"OpenCage error: {e}")
            return f"Lat: {latitude}, Lon: {longitude}"
    
    def get_coordinates_from_address(self, address):
        """
        Get coordinates from address (forward geocoding).
        
        Args:
            address: Address string
        
        Returns:
            dict: {'latitude': float, 'longitude': float}
        """
        if self.use_nominatim:
            return self._nominatim_forward(address)
        return None
    
    def _nominatim_forward(self, address):
        """
        Use Nominatim for forward geocoding.
        
        Args:
            address: Address string
        
        Returns:
            dict: Coordinates
        """
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'format': 'json',
                'q': address,
                'limit': 1
            }
            headers = {
                'User-Agent': 'AI-SOS-System/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        'latitude': float(data[0]['lat']),
                        'longitude': float(data[0]['lon'])
                    }
            
            return None
            
        except Exception as e:
            print(f"Forward geocoding error: {e}")
            return None


# Standalone function for quick location lookup
def get_location_address(latitude, longitude):
    """
    Quick function to get address from coordinates.
    
    Args:
        latitude: Latitude
        longitude: Longitude
    
    Returns:
        str: Address
    """
    service = LocationService()
    return service.get_address(latitude, longitude)


if __name__ == "__main__":
    # Test location service
    service = LocationService()
    
    # Test reverse geocoding
    test_coords = [
        (37.7749, -122.4194),  # San Francisco
        (40.7128, -74.0060),   # New York
        (51.5074, -0.1278),    # London
    ]
    
    print("Location Service Tests:")
    print("-" * 50)
    for lat, lon in test_coords:
        address = service.get_address(lat, lon)
        print(f"Coordinates: {lat}, {lon}")
        print(f"Address: {address}")
        print()

