import 'package:flutter/material.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/presentation/providers/terminal_controller.dart';

/// Dialog for adding or editing SSH connections
class AddConnectionDialog extends StatefulWidget {
  final SshConnection? connection;
  final Function(SshConnection) onSave;

  const AddConnectionDialog({
    super.key,
    this.connection,
    required this.onSave,
  });

  @override
  State<AddConnectionDialog> createState() => _AddConnectionDialogState();
}

class _AddConnectionDialogState extends State<AddConnectionDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _hostController;
  late final TextEditingController _portController;
  late final TextEditingController _usernameController;
  late final TextEditingController _passwordController;
  late final TextEditingController _privateKeyController;
  late final TextEditingController _descriptionController;
  late SshAuthMethod _authMethod;

  @override
  void initState() {
    super.initState();
    final conn = widget.connection;

    _nameController = TextEditingController(text: conn?.name ?? '');
    _hostController = TextEditingController(text: conn?.host ?? '');
    _portController = TextEditingController(text: (conn?.port ?? 22).toString());
    _usernameController = TextEditingController(text: conn?.username ?? '');
    _passwordController = TextEditingController(text: conn?.password ?? '');
    _privateKeyController = TextEditingController(text: conn?.privateKey ?? '');
    _descriptionController = TextEditingController(text: conn?.description ?? '');
    _authMethod = conn?.authMethod ?? SshAuthMethod.password;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _hostController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _privateKeyController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final connection = widget.connection != null
        ? widget.connection!.copyWith(
            name: _nameController.text,
            host: _hostController.text,
            port: int.parse(_portController.text),
            username: _usernameController.text,
            authMethod: _authMethod,
            password: _authMethod == SshAuthMethod.password ? _passwordController.text : null,
            privateKey: _authMethod == SshAuthMethod.publicKey ? _privateKeyController.text : null,
            description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
          )
        : createNewConnection(
            name: _nameController.text,
            host: _hostController.text,
            port: int.parse(_portController.text),
            username: _usernameController.text,
            authMethod: _authMethod,
            password: _authMethod == SshAuthMethod.password ? _passwordController.text : null,
            privateKey: _authMethod == SshAuthMethod.publicKey ? _privateKeyController.text : null,
            description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
          );

    widget.onSave(connection);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.connection == null ? 'Add Connection' : 'Edit Connection',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 24),

                // Connection name
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Connection Name',
                    hintText: 'My Server',
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a name';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // Host
                TextFormField(
                  controller: _hostController,
                  decoration: const InputDecoration(
                    labelText: 'Host',
                    hintText: 'example.com or 192.168.1.1',
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a host';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // Port and Username row
                Row(
                  children: [
                    Expanded(
                      flex: 1,
                      child: TextFormField(
                        controller: _portController,
                        decoration: const InputDecoration(
                          labelText: 'Port',
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Required';
                          }
                          final port = int.tryParse(value);
                          if (port == null || port < 1 || port > 65535) {
                            return 'Invalid port';
                          }
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      flex: 2,
                      child: TextFormField(
                        controller: _usernameController,
                        decoration: const InputDecoration(
                          labelText: 'Username',
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter username';
                          }
                          return null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Authentication method
                DropdownButtonFormField<SshAuthMethod>(
                  value: _authMethod,
                  decoration: const InputDecoration(
                    labelText: 'Authentication Method',
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: SshAuthMethod.password,
                      child: Text('Password'),
                    ),
                    DropdownMenuItem(
                      value: SshAuthMethod.publicKey,
                      child: Text('Public Key'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        _authMethod = value;
                      });
                    }
                  },
                ),
                const SizedBox(height: 16),

                // Password or private key based on auth method
                if (_authMethod == SshAuthMethod.password)
                  TextFormField(
                    controller: _passwordController,
                    decoration: const InputDecoration(
                      labelText: 'Password',
                    ),
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter password';
                      }
                      return null;
                    },
                  ),

                if (_authMethod == SshAuthMethod.publicKey)
                  TextFormField(
                    controller: _privateKeyController,
                    decoration: const InputDecoration(
                      labelText: 'Private Key',
                      hintText: 'Paste your private key here',
                    ),
                    maxLines: 5,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter private key';
                      }
                      return null;
                    },
                  ),

                const SizedBox(height: 16),

                // Description
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(
                    labelText: 'Description (optional)',
                    hintText: 'Production server, testing environment, etc.',
                  ),
                  maxLines: 2,
                ),

                const SizedBox(height: 24),

                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: _save,
                      child: Text(widget.connection == null ? 'Add' : 'Save'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
