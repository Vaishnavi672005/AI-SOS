"""
SOS Alert Manager Module
Handles sending SOS alerts to emergency contacts
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SOSAlertManager:
    """
    Manages SOS alert creation and sending.
    """
    
    def __init__(self):
        """Initialize the SOS alert manager."""
        # Twilio credentials (set in .env file)
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.to_number = os.getenv('EMERGENCY_CONTACT')
        
        # Alert history
        self.alert_history = []
        
        # Initialize Twilio client if available
        self.client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            if self.account_sid and self.auth_token:
                self.client = Client(self.account_sid, self.auth_token)
                print("Twilio client initialized")
            else:
                print("Twilio credentials not configured - SMS alerts disabled")
        except ImportError:
            print("Twilio not installed - SMS alerts disabled")
        except Exception as e:
            print(f"Error initializing Twilio: {e}")
    
    async def trigger_alert(self, emotion, confidence, location, message=None):
        """
        Trigger an SOS alert.
        
        Args:
            emotion: Detected emotion
            confidence: Emotion detection confidence
            location: Location dictionary with latitude, longitude, address
            message: Optional custom message
        
        Returns:
            dict: Alert status information
        """
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'emotion': emotion,
            'confidence': confidence,
            'location': location,
            'message': message,
            'alert_sent': False,
            'alert_id': len(self.alert_history) + 1
        }
        
        # Create alert message with Google Maps link
        if message is None:
            lat = location.get('latitude', 0) if location else 0
            lon = location.get('longitude', 0) if location else 0
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            
            message = f"AI SOS Alert!\n"
            message += f"Detected Emotion: {emotion} ({confidence*100:.1f}% confidence)\n"
            if location:
                message += f"Location: {location.get('address', 'Unknown')}\n"
                message += f"Google Maps: {maps_link}\n"
            message += f"Time: {alert_data['timestamp']}"
        
        alert_data['message'] = message
        
        # Try to send SMS
        if self.client and self.to_number:
            try:
                sms_result = self._send_sms(message)
                alert_data['alert_sent'] = sms_result
                alert_data['sms_status'] = 'sent' if sms_result else 'failed'
            except Exception as e:
                alert_data['sms_error'] = str(e)
                alert_data['sms_status'] = 'error'
        
        # Store alert
        self.alert_history.append(alert_data)
        
        return alert_data
    
    def _send_sms(self, message):
        """
        Send SMS via Twilio.
        
        Args:
            message: Message to send
        
        Returns:
            bool: True if sent successfully
        """
        if not self.client:
            return False
        
        try:
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            print(f"SMS sent: {twilio_message.sid}")
            return True
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False
    
    def get_alert_history(self):
        """Get all alert history."""
        return self.alert_history
    
    def get_recent_alerts(self, count=10):
        """Get recent alerts."""
        return self.alert_history[-count:]
    
    def clear_history(self):
        """Clear alert history."""
        self.alert_history = []


# Standalone function to send quick alert
async def send_sos_alert(emotion, confidence, location, message=None):
    """
    Quick function to send SOS alert.
    
    Args:
        emotion: Detected emotion
        confidence: Confidence level
        location: Location dictionary
        message: Optional message
    
    Returns:
        dict: Alert result
    """
    manager = SOSAlertManager()
    return await manager.trigger_alert(emotion, confidence, location, message)


if __name__ == "__main__":
    # Test SOS alert
    import asyncio
    
    async def test():
        manager = SOSAlertManager()
        
        test_location = {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'address': 'San Francisco, CA'
        }
        
        result = await manager.trigger_alert(
            emotion='fear',
            confidence=0.85,
            location=test_location,
            message='Test SOS Alert'
        )
        
        print("Alert Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    
    asyncio.run(test())

