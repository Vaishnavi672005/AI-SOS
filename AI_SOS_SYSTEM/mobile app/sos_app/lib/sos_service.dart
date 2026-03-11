/// SOS Service
/// Handles communication with the FastAPI backend.
/// Sends audio files and GPS coordinates, receives emotion predictions.

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class SosService {
  // ============================================================
  // CONFIGURATION - Change these values for your environment
  // ============================================================
  
  // IMPORTANT: For production deployment on Render:
  // 1. Deploy backend to Render.com
  // 2. Replace the URL below with your Render service URL
  //    e.g., "https://your-app-name.onrender.com"
  //
  // For local development:
  // - Android Emulator: use 10.0.2.2 instead of localhost
  // - iOS Simulator: use localhost (or 127.0.0.1)
  // - Physical Device: use your computer's local IP (e.g., 192.168.1.100)
  
// Set this to true when deploying to production
  static const bool isProduction = true;
  
  // Replace this with your Render URL when deployed
  // Format: "https://your-service-name.onrender.com"
  static const String productionUrl = "https://ai-sos-1.onrender.com";
  
  // Development URL (for real phone on same WiFi - use your computer's IP)
  static const String developmentUrl = "http://172.24.3.5:8000";
  
  // Auto-select URL based on environment
  static String get baseUrl => isProduction ? productionUrl : developmentUrl;

  /// Send recorded audio and GPS location to backend for emotion prediction.
  ///
  /// Returns a Map with prediction results or error information.
  static Future<Map<String, dynamic>> sendAudioForPrediction({
    required String audioFilePath,
    required double latitude,
    required double longitude,
  }) async {
    try {
      // Create multipart request to /predict-emotion endpoint
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/predict-emotion'));

      // Attach audio file
      request.files.add(
        await http.MultipartFile.fromPath('audio', audioFilePath),
      );

      // Attach GPS coordinates as form fields
      request.fields['latitude'] = latitude.toString();
      request.fields['longitude'] = longitude.toString();

      // Send request
      print('📤 Sending audio to backend...');
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        var result = jsonDecode(response.body);
        print('✅ Response received: ${result['emotion']}');
        
        // Transform backend response to match Flutter app's expected format
        // Backend returns: {emotion, confidence, is_distress, location, sos_triggered, sos_alert}
        // Flutter expects: {prediction: {emotion, confidence}, distress: {distress_detected, severity}}
        return _transformBackendResponse(result);
      } else {
        print('❌ Server error: ${response.statusCode}');
        return {'error': 'Server returned ${response.statusCode}'};
      }
    } catch (e) {
      print('❌ Connection error: $e');
      return {'error': 'Could not connect to server: $e'};
    }
  }

  /// Transform backend response to match Flutter app's expected format
  static Map<String, dynamic> _transformBackendResponse(Map<String, dynamic> backendResponse) {
    final String emotion = backendResponse['emotion'] ?? 'unknown';
    final double confidence = (backendResponse['confidence'] ?? 0.0).toDouble();
    final bool isDistress = backendResponse['is_distress'] ?? false;
    
    // Determine severity based on emotion and confidence
    String severity = 'low';
    if (isDistress) {
      if (confidence >= 0.8) {
        severity = 'high';
      } else if (confidence >= 0.6) {
        severity = 'moderate';
      } else {
        severity = 'low';
      }
    }

    return {
      'prediction': {
        'emotion': emotion,
        'confidence': confidence,
      },
      'distress': {
        'distress_detected': isDistress,
        'severity': severity,
      },
      'location': backendResponse['location'],
      'sos_triggered': backendResponse['sos_triggered'] ?? false,
      'sos_alert': backendResponse['sos_alert'],
    };
  }
  
  /// Trigger SOS alert manually after user confirms in countdown
  /// This is called when the 20-second countdown expires
  static Future<Map<String, dynamic>> triggerSOS({
    required double latitude,
    required double longitude,
    String? message,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/trigger-sos'));
      
      // Attach GPS coordinates as form fields
      request.fields['latitude'] = latitude.toString();
      request.fields['longitude'] = longitude.toString();
      
      if (message != null) {
        request.fields['message'] = message;
      }
      
      print('📤 Triggering SOS alert...');
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        var result = jsonDecode(response.body);
        print('✅ SOS triggered successfully');
        return {'success': true, 'alert': result};
      } else {
        print('❌ Server error: ${response.statusCode}');
        return {'error': 'Server returned ${response.statusCode}'};
      }
    } catch (e) {
      print('❌ Connection error: $e');
      return {'error': 'Could not connect to server: $e'};
    }
  }
}
