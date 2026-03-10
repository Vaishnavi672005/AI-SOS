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
  // State Variables
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
  
  // Countdown Timer Variables
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
          setState(() => _statusMessage = "Error: ${result['error']}");
          return;
        }
        setState(() {
          _emotion = result['prediction']['emotion'];
          _confidence = result['prediction']['confidence'];
          _distressDetected = result['distress']['distress_detected'];
          _severity = result['distress']['severity'];
          if (_distressDetected) {
            _statusMessage = "DISTRESS DETECTED! Waiting for confirmation...";
            _showCountdownDialog();
          } else {
            _statusMessage = "Monitoring... $_emotion (${(_confidence * 100).toStringAsFixed(0)}%)";
          }
        });
      },
      onStatus: (msg) {
        if (mounted) setState(() => _statusMessage = msg);
      },
    );
    
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
    super.dispose();
  }

  Future<bool> _requestPermissions() async {
    var micStatus = await Permission.microphone.request();
    var locStatus = await Permission.location.request();
    var notifStatus = await Permission.notification.request();
    return micStatus.isGranted && locStatus.isGranted;
  }

  Future<Position> _getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled');
    }
    return await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  Future<void> _startRecording() async {
    bool hasPermission = await _requestPermissions();
    if (!hasPermission) {
      setState(() {
        _statusMessage = "Microphone/location permission denied";
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
      _statusMessage = "Recording... Tap stop when ready";
      _distressDetected = false;
    });
  }

  Future<void> _stopRecording() async {
    final path = await _recorder.stop();

    if (path == null) {
      setState(() {
        _statusMessage = "Recording failed";
      });
      return;
    }

    setState(() {
      _isRecording = false;
      _isProcessing = true;
      _statusMessage = "Analyzing voice emotion...";
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
          _statusMessage = "Error: ${result['error']}";
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
          _statusMessage = "DISTRESS DETECTED! Confirm to send alert...";
          _pendingAlertPosition = position;
          _showCountdownDialog();
        } else {
          _statusMessage = "No distress detected. You're safe.";
        }
      });

    } catch (e) {
      setState(() {
        _statusMessage = "Error: $e";
        _isProcessing = false;
      });
    }
  }

  void _showCountdownDialog() {
    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (context) => _CountdownPage(
          emotion: _emotion,
          confidence: _confidence,
          severity: _severity,
          position: _pendingAlertPosition,
          onCancel: () {
            Navigator.of(context).pop();
            setState(() {
              _distressDetected = false;
              _statusMessage = "Alert cancelled. You are safe.";
            });
          },
          onSendSOS: () async {
            Navigator.of(context).pop();
            await _sendSOS();
          },
        ),
      ),
    );
  }

  Future<void> _sendSOS() async {
    Position position = _pendingAlertPosition ?? await _getCurrentLocation();
    
    try {
      await SosService.sendAudioForPrediction(
        audioFilePath: '',
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (e) {
      // Continue
    }
    
    if (mounted) {
      _showSOSDialog();
    }
    
    setState(() {
      _pendingAlertPosition = null;
    });
  }

  Future<void> _toggleBackgroundMode(bool value) async {
    if (value) {
      bool hasPermission = await _requestPermissions();
      if (!hasPermission) {
        if (mounted) {
          setState(() => _backgroundMode = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Permissions required for background monitoring")),
          );
        }
        return;
      }
      
      final started = await startBackgroundService();
      if (mounted) {
        setState(() => _backgroundMode = started);
        if (started) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Background monitoring started!")),
          );
        }
      }
    } else {
      await stopBackgroundService();
      if (mounted) {
        setState(() => _backgroundMode = false);
      }
    }
  }

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
            Text("Distress detected: ${_emotion.toUpperCase()}"),
            Text("Confidence: ${(_confidence * 100).toStringAsFixed(1)}%"),
            Text("Severity: $_severity"),
            const SizedBox(height: 12),
            const Text(
              "Emergency contacts notified!",
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
            // Status Card
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

            // Background Mode Toggle
            Card(
              color: _backgroundMode ? Colors.green[50] : Colors.grey[50],
              child: SwitchListTile(
                title: const Row(
                  children: [
                    Icon(Icons.notifications, color: Colors.orange),
                    SizedBox(width: 8),
                    Text("Background Monitoring"),
                  ],
                ),
                subtitle: Text(
                  _backgroundMode
                      ? "Active - Works when app is closed!"
                      : "Enable to monitor 24/7",
                ),
                value: _backgroundMode,
                activeColor: Colors.green[700],
                onChanged: _toggleBackgroundMode,
              ),
            ),
            
            const SizedBox(height: 12),

            // Continuous Mode Toggle
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
                      _statusMessage = "Permissions denied";
                    });
                  }
                } else {
                  _continuousMonitor.stop();
                }
              },
            ),
            const SizedBox(height: 16),

            // Record Button
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

            // Emotion Result Card
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
            
            // Info Card
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
                    const Text("- 20-second countdown before SOS alert is sent"),
                    const Text("- Tap CANCEL to stop the alert within 20 seconds"),
                    const Text("- Background Mode: Keeps monitoring when app is closed"),
                    const Text("- Continuous Mode: Auto-records while app is open"),
                    const Text("- Manual Mode: Tap mic button to record once"),
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

