import 'package:equatable/equatable.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';

/// Represents the overall state of voice interactions
class VoiceState extends Equatable {
  final VoiceStatus status;
  final TranscriptionResult? currentTranscription;
  final List<TranscriptionResult> transcriptionHistory;
  final VoiceOutput? currentOutput;
  final List<VoiceOutput> outputHistory;
  final double audioLevel;
  final String? error;
  final bool isRecording;
  final bool isPlaying;
  final Duration? recordingDuration;

  const VoiceState({
    this.status = VoiceStatus.idle,
    this.currentTranscription,
    this.transcriptionHistory = const [],
    this.currentOutput,
    this.outputHistory = const [],
    this.audioLevel = 0.0,
    this.error,
    this.isRecording = false,
    this.isPlaying = false,
    this.recordingDuration,
  });

  VoiceState copyWith({
    VoiceStatus? status,
    TranscriptionResult? currentTranscription,
    List<TranscriptionResult>? transcriptionHistory,
    VoiceOutput? currentOutput,
    List<VoiceOutput>? outputHistory,
    double? audioLevel,
    String? error,
    bool? isRecording,
    bool? isPlaying,
    Duration? recordingDuration,
  }) {
    return VoiceState(
      status: status ?? this.status,
      currentTranscription: currentTranscription ?? this.currentTranscription,
      transcriptionHistory: transcriptionHistory ?? this.transcriptionHistory,
      currentOutput: currentOutput ?? this.currentOutput,
      outputHistory: outputHistory ?? this.outputHistory,
      audioLevel: audioLevel ?? this.audioLevel,
      error: error,
      isRecording: isRecording ?? this.isRecording,
      isPlaying: isPlaying ?? this.isPlaying,
      recordingDuration: recordingDuration ?? this.recordingDuration,
    );
  }

  String get fullTranscript {
    if (transcriptionHistory.isEmpty) return '';
    return transcriptionHistory
        .where((t) => t.isFinal)
        .map((t) => t.text)
        .join(' ');
  }

  String get interimTranscript {
    return currentTranscription?.text ?? '';
  }

  @override
  List<Object?> get props => [
        status,
        currentTranscription,
        transcriptionHistory,
        currentOutput,
        outputHistory,
        audioLevel,
        error,
        isRecording,
        isPlaying,
        recordingDuration,
      ];

  @override
  String toString() {
    return 'VoiceState(status: $status, isRecording: $isRecording, isPlaying: $isPlaying)';
  }
}

/// Status of voice system
enum VoiceStatus {
  idle,
  initializing,
  recording,
  processing,
  speaking,
  error,
}
