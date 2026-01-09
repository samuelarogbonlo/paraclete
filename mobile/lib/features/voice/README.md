# Voice Module - Paraclete Mobile

Complete voice input and output implementation for Paraclete mobile app with real-time STT and TTS.

## Overview

The voice module provides a comprehensive voice interaction system with:
- Real-time Speech-to-Text (STT) via Deepgram WebSocket streaming
- Text-to-Speech (TTS) via ElevenLabs streaming API
- Hold-to-record UI pattern with visual feedback
- Real-time waveform visualization
- Transcript display with interim and final results
- TTS playback controls

## Architecture

### Clean Architecture Layers

```
lib/features/voice/
├── data/                          # Data Layer
│   ├── datasources/
│   │   ├── deepgram_datasource.dart     # WebSocket streaming STT
│   │   └── elevenlabs_datasource.dart   # HTTP streaming TTS
│   └── repositories/
│       └── voice_repository_impl.dart   # Repository implementation
├── domain/                        # Domain Layer
│   ├── entities/
│   │   ├── transcription_result.dart    # STT result entity
│   │   ├── voice_input.dart             # Voice input entity
│   │   ├── voice_output.dart            # TTS output entity
│   │   └── voice_state.dart             # Overall voice state
│   ├── repositories/
│   │   └── voice_repository.dart        # Repository interface
│   └── services/
│       └── voice_service.dart           # Voice orchestration service
└── presentation/                  # Presentation Layer
    ├── providers/
    │   └── voice_provider.dart          # Riverpod state management
    ├── screens/
    │   └── voice_input_screen.dart      # Main voice UI screen
    └── widgets/
        ├── hold_to_record_button.dart   # Hold-to-record button
        ├── transcript_display.dart      # Transcript display
        ├── tts_controls.dart            # TTS playback controls
        └── waveform_visualizer.dart     # Audio waveform visualization
```

## Key Features

### 1. Real-Time Speech-to-Text
- **Deepgram Nova-2 Model**: Industry-leading accuracy for technical speech
- **WebSocket Streaming**: Real-time transcription with <2 second latency
- **Interim Results**: Shows in-progress transcription (italic, lighter color)
- **Final Results**: Confirmed transcription (normal weight, full color)
- **Auto-Reconnection**: Exponential backoff (1s → 30s max, 5 retries)
- **Audio Configuration**: PCM 16-bit, 16kHz, mono (verified pattern)

### 2. Text-to-Speech
- **ElevenLabs Turbo v2**: Low-latency, natural-sounding voice synthesis
- **Streaming Playback**: Audio chunks streamed for faster response
- **Voice Selection**: Support for multiple voice IDs
- **Playback Controls**: Play, pause, stop, resume

### 3. User Interface
- **Hold-to-Record Button**: 
  - Scale animation on press
  - Pulse effect while recording
  - Haptic feedback (medium on press, light on release)
  - Color change (primary → error while recording)
  
- **Waveform Visualizer**:
  - 30 animated bars
  - Real-time audio level response
  - Smooth transitions
  - Fades out when not recording

- **Transcript Display**:
  - Auto-scroll as new text appears
  - Visual distinction between interim and final
  - Clear button to reset
  - Error state handling

- **TTS Controls**:
  - Status badge (pending, playing, paused, completed, error)
  - Play/pause/stop buttons
  - Text preview of what's being spoken

## Usage

### 1. Configure API Keys

Users must configure API keys in Settings:

```dart
final secureStorage = SecureStorageService();
await secureStorage.storeApiKey(
  SecureStorageKey.deepgramKey, 
  'YOUR_DEEPGRAM_API_KEY',
);
await secureStorage.storeApiKey(
  SecureStorageKey.elevenLabsKey,
  'YOUR_ELEVENLABS_API_KEY',
);
```

### 2. Navigate to Voice Screen

```dart
Navigator.push(
  context,
  MaterialPageRoute(builder: (context) => VoiceInputScreen()),
);
```

### 3. Recording Voice

```dart
// Start recording (triggered by hold-to-record button)
ref.read(voiceNotifierProvider.notifier).startRecording();

// Stop recording (triggered by button release)
ref.read(voiceNotifierProvider.notifier).stopRecording();
```

### 4. Playing TTS

```dart
// Synthesize and play text
ref.read(voiceNotifierProvider.notifier).speakText('Hello world');

// Control playback
ref.read(voiceNotifierProvider.notifier).pausePlayback();
ref.read(voiceNotifierProvider.notifier).resumePlayback();
ref.read(voiceNotifierProvider.notifier).stopPlayback();
```

### 5. Accessing State

```dart
// Watch voice state
final voiceState = ref.watch(voiceStateProvider);

// Check if recording
final isRecording = ref.watch(isRecordingProvider);

// Check if playing
final isPlaying = ref.watch(isPlayingProvider);

// Get full transcript
final transcript = ref.watch(fullTranscriptProvider);

// Get interim transcript
final interim = ref.watch(interimTranscriptProvider);
```

