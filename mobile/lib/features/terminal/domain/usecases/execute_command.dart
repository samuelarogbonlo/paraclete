import 'package:paraclete/features/terminal/domain/entities/command_result.dart';
import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for executing a command on SSH session
class ExecuteCommand {
  final TerminalRepository _repository;

  ExecuteCommand(this._repository);

  Future<CommandResult> call(String sessionId, String command) async {
    return _repository.executeCommand(sessionId, command);
  }
}
