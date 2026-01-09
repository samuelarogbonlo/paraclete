import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for disconnecting SSH session
class DisconnectSsh {
  final TerminalRepository _repository;

  DisconnectSsh(this._repository);

  Future<void> call(String sessionId) async {
    return _repository.disconnect(sessionId);
  }
}
