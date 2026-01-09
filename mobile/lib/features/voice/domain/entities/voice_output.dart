import 'package:equatable/equatable.dart';

/// Represents voice output (TTS) from the system
class VoiceOutput extends Equatable {
  final String id;
  final String text;
  final List<int> audioData;
  final String voiceId;
  final DateTime timestamp;
  final Duration duration;
  final VoiceOutputStatus status;

  const VoiceOutput({
    required this.id,
    required this.text,
    required this.audioData,
    required this.voiceId,
    required this.timestamp,
    required this.duration,
    this.status = VoiceOutputStatus.pending,
  });

  VoiceOutput copyWith({
    String? id,
    String? text,
    List<int>? audioData,
    String? voiceId,
    DateTime? timestamp,
    Duration? duration,
    VoiceOutputStatus? status,
  }) {
    return VoiceOutput(
      id: id ?? this.id,
      text: text ?? this.text,
      audioData: audioData ?? this.audioData,
      voiceId: voiceId ?? this.voiceId,
      timestamp: timestamp ?? this.timestamp,
      duration: duration ?? this.duration,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [
        id,
        text,
        audioData,
        voiceId,
        timestamp,
        duration,
        status,
      ];

  @override
  String toString() {
    return 'VoiceOutput(id: $id, text: $text, status: $status)';
  }
}

/// Status of voice output playback
enum VoiceOutputStatus {
  pending,
  playing,
  paused,
  completed,
  error,
}
