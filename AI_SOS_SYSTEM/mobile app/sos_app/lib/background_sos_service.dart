/// Background SOS Service
/// Runs continuously in the background to monitor emotions and send SOS alerts
/// even when the app is closed.

import 'dart:async';
import 'dart:io';
import 'dart:ui';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:geolocator/geolocator.dart';
import 'package:record/record.dart';
import 'sos_service.dart';

/// Initialize the background service
Future<void> initializeBackgroundService() async {
  final service = FlutterBackgroundService();
  
  await service.configure(
    androidConfiguration: AndroidConfiguration(
      onStart: onStart,
      autoStart: false,
      isForegroundMode: true,
      notificationChannelId: 'ai_sos_channel',
      initialNotificationTitle: 'AI SOS Active',
      initialNotificationContent: 'Monitoring for distress...',
      foregroundServiceNotificationId: 888,
      foregroundServiceTypes: [AndroidForegroundType.microphone],
    ),
    iosConfiguration: IosConfiguration(
      autoStart: false,
      onForeground: onStart,
      onBackground: onIosBackground,
    ),
  );
}

/// iOS background handler
@pragma('vm:entry-point')
Future<bool> onIosBackground(ServiceInstance service) async {
  return true;
}

/// Main background service entry point
@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();
  
  final FlutterLocalNotificationsPlugin notifications = FlutterLocalNotificationsPlugin();
  
  // Initialize notification channel for Android
  if (service is AndroidServiceInstance) {
    service.on('setAsForeground').listen((event) {
      service.setAsForegroundService();
    });
    
    service.on('setAsBackground').listen((event) {
      service.setAsBackgroundService();
    });
  }
  
  service.on('stopService').listen((event) {
    service.stopSelf();
  });
  
  // Recording configuration
  final AudioRecorder recorder = AudioRecorder();
  bool isRecording = false;
  
  // Main monitoring loop
  Timer.periodic(const Duration(seconds: 5), (timer) async {
    if (service is AndroidServiceInstance) {
      if (await service.isForegroundService()) {
        // Update notification
        service.setForegroundNotificationInfo(
          title: 'AI SOS Active',
          content: isRecording ? 'Recording & analyzing...' : 'Waiting...',
        );
      }
    }
    
    try {
      // Check if we should be running (service is still active)
      // Record a short audio clip
      if (!isRecording) {
        isRecording = true;
        
        try {
          // Get temp directory for recording
          final directory = Directory.systemTemp;
          final path = '${directory.path}/bg_ai_sos_${DateTime.now().millisecondsSinceEpoch}.wav';
          
          // Start recording
          await recorder.start(
            const RecordConfig(encoder: AudioEncoder.wav),
            path: path,
          );
          
          // Record for 4 seconds
          await Future.delayed(const Duration(seconds: 4));
          
          // Stop recording
          final filePath = await recorder.stop();
          
          if (filePath != null) {
            // Get GPS location
            Position? position;
            try {
              position = await Geolocator.getCurrentPosition(
                desiredAccuracy: LocationAccuracy.high,
              );
            } catch (e) {
              // Location might not be available
            }
            
            // Send for analysis
            if (position != null) {
              final result = await SosService.sendAudioForPrediction(
                audioFilePath: filePath,
                latitude: position.latitude,
                longitude: position.longitude,
              );
              
              // Check if distress detected
              final distressDetected = result['distress']?['distress_detected'] == true;
              final sosTriggered = result['sos_triggered'] == true;
              
              if (distressDetected) {
                // Show alert notification
                await notifications.show(
                  1,
                  '🚨 DISTRESS DETECTED',
                  'Emotion: ${result['prediction']?['emotion']} - SOS Alert Sent!',
                  const NotificationDetails(
                    android: AndroidNotificationDetails(
                      'ai_sos_alerts',
                      'SOS Alerts',
                      channelDescription: 'Alerts when distress is detected',
                      importance: Importance.high,
                      priority: Priority.high,
                      playSound: true,
                      enableVibration: true,
                    ),
                  ),
                );
              }
              
              // Send status update to app
              service.invoke('update', {
                'emotion': result['prediction']?['emotion'],
                'confidence': result['prediction']?['confidence'],
                'distress_detected': distressDetected,
                'sos_triggered': sosTriggered,
                'latitude': position.latitude,
                'longitude': position.longitude,
              });
            }
            
            // Clean up audio file
            try {
              final file = File(filePath);
              if (await file.exists()) {
                await file.delete();
              }
            } catch (e) {
              // Ignore cleanup errors
            }
          }
        } catch (e) {
          // Recording or analysis error
        }
        
        isRecording = false;
      }
    } catch (e) {
      isRecording = false;
    }
  });
}

/// Start the background service
Future<bool> startBackgroundService() async {
  final service = FlutterBackgroundService();
  final isRunning = await service.isRunning();
  
  if (!isRunning) {
    return await service.startService();
  }
  return true;
}

/// Stop the background service
Future<void> stopBackgroundService() async {
  final service = FlutterBackgroundService();
  service.invoke('stopService');
}

/// Check if background service is running
Future<bool> isBackgroundServiceRunning() async {
  final service = FlutterBackgroundService();
  return await service.isRunning();
}
