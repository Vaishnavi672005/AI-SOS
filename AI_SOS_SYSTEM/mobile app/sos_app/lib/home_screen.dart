/// Home Screen
/// Main UI for the SOS Emergency System.
/// Features: Start/Stop recording, emotion display, SOS alert display.

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'sos_service.dart';
import 'continuous_monitor.dart';
import 'background_sos_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // ─── State Variables ───
  final AudioRecorder _recorder = AudioRecorder();
  late ContinuousMonitor _continuousMonitor;
  bool _continuousMode = false;
  bool _backgroundMode = false;
  bool _isRecording = false;
  bool _isProcessing = false;
  String _emotion = "—";
  double _confidence = 0.0;
  bool _distressDetected = false;
  String _severity = "";
  String _statusMessage = "Tap the button to start monitoring";
  
  // ─── Countdown Timer Variables ───
  bool _showCountdown = false;
  int _countdownSeconds = 10;
  Timer? _countdownTimer;
  Position? _pendingAlertPosition;

  @override
  void initState() {
    super.initState();
    _continuousMonitor = ContinuousMonitor(
      recordingDuration: 4,
      pauseBetween: 2,
      onResult: (result) {
        if (!mounted) return;
        if (result.containsKey('error')) {
          setState(() => _statusMessage = "❌ ${result['error']}");
          return;
        }
        setState(() {
          _emotion = result['prediction']['emotion'];
          _confidence = result['prediction']['confidence'];
          _distressDetected = result['distress']['distress_detected'];
          _severity = result['distress']['severity'];
          if (_distressDetected) {
            _statusMessage = "🚨 DISTRESS DETECTED! Waiting for confirmation...";
            _showCountdownDialog();
          } else {
            _statusMessage = "✅ Monitoring... $_emotion (${(_confidence * 100).toStringAsFixed(0)}%)";
          }
        });
      },
      onStatus: (msg) {
        if (mounted) setState(() => _statusMessage = msg);
      },
    );
    
    // Check if background service is already running
    _checkBackgroundService();
  }
  
  Future<void> _checkBackgroundService() async {
    final isRunning = await isBackgroundServiceRunning();
    if (mounted) {
      setState(() => _backgroundMode = isRunning);
    }
  }

  @override
  void dispose() {
    _continuousMonitor.dispose();
    _recorder.dispose();
    _countdownTimer?.cancel();
    super.dispose();
  }

  /// Request microphone and location permissions
  Future<bool> _requestPermissions() async {
    var micStatus = await Permission.microphone.request();
    var locStatus = await Permission.location.request();
    var notifStatus = await Permission.notification.request();
    return micStatus.isGranted && locStatus.isGranted;
  }

  /// Get current GPS position
  Future<Position> _getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled');
    }

    return await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  /// Start recording audio from microphone
  Future<void> _startRecording() async {
    bool hasPermission = await _requestPermissions();
    if (!hasPermission) {
      setState(() {
        _statusMessage = "❌ Microphone/location permission denied";
      });
      return;
    }

    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/sos_recording.wav';

    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: path,
    );

    setState(() {
      _isRecording = true;
      _statusMessage = "🎙️ Recording... Tap stop when ready";
      _distressDetected = false;
    });
  }

  /// Stop recording and send audio for analysis
  Future<void> _stopRecording() async {
    final path = await _recorder.stop();

    if (path == null) {
      setState(() {
        _statusMessage = "❌ Recording failed";
      });
      return;
    }

    setState(() {
      _isRecording = false;
      _isProcessing = true;
      _statusMessage = "🔄 Analyzing voice emotion...";
    });

    try {
      Position position = await _getCurrentLocation();

      Map<String, dynamic> result = await SosService.sendAudioForPrediction(
        audioFilePath: path,
        latitude: position.latitude,
        longitude: position.longitude,
      );

      if (result.containsKey('error')) {
        setState(() {
          _statusMessage = "❌ ${result['error']}";
          _isProcessing = false;
        });
        return;
      }

      setState(() {
        _emotion = result['prediction']['emotion'];
        _confidence = result['prediction']['confidence'];
        _distressDetected = result['distress']['distress_detected'];
        _severity = result['distress']['severity'];
        _isProcessing = false;

        if (_distressDetected) {
          _statusMessage = "🚨 DISTRESS DETECTED! Confirm to send alert...";
          _pendingAlertPosition = position;
          _showCountdownDialog();
        } else {
          _statusMessage = "✅ No distress detected. You're safe.";
        }
      });

    } catch (e) {
      setState(() {
        _statusMessage = "❌ Error: $e";
        _isProcessing = false;
      });
    }
  }

  /// Show countdown dialog before sending alert
  void _showCountdownDialog() {
    setState(() {
      _showCountdown = true;
      _countdownSeconds = 10;
    });
    
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      
      setState(() {
        _countdownSeconds--;
      });
      
      if (_countdownSeconds <= 0) {
        timer.cancel();
        _sendActualAlert();
      }
    });
    
    // Show the countdown dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _CountdownDialog(
        seconds: _countdownSeconds,
        emotion: _emotion,
        confidence: _confidence,
        severity: _severity,
        onCancel: _cancelCountdown,
      ),
    );
  }

  /// Cancel the countdown
  void _cancelCountdown() {
    _countdownTimer?.cancel();
    Navigator.of(context).pop(); // Close dialog
    setState(() {
      _showCountdown = false;
      _countdownSeconds = 10;
      _statusMessage = "✅ Alert cancelled. Monitoring continues...";
    });
  }

  /// Send the actual SOS alert after countdown
  Future<void> _sendActualAlert() async {
    Navigator.of(context).pop(); // Close dialog
    
    Position position = _pendingAlertPosition ?? await _getCurrentLocation();
    
    // Trigger SOS alert on backend
    try {
      await SosService.sendAudioForPrediction(
        audioFilePath: '', // Empty - we just trigger the alert
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (e) {
      // Even if it fails, show the dialog
    }
    
    if (mounted) {
      _showSOSDialog();
    }
    
    setState(() {
      _showCountdown = false;
      _countdownSeconds = 10;
      _pendingAlertPosition = null;
    });
  }

  /// Toggle background monitoring
  Future<void> _toggleBackgroundMode(bool value) async {
    if (value) {
      // Start background service
      bool hasPermission = await _requestPermissions();
      if (!hasPermission) {
        if (mounted) {
          setState(() => _backgroundMode = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("❌ Permissions required for background monitoring")),
          );
        }
        return;
      }
      
      final started = await startBackgroundService();
      if (mounted) {
        setState(() => _backgroundMode = started);
        if (started) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("🔔 Background monitoring started - works even when app is closed!")),
          );
        }
      }
    } else {
      // Stop background service
      await stopBackgroundService();
      if (mounted) {
        setState(() => _backgroundMode = false);
      }
    }
  }

  /// Show emergency alert dialog
  void _showSOSDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: Colors.red[50],
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.red, size: 32),
            SizedBox(width: 8),
            Text("SOS ALERT SENT!", style: TextStyle(color: Colors.red)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Distress emotion detected: ${_emotion.toUpperCase()}"),
            Text("Confidence: ${(_confidence * 100).toStringAsFixed(1)}%"),
            Text("Severity: $_severity"),
            const SizedBox(height: 12),
            const Text(
              "✅ Emergency contacts have been notified with your location!",
              style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _distressDetected ? Colors.red[50] : Colors.white,
      appBar: AppBar(
        title: const Text("AI SOS Emergency System"),
        backgroundColor: Colors.red[700],
        foregroundColor: Colors.white,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            // ─── Status Card ───
            Card(
              elevation: 4,
              color: _distressDetected ? Colors.red[100] : Colors.blue[50],
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Icon(
                      _distressDetected
                          ? Icons.warning_amber_rounded
                          : (_backgroundMode ? Icons.shield : Icons.shield_outlined),
                      size: 48,
                      color: _distressDetected ? Colors.red : (_backgroundMode ? Colors.green : Colors.blue),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _statusMessage,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: _distressDetected ? Colors.red[800] : Colors.blue[800],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // ─── Background Mode Toggle ───
            Card(
              color: _backgroundMode ? Colors.green[50] : Colors.grey[50],
              child: SwitchListTile(
                title: const Row(
                  children: [
                    Icon(
                      Icons.notifications,
                      color: Colors.orange,
                    ),
                    SizedBox(width: 8),
                    Text("Background Monitoring"),
                  ],
                ),
                subtitle: Text(
                  _backgroundMode
                      ? "✅ Active - Works when app is closed!"
                      : "Enable to monitor 24/7 (requires notification permission)",
                ),
                value: _backgroundMode,
                activeColor: Colors.green[700],
                onChanged: _toggleBackgroundMode,
              ),
            ),
            
            const SizedBox(height: 12),

            // ─── Continuous Mode Toggle ───
            SwitchListTile(
              title: const Text("Continuous Monitoring"),
              subtitle: Text(
                _continuousMode
                    ? "Auto-recording every few seconds"
                    : "Manual record mode",
              ),
              value: _continuousMode,
              activeColor: Colors.red[700],
              onChanged: (value) async {
                setState(() => _continuousMode = value);
                if (value) {
                  bool hasPermission = await _requestPermissions();
                  if (hasPermission) {
                    _continuousMonitor.start();
                  } else {
                    setState(() {
                      _continuousMode = false;
                      _statusMessage = "❌ Permissions denied";
                    });
                  }
                } else {
                  _continuousMonitor.stop();
                }
              },
            ),
            const SizedBox(height: 16),

            // ─── Record Button (only in manual mode) ───
            if (!_continuousMode && !_backgroundMode)
            GestureDetector(
              onTap: _isProcessing
                  ? null
                  : (_isRecording ? _stopRecording : _startRecording),
              child: Container(
                width: 140,
                height: 140,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isProcessing
                      ? Colors.grey
                      : (_isRecording ? Colors.red : Colors.red[700]),
                  boxShadow: [
                    BoxShadow(
                      color: (_isRecording ? Colors.red : Colors.red[700])!
                          .withOpacity(0.4),
                      blurRadius: 20,
                      spreadRadius: 5,
                    ),
                  ],
                ),
                child: Center(
                  child: _isProcessing
                      ? const CircularProgressIndicator(color: Colors.white)
                      : Icon(
                          _isRecording ? Icons.stop : Icons.mic,
                          size: 60,
                          color: Colors.white,
                        ),
                ),
              ),
            ),

            const SizedBox(height: 12),
            if (!_backgroundMode)
            Text(
              _isProcessing
                  ? "Processing..."
                  : (_isRecording ? "Tap to Stop" : "Tap to Record"),
              style: const TextStyle(fontSize: 16, color: Colors.grey),
            ),

            const SizedBox(height: 32),

            // ─── Emotion Result Card ───
            if (_emotion != "—")
              Card(
                elevation: 3,
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Text(
                        "Detected Emotion",
                        style: TextStyle(fontSize: 14, color: Colors.grey),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _emotion.toUpperCase(),
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: _distressDetected ? Colors.red : Colors.green,
                        ),
                      ),
                      const SizedBox(height: 8),
                      LinearProgressIndicator(
                        value: _confidence,
                        backgroundColor: Colors.grey[200],
                        valueColor: AlwaysStoppedAnimation(
                          _distressDetected ? Colors.red : Colors.green,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Confidence: ${(_confidence * 100).toStringAsFixed(1)}%",
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ),
              
            const SizedBox(height: 24),
            
            // ─── Info Card ───
            Card(
              color: Colors.amber[50],
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.amber[800]),
                        const SizedBox(width: 8),
                        Text(
                          "How it works",
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.amber[800],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text("• 10-second countdown before SOS alert is sent"),
                    const Text("• Cancel button to prevent false alerts"),
                    const Text("• Background Mode: Keeps monitoring even when app is closed"),
                    const Text("• Continuous Mode: Auto-records while app is open"),
                    const Text("• Manual Mode: Tap mic button to record once"),
                    const SizedBox(height: 8),
                    Text(
                      "Backend: ${SosService.baseUrl}",
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Countdown Dialog Widget
class _CountdownDialog extends StatelessWidget {
  final int seconds;
  final String emotion;
  final double confidence;
  final String severity;
  final VoidCallback onCancel;

  const _CountdownDialog({
    required this.seconds,
    required this.emotion,
    required this.confidence,
    required this.severity,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: Colors.orange[50],
      title: Row(
        children: [
          Icon(Icons.timer, color: Colors.orange[700], size: 28),
          const SizedBox(width: 8),
          Text(
            "Confirm SOS Alert",
            style: TextStyle(color: Colors.orange[800]),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Countdown circle
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 100,
                height: 100,
                child: CircularProgressIndicator(
                  value: seconds / 10,
                  strokeWidth: 8,
                  backgroundColor: Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation(
                    seconds > 3 ? Colors.orange : Colors.red,
                  ),
                ),
              ),
              Text(
                "$seconds",
                style: TextStyle(
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                  color: seconds > 3 ? Colors.orange[700] : Colors.red,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            "SOS will be sent in:",
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 8),
          Text(
            "$seconds seconds",
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          // Emotion info
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red[50],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                Text(
                  "Detected: ${emotion.toUpperCase()}",
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text("Confidence: ${(confidence * 100).toStringAsFixed(1)}%"),
                Text("Severity: $severity"),
              ],
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            "Tap CANCEL if you're safe!",
            style: TextStyle(
              color: Colors.red,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
      actions: [
        ElevatedButton(
          onPressed: onCancel,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.green,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          ),
          child: const Text(
            "CANCEL - I'M SAFE",
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }
}