## Integration Points

### Core Dependencies
- **core_network**: Uses DioClient for HTTP requests (ElevenLabs)
- **core_storage**: Uses SecureStorageService for API key retrieval
- **core_theme**: Uses AppTheme colors for consistent styling
- **core_utils**: Uses AppLogger for debugging and error tracking

### State Management
- **Riverpod 3.0**: StateNotifierProvider for voice state
- **AsyncValue**: Handles loading, data, and error states
- **StreamController**: Manages real-time state updates

### Audio Packages
- **deepgram_speech_to_text ^2.3.0**: Real-time STT
- **record ^5.0.0**: Audio recording from microphone
- **audioplayers ^5.2.0**: Audio playback for TTS
- **dio ^5.4.0**: HTTP client for ElevenLabs API

## Permissions

### iOS (Info.plist)
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Paraclete needs microphone access for voice commands and speech-to-text transcription</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>Paraclete needs speech recognition to transcribe your voice commands</string>
```

### Android (AndroidManifest.xml)
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
```

## Audio Configuration

**Critical**: These values MUST NOT be changed as they are verified to work with Deepgram:

```dart
static const int sampleRate = 16000;  // 16kHz
static const int bitDepth = 16;       // 16-bit
static const int channels = 1;        // Mono
static const String encoding = 'linear16';  // PCM
```

## Error Handling

### Common Errors

1. **API Key Missing**
   - Dialog prompts user to configure keys in Settings
   - Prevents recording/TTS until keys are set

2. **Microphone Permission Denied**
   - DeepgramDatasource checks permission before starting
   - Emits error if permission not granted

3. **Network Errors**
   - Auto-reconnection with exponential backoff
   - User-friendly error messages in UI

4. **WebSocket Disconnection**
   - Automatic retry up to 5 times
   - Delays: 1s, 2s, 4s, 8s, 16s, 30s (max)

## Performance

### Target Metrics
- **Transcription Latency**: < 2 seconds from speech to display
- **Audio Quality**: PCM 16-bit, 16kHz maintains clarity
- **Memory Efficiency**: Streaming prevents large buffer accumulation
- **Battery Optimization**: Resources released when not in use

### Optimization Techniques
- Audio streamed directly without intermediate buffering
- WebSocket connection reused for multiple recordings
- Waveform animation uses efficient AnimationController
- State updates throttled to prevent UI jank

## Testing

### Manual Testing Checklist
- [ ] Hold button starts recording (visual feedback)
- [ ] Release button stops recording
- [ ] Interim transcript appears (italic, lighter)
- [ ] Final transcript appears (normal, darker)
- [ ] Waveform animates during recording
- [ ] Recording duration displays
- [ ] TTS plays transcript correctly
- [ ] Pause/resume TTS works
- [ ] Error states display properly
- [ ] API key dialog shows when keys missing
- [ ] Permissions requested on first use

### Integration Testing
```dart
// Test voice flow
await tester.pumpWidget(ProviderScope(child: VoiceInputScreen()));
await tester.longPress(find.byType(HoldToRecordButton));
await tester.pumpAndSettle();
expect(find.text('Recording'), findsOneWidget);
```

## Future Enhancements

### Phase 2
- [ ] Real audio level calculation (currently simulated)
- [ ] Custom voice selection UI
- [ ] Transcript history persistence
- [ ] Voice command shortcuts
- [ ] Multi-language support

### Phase 3
- [ ] Background recording with push notifications
- [ ] Offline transcription caching
- [ ] Voice activity detection (VAD)
- [ ] Noise cancellation
- [ ] Speaker diarization

## Troubleshooting

### Recording doesn't start
1. Check API keys configured
2. Verify microphone permission granted
3. Check Deepgram API quota
4. Review logs for WebSocket errors

### Poor transcription quality
1. Ensure quiet environment
2. Speak clearly into microphone
3. Check audio configuration (16kHz, mono)
4. Verify Deepgram model (nova-2-general)

### TTS playback issues
1. Check ElevenLabs API key
2. Verify internet connection
3. Check audio output device
4. Review audioplayers logs

## API Costs

### Deepgram (STT)
- Nova-2 Model: $0.0043/minute
- Example: 1000 minutes/month = $4.30

### ElevenLabs (TTS)
- Turbo v2 Model: ~$0.18/1000 characters
- Example: 50,000 characters/month = $9

## References

- [Deepgram Docs](https://developers.deepgram.com/)
- [ElevenLabs API](https://docs.elevenlabs.io/)
- [Riverpod Docs](https://riverpod.dev/)
- [Flutter Audio](https://docs.flutter.dev/cookbook/plugins/play-audio)

---

**Built for Wave 2 - Paraclete Mobile Foundation**
