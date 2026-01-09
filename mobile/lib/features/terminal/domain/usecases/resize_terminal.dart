import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for resizing terminal
class ResizeTerminal {
  final TerminalRepository _repository;

  ResizeTerminal(this._repository);

  Future<void> call(String sessionId, int width, int height) async {
    return _repository.resizeTerminal(sessionId, width, height);
  }
}
