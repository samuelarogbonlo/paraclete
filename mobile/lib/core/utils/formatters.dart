import 'package:intl/intl.dart';

/// Text formatting utilities
class Formatters {
  Formatters._();

  /// Format file size
  static String fileSize(int bytes) {
    if (bytes < 1024) {
      return '$bytes B';
    } else if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    } else if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    } else {
      return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
    }
  }

  /// Format duration
  static String duration(Duration duration) {
    if (duration.inDays > 0) {
      return '${duration.inDays}d ${duration.inHours.remainder(24)}h';
    } else if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes.remainder(60)}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds.remainder(60)}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }

  /// Format currency
  static String currency(
    double amount, {
    String symbol = '\$',
    int decimalDigits = 2,
  }) {
    final formatter = NumberFormat.currency(
      symbol: symbol,
      decimalDigits: decimalDigits,
    );
    return formatter.format(amount);
  }

  /// Format percentage
  static String percentage(
    double value, {
    int decimalDigits = 1,
    bool includeSign = true,
  }) {
    final formatted = value.toStringAsFixed(decimalDigits);
    return includeSign ? '$formatted%' : formatted;
  }

  /// Format phone number
  static String phoneNumber(String phone) {
    // Remove all non-digits
    final digitsOnly = phone.replaceAll(RegExp(r'\D'), '');

    // Format based on length
    if (digitsOnly.length == 10) {
      // US format: (XXX) XXX-XXXX
      return '(${digitsOnly.substring(0, 3)}) ${digitsOnly.substring(3, 6)}-${digitsOnly.substring(6)}';
    } else if (digitsOnly.length == 11 && digitsOnly.startsWith('1')) {
      // US format with country code: +1 (XXX) XXX-XXXX
      return '+1 (${digitsOnly.substring(1, 4)}) ${digitsOnly.substring(4, 7)}-${digitsOnly.substring(7)}';
    } else {
      // Return as-is for other formats
      return phone;
    }
  }

  /// Format credit card number
  static String creditCard(String number) {
    // Remove all non-digits
    final digitsOnly = number.replaceAll(RegExp(r'\D'), '');

    // Add spaces every 4 digits
    final buffer = StringBuffer();
    for (var i = 0; i < digitsOnly.length; i++) {
      if (i > 0 && i % 4 == 0) {
        buffer.write(' ');
      }
      buffer.write(digitsOnly[i]);
    }

    return buffer.toString();
  }

  /// Format date
  static String date(
    DateTime dateTime, {
    String pattern = 'MMM dd, yyyy',
  }) {
    return DateFormat(pattern).format(dateTime);
  }

  /// Format time
  static String time(
    DateTime dateTime, {
    bool use24Hour = false,
  }) {
    final pattern = use24Hour ? 'HH:mm' : 'h:mm a';
    return DateFormat(pattern).format(dateTime);
  }

  /// Format date and time
  static String dateTime(
    DateTime dateTime, {
    String pattern = 'MMM dd, yyyy h:mm a',
  }) {
    return DateFormat(pattern).format(dateTime);
  }

  /// Format relative time
  static String relativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.isNegative) {
      // Future dates
      final futureDiff = dateTime.difference(now);
      if (futureDiff.inDays > 365) {
        final years = (futureDiff.inDays / 365).floor();
        return 'in $years ${years == 1 ? 'year' : 'years'}';
      } else if (futureDiff.inDays > 30) {
        final months = (futureDiff.inDays / 30).floor();
        return 'in $months ${months == 1 ? 'month' : 'months'}';
      } else if (futureDiff.inDays > 0) {
        return 'in ${futureDiff.inDays} ${futureDiff.inDays == 1 ? 'day' : 'days'}';
      } else if (futureDiff.inHours > 0) {
        return 'in ${futureDiff.inHours} ${futureDiff.inHours == 1 ? 'hour' : 'hours'}';
      } else if (futureDiff.inMinutes > 0) {
        return 'in ${futureDiff.inMinutes} ${futureDiff.inMinutes == 1 ? 'minute' : 'minutes'}';
      } else {
        return 'in a moment';
      }
    }

    // Past dates
    if (difference.inDays > 365) {
      final years = (difference.inDays / 365).floor();
      return '$years ${years == 1 ? 'year' : 'years'} ago';
    } else if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return '$months ${months == 1 ? 'month' : 'months'} ago';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} ${difference.inDays == 1 ? 'day' : 'days'} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} ${difference.inHours == 1 ? 'hour' : 'hours'} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} ${difference.inMinutes == 1 ? 'minute' : 'minutes'} ago';
    } else {
      return 'just now';
    }
  }

  /// Format number with commas
  static String number(
    num value, {
    int decimalDigits = 0,
  }) {
    final formatter = NumberFormat.decimalPattern()
      ..minimumFractionDigits = decimalDigits
      ..maximumFractionDigits = decimalDigits;
    return formatter.format(value);
  }

  /// Format compact number (1K, 1M, etc.)
  static String compactNumber(num value) {
    return NumberFormat.compact().format(value);
  }

  /// Format timer (MM:SS or HH:MM:SS)
  static String timer(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    if (duration.inHours > 0) {
      return '${twoDigits(duration.inHours)}:${twoDigits(duration.inMinutes.remainder(60))}:${twoDigits(duration.inSeconds.remainder(60))}';
    } else {
      return '${twoDigits(duration.inMinutes)}:${twoDigits(duration.inSeconds.remainder(60))}';
    }
  }

  /// Format repository name from URL
  static String repoName(String url) {
    // Extract owner/repo from GitHub URL
    final regex = RegExp(
      r'github\.com[:/]([^/]+)/([^/\s]+)',
      caseSensitive: false,
    );
    final match = regex.firstMatch(url);
    if (match != null) {
      final owner = match.group(1);
      final repo = match.group(2)?.replaceAll('.git', '');
      return '$owner/$repo';
    }
    return url;
  }

  /// Format branch name for display
  static String branchName(String branch) {
    // Shorten common prefixes
    return branch
        .replaceAll('refs/heads/', '')
        .replaceAll('refs/remotes/', '')
        .replaceAll('origin/', '');
  }

  /// Format commit hash
  static String commitHash(String hash, {int length = 7}) {
    if (hash.length <= length) return hash;
    return hash.substring(0, length);
  }

  /// Format code language for display
  static String codeLanguage(String lang) {
    final languages = {
      'js': 'JavaScript',
      'ts': 'TypeScript',
      'jsx': 'React',
      'tsx': 'React TypeScript',
      'py': 'Python',
      'rb': 'Ruby',
      'go': 'Go',
      'rs': 'Rust',
      'cpp': 'C++',
      'cs': 'C#',
      'java': 'Java',
      'kt': 'Kotlin',
      'swift': 'Swift',
      'dart': 'Dart',
      'php': 'PHP',
      'sh': 'Shell',
      'yml': 'YAML',
      'json': 'JSON',
      'xml': 'XML',
      'html': 'HTML',
      'css': 'CSS',
      'scss': 'SCSS',
      'sql': 'SQL',
      'md': 'Markdown',
    };

    return languages[lang.toLowerCase()] ?? lang.toUpperCase();
  }

  /// Format agent name
  static String agentName(String agent) {
    // Capitalize and format agent names
    return agent
        .replaceAll('_', ' ')
        .split(' ')
        .map((word) => word.isEmpty
            ? ''
            : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
        .join(' ');
  }

  /// Format model name
  static String modelName(String model) {
    final models = {
      'claude-3-5-sonnet': 'Claude 3.5 Sonnet',
      'claude-3-opus': 'Claude 3 Opus',
      'gpt-4-turbo': 'GPT-4 Turbo',
      'gpt-4': 'GPT-4',
      'gpt-3.5-turbo': 'GPT-3.5 Turbo',
      'gemini-pro': 'Gemini Pro',
      'gemini-ultra': 'Gemini Ultra',
    };

    return models[model.toLowerCase()] ?? model;
  }
}