import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// String extensions
extension StringExtensions on String {
  /// Check if string is a valid email
  bool get isValidEmail {
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );
    return emailRegex.hasMatch(this);
  }

  /// Check if string is a valid URL
  bool get isValidUrl {
    final urlRegex = RegExp(
      r'^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$',
      caseSensitive: false,
    );
    return urlRegex.hasMatch(this);
  }

  /// Check if string is a valid phone number
  bool get isValidPhoneNumber {
    final phoneRegex = RegExp(r'^\+?[1-9]\d{1,14}$');
    return phoneRegex.hasMatch(replaceAll(RegExp(r'[\s-()]'), ''));
  }

  /// Capitalize first letter
  String get capitalize {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }

  /// Capitalize each word
  String get capitalizeWords {
    if (isEmpty) return this;
    return split(' ').map((word) => word.capitalize).join(' ');
  }

  /// Truncate string with ellipsis
  String truncate(int maxLength, {String suffix = '...'}) {
    if (length <= maxLength) return this;
    return '${substring(0, maxLength - suffix.length)}$suffix';
  }

  /// Remove all whitespace
  String get removeAllWhitespace {
    return replaceAll(RegExp(r'\s+'), '');
  }

  /// Check if string contains only digits
  bool get isNumeric {
    if (isEmpty) return false;
    return RegExp(r'^\d+$').hasMatch(this);
  }

  /// Convert to safe filename
  String get toSafeFilename {
    return replaceAll(RegExp(r'[^\w\s-.]'), '')
        .replaceAll(RegExp(r'[-\s]+'), '-')
        .toLowerCase();
  }

  /// Mask sensitive data
  String mask({int visibleStart = 4, int visibleEnd = 4}) {
    if (length <= visibleStart + visibleEnd) return '*' * length;
    final start = substring(0, visibleStart);
    final end = substring(length - visibleEnd);
    final masked = '*' * (length - visibleStart - visibleEnd);
    return '$start$masked$end';
  }
}

/// DateTime extensions
extension DateTimeExtensions on DateTime {
  /// Format date as relative time (e.g., "2 hours ago")
  String get timeAgo {
    final now = DateTime.now();
    final difference = now.difference(this);

    if (difference.inDays > 365) {
      final years = (difference.inDays / 365).floor();
      return '$years ${years == 1 ? 'year' : 'years'} ago';
    } else if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return '$months ${months == 1 ? 'month' : 'months'} ago';
    } else if (difference.inDays > 7) {
      final weeks = (difference.inDays / 7).floor();
      return '$weeks ${weeks == 1 ? 'week' : 'weeks'} ago';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} ${difference.inDays == 1 ? 'day' : 'days'} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} ${difference.inHours == 1 ? 'hour' : 'hours'} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} ${difference.inMinutes == 1 ? 'minute' : 'minutes'} ago';
    } else {
      return 'Just now';
    }
  }

  /// Format date as human-readable string
  String get formatted {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));
    final dateOnly = DateTime(year, month, day);

    if (dateOnly == today) {
      return 'Today ${DateFormat.jm().format(this)}';
    } else if (dateOnly == yesterday) {
      return 'Yesterday ${DateFormat.jm().format(this)}';
    } else if (year == now.year) {
      return DateFormat('MMM d, h:mm a').format(this);
    } else {
      return DateFormat('MMM d, y').format(this);
    }
  }

  /// Check if date is today
  bool get isToday {
    final now = DateTime.now();
    return year == now.year && month == now.month && day == now.day;
  }

  /// Check if date is yesterday
  bool get isYesterday {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    return year == yesterday.year &&
        month == yesterday.month &&
        day == yesterday.day;
  }

  /// Start of day
  DateTime get startOfDay {
    return DateTime(year, month, day);
  }

  /// End of day
  DateTime get endOfDay {
    return DateTime(year, month, day, 23, 59, 59, 999);
  }
}

/// Duration extensions
extension DurationExtensions on Duration {
  /// Format duration as human-readable string
  String get formatted {
    if (inDays > 0) {
      return '${inDays}d ${inHours.remainder(24)}h';
    } else if (inHours > 0) {
      return '${inHours}h ${inMinutes.remainder(60)}m';
    } else if (inMinutes > 0) {
      return '${inMinutes}m ${inSeconds.remainder(60)}s';
    } else {
      return '${inSeconds}s';
    }
  }

