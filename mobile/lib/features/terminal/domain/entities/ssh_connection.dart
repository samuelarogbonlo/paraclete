import 'package:equatable/equatable.dart';

/// Authentication method for SSH connection
enum SshAuthMethod {
  password,
  publicKey,
  agent,
}

/// SSH connection configuration entity
class SshConnection extends Equatable {
  final String id;
  final String name;
  final String host;
  final int port;
  final String username;
  final SshAuthMethod authMethod;
  final String? password;
  final String? privateKey;
  final String? privateKeyPassphrase;
  final DateTime createdAt;
  final DateTime? lastUsedAt;
  final Map<String, String>? environment;
  final bool autoReconnect;
  final int reconnectDelay;
  final String? description;

  const SshConnection({
    required this.id,
    required this.name,
    required this.host,
    this.port = 22,
    required this.username,
    required this.authMethod,
    this.password,
    this.privateKey,
    this.privateKeyPassphrase,
    required this.createdAt,
    this.lastUsedAt,
    this.environment,
    this.autoReconnect = true,
    this.reconnectDelay = 1000,
    this.description,
  });

  SshConnection copyWith({
    String? id,
    String? name,
    String? host,
    int? port,
    String? username,
    SshAuthMethod? authMethod,
    String? password,
    String? privateKey,
    String? privateKeyPassphrase,
    DateTime? createdAt,
    DateTime? lastUsedAt,
    Map<String, String>? environment,
    bool? autoReconnect,
    int? reconnectDelay,
    String? description,
  }) {
    return SshConnection(
      id: id ?? this.id,
      name: name ?? this.name,
      host: host ?? this.host,
      port: port ?? this.port,
      username: username ?? this.username,
      authMethod: authMethod ?? this.authMethod,
      password: password ?? this.password,
      privateKey: privateKey ?? this.privateKey,
      privateKeyPassphrase: privateKeyPassphrase ?? this.privateKeyPassphrase,
      createdAt: createdAt ?? this.createdAt,
      lastUsedAt: lastUsedAt ?? this.lastUsedAt,
      environment: environment ?? this.environment,
      autoReconnect: autoReconnect ?? this.autoReconnect,
      reconnectDelay: reconnectDelay ?? this.reconnectDelay,
      description: description ?? this.description,
    );
  }

  @override
  List<Object?> get props => [
        id,
        name,
        host,
        port,
        username,
        authMethod,
        password,
        privateKey,
        privateKeyPassphrase,
        createdAt,
        lastUsedAt,
        environment,
        autoReconnect,
        reconnectDelay,
        description,
      ];

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'host': host,
      'port': port,
      'username': username,
      'auth_method': authMethod.name,
      'password': password,
      'private_key': privateKey,
      'private_key_passphrase': privateKeyPassphrase,
      'created_at': createdAt.toIso8601String(),
      'last_used_at': lastUsedAt?.toIso8601String(),
      'environment': environment,
      'auto_reconnect': autoReconnect,
      'reconnect_delay': reconnectDelay,
      'description': description,
    };
  }

  factory SshConnection.fromJson(Map<String, dynamic> json) {
    return SshConnection(
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
}
