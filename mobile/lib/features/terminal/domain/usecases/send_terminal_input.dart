import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for sending input to terminal
class SendTerminalInput {
  final TerminalRepository _repository;

  SendTerminalInput(this._repository);

  Future<void> call(String sessionId, String data) async {
    return _repository.sendInput(sessionId, data);
  }
}
