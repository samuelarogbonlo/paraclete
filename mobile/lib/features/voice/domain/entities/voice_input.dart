import 'package:equatable/equatable.dart';

/// Represents voice input from the user
class VoiceInput extends Equatable {
  final String id;
  final List<int> audioData;
  final String encoding;
  final int sampleRate;
  final int channels;
  final DateTime timestamp;
  final Duration duration;

  const VoiceInput({
    required this.id,
    required this.audioData,
    this.encoding = 'linear16',
    this.sampleRate = 16000,
    this.channels = 1,
    required this.timestamp,
    required this.duration,
  });

  VoiceInput copyWith({
    String? id,
    List<int>? audioData,
    String? encoding,
    int? sampleRate,
    int? channels,
    DateTime? timestamp,
    Duration? duration,
  }) {
    return VoiceInput(
      id: id ?? this.id,
      audioData: audioData ?? this.audioData,
      encoding: encoding ?? this.encoding,
      sampleRate: sampleRate ?? this.sampleRate,
      channels: channels ?? this.channels,
      timestamp: timestamp ?? this.timestamp,
      duration: duration ?? this.duration,
    );
  }

  @override
  List<Object?> get props => [
        id,
        audioData,
        encoding,
        sampleRate,
        channels,
        timestamp,
        duration,
      ];

  @override
  String toString() {
    return 'VoiceInput(id: $id, duration: $duration, sampleRate: $sampleRate)';
  }
}
