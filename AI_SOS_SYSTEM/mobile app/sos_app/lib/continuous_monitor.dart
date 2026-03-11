/// Continuous Monitoring Service
/// Automatically records audio in short intervals and sends for analysis.
/// Runs in a loop until stopped by the user.

import 'dart:async';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:geolocator/geolocator.dart';
import 'sos_service.dart';

/// Callback type for when an emotion prediction result is received
typedef OnEmotionResult = void Function(Map<String, dynamic> result);

/// Callback type for status messages
typedef OnStatusUpdate = void Function(String message);

/// Callback type for when countdown starts (needs user confirmation)
typedef OnCountdownStart = void Function(Map<String, dynamic> result);

class ContinuousMonitor {
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _monitorTimer;
  bool _isMonitoring = false;
  bool _isProcessing = false;
  
  /// Flag to track if user is in countdown/cancel mode
  bool _isInCountdown = false;

  /// Duration of each recording clip (seconds)
  final int recordingDuration;

  /// Pause between recordings (seconds)
  final int pauseBetween;

  /// Callbacks
  final OnEmotionResult onResult;
  final OnStatusUpdate onStatus;
  final OnCountdownStart? onCountdownStart;

  ContinuousMonitor({
    this.recordingDuration = 4,
    this.pauseBetween = 1,
    required this.onResult,
    required this.onStatus,
    this.onCountdownStart,
  });

  bool get isMonitoring => _isMonitoring;
  
  /// Check if user is currently in countdown/cancel mode
  bool get isInCountdown => _isInCountdown;
  
  /// Called when user starts countdown - should pause monitoring
  void startCountdown() {
    _isInCountdown = true;
    onStatus("⏳ Waiting for user confirmation...");
  }
  
  /// Called when user cancels or confirms - can resume monitoring
  void endCountdown() {
    _isInCountdown = false;
    onStatus("🔄 Resuming monitoring...");
  }

  /// Start continuous monitoring loop
  Future<void> start() async {
    if (_isMonitoring) return;
    _isMonitoring = true;
    onStatus("🔄 Continuous monitoring started");

    // Run the first cycle immediately, then repeat
    _runCycle();
  }

  /// Stop continuous monitoring
  Future<void> stop() async {
    _isMonitoring = false;
    _monitorTimer?.cancel();
    _monitorTimer = null;

    // Stop any active recording
    if (await _recorder.isRecording()) {
      await _recorder.stop();
    }

    onStatus("⏹️ Monitoring stopped");
  }

  /// Single record → analyze cycle
  Future<void> _runCycle() async {
    if (!_isMonitoring || _isProcessing) return;
    _isProcessing = true;

    try {
      // 1. Record a short clip
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/continuous_${DateTime.now().millisecondsSinceEpoch}.wav';

      onStatus("🎙️ Listening...");
      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.wav),
        path: path,
      );

      // Wait for recording duration
      await Future.delayed(Duration(seconds: recordingDuration));

      final filePath = await _recorder.stop();
      if (filePath == null || !_isMonitoring) {
        _isProcessing = false;
        return;
      }

      // 2. Get GPS location
      onStatus("📍 Getting location...");
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      // 3. Send for analysis
      onStatus("🧠 Analyzing emotion...");
      Map<String, dynamic> result = await SosService.sendAudioForPrediction(
        audioFilePath: filePath,
        latitude: position.latitude,
        longitude: position.longitude,
      );

      // 4. Deliver result
      onResult(result);

      // 5. If distress detected, pause monitoring and wait for user confirmation
      // IMPORTANT: SOS is NOT sent automatically - it requires user confirmation!
      // The mobile app shows a 20-second countdown dialog where user can cancel
      if (result['distress']?['distress_detected'] == true) {
        // Signal that we're in countdown mode
        _isInCountdown = true;
        
        // Notify via callback if provided
        if (onCountdownStart != null) {
          onCountdownStart!(result);
        }
        
        // Update status - user needs to confirm or cancel
        onStatus("🚨 DISTRESS DETECTED - Waiting for user confirmation...");
        
        // Wait here until user either confirms or cancels the alert
        // The home_screen will call endCountdown() when done
        while (_isInCountdown && _isMonitoring) {
          await Future.delayed(const Duration(milliseconds: 500));
        }
        
        // After countdown ends (user confirmed or cancelled), pause briefly
        if (_isMonitoring) {
          onStatus("⏸️ Pausing briefly after alert action...");
          await Future.delayed(const Duration(seconds: 10));
        }
      }
    } catch (e) {
      onStatus("⚠️ Cycle error: $e");
    } finally {
      _isProcessing = false;
    }

    // Schedule next cycle after a short pause
    if (_isMonitoring) {
      _monitorTimer = Timer(
        Duration(seconds: pauseBetween),
        _runCycle,
      );
    }
  }

  /// Clean up resources
  void dispose() {
    stop();
    _recorder.dispose();
  }
}
