import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Use case for managing saved SSH connections
class ManageSavedConnections {
  final TerminalRepository _repository;

  ManageSavedConnections(this._repository);

  Future<List<SshConnection>> getSavedConnections() async {
    return _repository.getSavedConnections();
  }

  Future<SshConnection?> getSavedConnection(String id) async {
    return _repository.getSavedConnection(id);
  }

  Future<void> saveConnection(SshConnection connection) async {
    return _repository.saveConnection(connection);
  }

  Future<void> updateConnection(SshConnection connection) async {
    return _repository.updateConnection(connection);
  }

  Future<void> deleteConnection(String id) async {
    return _repository.deleteConnection(id);
  }
}
