import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';

/// Data model for SSH connection (extends entity for data layer operations)
class SshConnectionModel extends SshConnection {
  const SshConnectionModel({
    required super.id,
    required super.name,
    required super.host,
    super.port,
    required super.username,
    required super.authMethod,
    super.password,
    super.privateKey,
    super.privateKeyPassphrase,
    required super.createdAt,
    super.lastUsedAt,
    super.environment,
    super.autoReconnect,
    super.reconnectDelay,
    super.description,
  });

  factory SshConnectionModel.fromEntity(SshConnection entity) {
    return SshConnectionModel(
      id: entity.id,
      name: entity.name,
      host: entity.host,
      port: entity.port,
      username: entity.username,
      authMethod: entity.authMethod,
      password: entity.password,
      privateKey: entity.privateKey,
      privateKeyPassphrase: entity.privateKeyPassphrase,
      createdAt: entity.createdAt,
      lastUsedAt: entity.lastUsedAt,
      environment: entity.environment,
      autoReconnect: entity.autoReconnect,
      reconnectDelay: entity.reconnectDelay,
      description: entity.description,
    );
  }

  factory SshConnectionModel.fromJson(Map<String, dynamic> json) {
    return SshConnectionModel(
      id: json['id'] as String,
      name: json['name'] as String,
      host: json['host'] as String,
      port: json['port'] as int? ?? 22,
      username: json['username'] as String,
      authMethod: SshAuthMethod.values.firstWhere(
        (e) => e.name == json['auth_method'],
        orElse: () => SshAuthMethod.password,
      ),
      password: json['password'] as String?,
      privateKey: json['private_key'] as String?,
      privateKeyPassphrase: json['private_key_passphrase'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUsedAt: json['last_used_at'] != null
          ? DateTime.parse(json['last_used_at'] as String)
          : null,
      environment: json['environment'] != null
          ? Map<String, String>.from(json['environment'] as Map)
          : null,
      autoReconnect: json['auto_reconnect'] as bool? ?? true,
      reconnectDelay: json['reconnect_delay'] as int? ?? 1000,
      description: json['description'] as String?,
    );
  }

  SshConnection toEntity() => this;
}
