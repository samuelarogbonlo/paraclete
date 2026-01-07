/// Input validation utilities
class Validators {
  Validators._();

  /// Validate email address
  static String? email(String? value) {
    if (value == null || value.isEmpty) {
      return 'Email is required';
    }

    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );

    if (!emailRegex.hasMatch(value)) {
      return 'Please enter a valid email address';
    }

    return null;
  }

  /// Validate password
  static String? password(String? value) {
    if (value == null || value.isEmpty) {
      return 'Password is required';
    }

    if (value.length < 8) {
      return 'Password must be at least 8 characters long';
    }

    if (!RegExp(r'[A-Z]').hasMatch(value)) {
      return 'Password must contain at least one uppercase letter';
    }

    if (!RegExp(r'[a-z]').hasMatch(value)) {
      return 'Password must contain at least one lowercase letter';
    }

    if (!RegExp(r'[0-9]').hasMatch(value)) {
      return 'Password must contain at least one number';
    }

    return null;
  }

  /// Validate password confirmation
  static String? confirmPassword(String? value, String password) {
    if (value == null || value.isEmpty) {
      return 'Please confirm your password';
    }

    if (value != password) {
      return 'Passwords do not match';
    }

    return null;
  }

  /// Validate required field
  static String? required(String? value, {String fieldName = 'This field'}) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName is required';
    }
    return null;
  }

  /// Validate minimum length
  static String? minLength(
    String? value,
    int minLength, {
    String fieldName = 'This field',
  }) {
    if (value == null || value.isEmpty) {
      return '$fieldName is required';
    }

    if (value.length < minLength) {
      return '$fieldName must be at least $minLength characters';
    }

    return null;
  }

  /// Validate maximum length
  static String? maxLength(
    String? value,
    int maxLength, {
    String fieldName = 'This field',
  }) {
    if (value == null || value.isEmpty) {
      return null; // Max length is only checked if there's a value
    }

    if (value.length > maxLength) {
      return '$fieldName must not exceed $maxLength characters';
    }

    return null;
  }

  /// Validate phone number
  static String? phoneNumber(String? value) {
    if (value == null || value.isEmpty) {
      return 'Phone number is required';
    }

    // Remove all non-digit characters
    final digitsOnly = value.replaceAll(RegExp(r'[^\d+]'), '');

    // Check if it's a valid phone number format
    if (!RegExp(r'^\+?[1-9]\d{1,14}$').hasMatch(digitsOnly)) {
      return 'Please enter a valid phone number';
    }

    return null;
  }

  /// Validate URL
  static String? url(String? value) {
    if (value == null || value.isEmpty) {
      return 'URL is required';
    }

    final urlRegex = RegExp(
      r'^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$',
      caseSensitive: false,
    );

    if (!urlRegex.hasMatch(value)) {
      return 'Please enter a valid URL';
    }

    return null;
  }

  /// Validate GitHub repository URL
  static String? githubRepo(String? value) {
    if (value == null || value.isEmpty) {
      return 'Repository URL is required';
    }

    final githubRegex = RegExp(
      r'^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w-]+\/?$',
      caseSensitive: false,
    );

    if (!githubRegex.hasMatch(value)) {
      return 'Please enter a valid GitHub repository URL';
    }

    return null;
  }

  /// Validate API key
  static String? apiKey(String? value, {String provider = 'API'}) {
    if (value == null || value.isEmpty) {
      return '$provider key is required';
    }

    // Basic validation - adjust patterns per provider
    switch (provider.toLowerCase()) {
      case 'anthropic':
        if (!value.startsWith('sk-ant-')) {
          return 'Invalid Anthropic API key format';
        }
        break;
      case 'openai':
        if (!value.startsWith('sk-')) {
          return 'Invalid OpenAI API key format';
        }
        break;
      case 'github':
        if (!RegExp(r'^(ghp_|github_pat_)').hasMatch(value)) {
          return 'Invalid GitHub token format';
        }
        break;
      default:
        if (value.length < 20) {
          return '$provider key seems too short';
        }
    }

    return null;
  }

  /// Validate number
  static String? number(String? value, {String fieldName = 'This field'}) {
    if (value == null || value.isEmpty) {
      return '$fieldName is required';
    }

    if (double.tryParse(value) == null) {
      return '$fieldName must be a valid number';
    }

    return null;
  }

  /// Validate integer
  static String? integer(String? value, {String fieldName = 'This field'}) {
    if (value == null || value.isEmpty) {
      return '$fieldName is required';
    }

    if (int.tryParse(value) == null) {
      return '$fieldName must be a whole number';
    }

    return null;
  }

  /// Validate range
  static String? range(
    String? value, {
    double? min,
    double? max,
    String fieldName = 'Value',
  }) {
    if (value == null || value.isEmpty) {
      return '$fieldName is required';
    }

    final number = double.tryParse(value);
    if (number == null) {
      return '$fieldName must be a valid number';
    }

    if (min != null && number < min) {
      return '$fieldName must be at least $min';
    }

    if (max != null && number > max) {
      return '$fieldName must not exceed $max';
    }

    return null;
  }

  /// Validate branch name
  static String? branchName(String? value) {
    if (value == null || value.isEmpty) {
      return 'Branch name is required';
    }

    // Git branch name rules
    if (!RegExp(r'^[a-zA-Z0-9/_-]+$').hasMatch(value)) {
      return 'Branch name can only contain letters, numbers, /, -, and _';
    }

    if (value.startsWith('/') || value.endsWith('/')) {
      return 'Branch name cannot start or end with /';
    }

    if (value.contains('..') || value.contains('//')) {
      return 'Branch name cannot contain .. or //';
    }

    return null;
  }

  /// Validate session name
  static String? sessionName(String? value) {
    if (value == null || value.isEmpty) {
      return 'Session name is required';
    }

    if (value.length < 3) {
      return 'Session name must be at least 3 characters';
    }

    if (value.length > 50) {
      return 'Session name must not exceed 50 characters';
    }

    if (!RegExp(r'^[a-zA-Z0-9\s_-]+$').hasMatch(value)) {
      return 'Session name can only contain letters, numbers, spaces, -, and _';
    }

    return null;
  }

  /// Validate file path
  static String? filePath(String? value) {
    if (value == null || value.isEmpty) {
      return 'File path is required';
    }

    // Basic file path validation
    if (value.contains('\0')) {
      return 'Invalid file path';
    }

    // Check for dangerous patterns
    if (value.contains('../') || value.contains('..\\')) {
      return 'File path cannot contain directory traversal';
    }

    return null;
  }

  /// Combine multiple validators
  static String? Function(String?) combine(
    List<String? Function(String?)> validators,
  ) {
    return (String? value) {
      for (final validator in validators) {
        final result = validator(value);
        if (result != null) {
          return result;
        }
      }
      return null;
    };
  }
}