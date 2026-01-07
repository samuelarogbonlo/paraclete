/// Common test helper functions and utilities
library test_helpers;

import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

/// Helper to wait for async operations
Future<void> pumpAndSettle() async {
  await Future.delayed(const Duration(milliseconds: 100));
}

/// Helper to verify mock call count
void verifyCallCount(dynamic mock, Function invocation, int count) {
  verify(invocation).called(count);
}

/// Helper to verify no interactions
void verifyNoInteractions(dynamic mock) {
  verifyZeroInteractions(mock);
}

/// Helper to create a delay
Future<void> delay([int milliseconds = 100]) async {
  await Future.delayed(Duration(milliseconds: milliseconds));
}

/// Matcher for checking exception types
Matcher throwsA<T>() => throwsA(isA<T>());
