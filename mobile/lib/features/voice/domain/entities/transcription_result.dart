import 'package:equatable/equatable.dart';

/// Represents a transcription result from STT service
class TranscriptionResult extends Equatable {
  final String text;
  final bool isFinal;
  final double confidence;
  final DateTime timestamp;
  final Duration? duration;

  const TranscriptionResult({
    required this.text,
    required this.isFinal,
    this.confidence = 0.0,
    required this.timestamp,
    this.duration,
  });

  TranscriptionResult copyWith({
    String? text,
    bool? isFinal,
    double? confidence,
    DateTime? timestamp,
    Duration? duration,
  }) {
    return TranscriptionResult(
      text: text ?? this.text,
      isFinal: isFinal ?? this.isFinal,
      confidence: confidence ?? this.confidence,
      timestamp: timestamp ?? this.timestamp,
      duration: duration ?? this.duration,
    );
  }

  @override
  List<Object?> get props => [text, isFinal, confidence, timestamp, duration];

  @override
  String toString() {
    return 'TranscriptionResult(text: $text, isFinal: $isFinal, confidence: $confidence)';
  }
}