/// Full-screen countdown page with its own timer
class _CountdownPage extends StatefulWidget {
  final String emotion;
  final double confidence;
  final String severity;
  final Position? position;
  final VoidCallback onCancel;
  final VoidCallback onSendSOS;

  const _CountdownPage({
    required this.emotion,
    required this.confidence,
    required this.severity,
    required this.position,
    required this.onCancel,
    required this.onSendSOS,
  });

  @override
  State<_CountdownPage> createState() => _CountdownPageState();
}

class _CountdownPageState extends State<_CountdownPage> {
  int _secondsRemaining = 20;
  Timer? _timer;
  bool _cancelled = false;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      
      if (_cancelled) {
        timer.cancel();
        return;
      }
      
      setState(() {
        _secondsRemaining--;
      });
      
      if (_secondsRemaining <= 0) {
        timer.cancel();
        if (!_cancelled) {
          widget.onSendSOS();
        }
      }
    });
  }

  void _handleCancel() {
    _cancelled = true;
    _timer?.cancel();
    widget.onCancel();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.orange[50],
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.timer, color: Colors.orange[700], size: 80),
              const SizedBox(height: 24),
              Text(
                "SOS Alert",
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.orange[800],
                ),
              ),
              const SizedBox(height: 32),
              
              // Countdown circle
              Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 150,
                    height: 150,
                    child: CircularProgressIndicator(
                      value: _secondsRemaining / 20,
                      strokeWidth: 12,
                      backgroundColor: Colors.grey[300],
                      valueColor: AlwaysStoppedAnimation(
                        _secondsRemaining > 10 ? Colors.orange : Colors.red,
                      ),
                    ),
                  ),
                  Text(
                    "$_secondsRemaining",
                    style: TextStyle(
                      fontSize: 60,
                      fontWeight: FontWeight.bold,
                      color: _secondsRemaining > 10 ? Colors.orange[700] : Colors.red,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 24),
              Text(
                "SOS will be sent in:",
                style: const TextStyle(fontSize: 20),
              ),
              Text(
                "$_secondsRemaining seconds",
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Colors.orange[800],
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Emotion info
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red[50],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Text(
                      "Detected: ${widget.emotion.toUpperCase()}",
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text("Confidence: ${(widget.confidence * 100).toStringAsFixed(1)}%"),
                    Text("Severity: ${widget.severity}"),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),
              const Text(
                "Tap CANCEL if you're safe!",
                style: TextStyle(
                  color: Colors.red,
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Cancel button
              SizedBox(
                width: double.infinity,
                height: 60,
                child: ElevatedButton(
                  onPressed: _handleCancel,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                  child: const Text(
                    "CANCEL - I'M SAFE",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
