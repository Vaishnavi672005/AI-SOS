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

class ContinuousMonitor {
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _monitorTimer;
  bool _isMonitoring = false;
  bool _isProcessing = false;

  /// Duration of each recording clip (seconds)
  final int recordingDuration;

  /// Pause between recordings (seconds)
  final int pauseBetween;

  /// Callbacks
  final OnEmotionResult onResult;
  final OnStatusUpdate onStatus;

  ContinuousMonitor({
    this.recordingDuration = 4,
    this.pauseBetween = 1,
    required this.onResult,
    required this.onStatus,
  });

  bool get isMonitoring => _isMonitoring;

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

      // 5. If distress detected with SOS triggered, pause monitoring briefly
      if (result['distress']?['distress_detected'] == true) {
        onStatus("🚨 DISTRESS DETECTED — Alert sent. Pausing 30s...");
        await Future.delayed(const Duration(seconds: 30));
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
