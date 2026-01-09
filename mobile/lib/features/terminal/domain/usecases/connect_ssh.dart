import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';
import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for establishing SSH connection
class ConnectSsh {
  final TerminalRepository _repository;

  ConnectSsh(this._repository);

  Future<TerminalSession> call(SshConnection connection) async {
    return _repository.connect(connection);
  }
}
