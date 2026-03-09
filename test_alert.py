"""Test script for /test-alert endpoint"""
import urllib.request
import urllib.parse

url = "http://localhost:8001/test-alert"
data = urllib.parse.urlencode({
    "latitude": "12.9716",
    "longitude": "77.5946"
}).encode()

try:
    req = urllib.request.Request(url, data=data, method="POST")
    response = urllib.request.urlopen(req)
    print(f"Status Code: {response.status}")
    print(f"Response: {response.read().decode()}")
except Exception as e:
    print(f"Error: {e}")

