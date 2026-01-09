import 'package:equatable/equatable.dart';

/// Command execution result entity
class CommandResult extends Equatable {
  final String command;
  final String output;
  final int? exitCode;
  final DateTime executedAt;
  final Duration? executionTime;
  final bool isError;

  const CommandResult({
    required this.command,
    required this.output,
    this.exitCode,
    required this.executedAt,
    this.executionTime,
    this.isError = false,
  });

  CommandResult copyWith({
    String? command,
    String? output,
    int? exitCode,
    DateTime? executedAt,
    Duration? executionTime,
    bool? isError,
  }) {
    return CommandResult(
      command: command ?? this.command,
      output: output ?? this.output,
      exitCode: exitCode ?? this.exitCode,
      executedAt: executedAt ?? this.executedAt,
      executionTime: executionTime ?? this.executionTime,
      isError: isError ?? this.isError,
    );
  }

  @override
  List<Object?> get props => [
        command,
        output,
        exitCode,
        executedAt,
        executionTime,
        isError,
      ];
}