  /// Format duration as MM:SS or HH:MM:SS
  String get timerFormat {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    if (inHours > 0) {
      return '${twoDigits(inHours)}:${twoDigits(inMinutes.remainder(60))}:${twoDigits(inSeconds.remainder(60))}';
    } else {
      return '${twoDigits(inMinutes)}:${twoDigits(inSeconds.remainder(60))}';
    }
  }
}

/// List extensions
extension ListExtensions<T> on List<T> {
  /// Get element at index or return null
  T? getOrNull(int index) {
    if (index >= 0 && index < length) {
      return this[index];
    }
    return null;
  }

  /// Get element at index or return default
  T getOrElse(int index, T defaultValue) {
    return getOrNull(index) ?? defaultValue;
  }

  /// Split list into chunks
  List<List<T>> chunk(int size) {
    final chunks = <List<T>>[];
    for (var i = 0; i < length; i += size) {
      final end = (i + size < length) ? i + size : length;
      chunks.add(sublist(i, end));
    }
    return chunks;
  }

  /// Remove duplicates while preserving order
  List<T> get unique {
    final seen = <T>{};
    return where((item) => seen.add(item)).toList();
  }
}

/// Map extensions
extension MapExtensions<K, V> on Map<K, V> {
  /// Get value or return default
  V getOrElse(K key, V defaultValue) {
    return this[key] ?? defaultValue;
  }

  /// Filter map entries
  Map<K, V> filter(bool Function(K key, V value) test) {
    final filtered = <K, V>{};
    forEach((key, value) {
      if (test(key, value)) {
        filtered[key] = value;
      }
    });
    return filtered;
  }

  /// Map values while keeping keys
  Map<K, R> mapValues<R>(R Function(V value) transform) {
    return map((key, value) => MapEntry(key, transform(value)));
  }
}

/// BuildContext extensions
extension BuildContextExtensions on BuildContext {
  /// Get theme
  ThemeData get theme => Theme.of(this);

  /// Get text theme
  TextTheme get textTheme => theme.textTheme;

  /// Get color scheme
  ColorScheme get colorScheme => theme.colorScheme;

  /// Get screen size
  Size get screenSize => MediaQuery.of(this).size;

  /// Get screen width
  double get screenWidth => screenSize.width;

  /// Get screen height
  double get screenHeight => screenSize.height;

  /// Check if keyboard is visible
  bool get isKeyboardVisible => MediaQuery.of(this).viewInsets.bottom > 0;

  /// Get safe area padding
  EdgeInsets get safeAreaPadding => MediaQuery.of(this).padding;

  /// Check if dark mode is enabled
  bool get isDarkMode => theme.brightness == Brightness.dark;

  /// Show snackbar
  void showSnackBar(
    String message, {
    Duration duration = const Duration(seconds: 3),
    SnackBarAction? action,
  }) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: duration,
        action: action,
      ),
    );
  }

  /// Show error snackbar
  void showErrorSnackBar(
    String message, {
    Duration duration = const Duration(seconds: 3),
  }) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: colorScheme.error,
        duration: duration,
      ),
    );
  }

  /// Show success snackbar
  void showSuccessSnackBar(
    String message, {
    Duration duration = const Duration(seconds: 3),
  }) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
        duration: duration,
      ),
    );
  }
}

/// Color extensions
extension ColorExtensions on Color {
  /// Darken color
  Color darken([double percent = 10]) {
    assert(percent >= 1 && percent <= 100);
    final factor = 1 - percent / 100;
    return Color.fromARGB(
      alpha,
      (red * factor).round(),
      (green * factor).round(),
      (blue * factor).round(),
    );
  }

  /// Lighten color
  Color lighten([double percent = 10]) {
    assert(percent >= 1 && percent <= 100);
    final factor = percent / 100;
    return Color.fromARGB(
      alpha,
      red + ((255 - red) * factor).round(),
      green + ((255 - green) * factor).round(),
      blue + ((255 - blue) * factor).round(),
    );
  }

  /// Convert to hex string
  String get toHex {
    return '#${value.toRadixString(16).padLeft(8, '0').substring(2)}';
  }
}