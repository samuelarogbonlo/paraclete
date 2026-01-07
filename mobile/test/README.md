# Paraclete Mobile Tests

Comprehensive test suite for the Paraclete Flutter mobile application.

## Running Tests

### Run all tests
```bash
flutter test
```

### Run specific test file
```bash
flutter test test/core/network/api_client_test.dart
```

### Run with coverage
```bash
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

## Test Structure

```
test/
├── core/
│   ├── config/           # App configuration tests
│   ├── network/          # API client, WebSocket, interceptor tests
│   └── storage/          # Secure storage tests
├── helpers/              # Test utilities and helpers
└── mocks/                # Mock objects and test doubles
```

## Test Categories

### Unit Tests
- **Config**: AppConfig, EnvConfig settings validation
- **Network**: ApiClient methods, WebSocketClient connection management
- **Storage**: SecureStorageService encryption and retrieval
- **Interceptors**: Auth, error handling, logging logic

### Coverage Goals
- Core modules: >80%
- Network layer: >85%
- Storage layer: >80%
- Configuration: >90%

## Key Test Files

### Network Layer
- `api_client_test.dart` - Tests all API endpoints and HTTP methods
- `websocket_client_test.dart` - WebSocket connection, messaging, and state management
- `error_interceptor_test.dart` - Error transformation and exception handling

### Configuration
- `app_config_test.dart` - App settings, timeouts, feature flags
- `env_config_test.dart` - Environment-specific configuration

### Storage
- `secure_storage_test.dart` - Secure data storage and retrieval

## Test Helpers

### Mock Objects
```dart
// Use generated mocks
import 'package:mockito/annotations.dart';

@GenerateMocks([SecureStorageService, Dio])
import 'test_file.mocks.dart';
```

### Test Utilities
```dart
import '../helpers/test_helpers.dart';

await delay(100); // Wait for async operations
```

## Writing New Tests

1. Create test file in appropriate directory
2. Import required packages and mocks
3. Group related tests using `group()`
4. Use descriptive test names
5. Follow AAA pattern: Arrange, Act, Assert

Example:
```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MyFeature', () {
    setUp(() {
      // Arrange
    });

    test('should do something', () {
      // Act
      final result = doSomething();

      // Assert
      expect(result, expectedValue);
    });
  });
}
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Release builds

## Troubleshooting

### Tests timeout
- Increase timeout: `testWidgets('test', (tester) async { ... }, timeout: Timeout(Duration(seconds: 30)))`

### Mock generation fails
- Run: `flutter pub run build_runner build --delete-conflicting-outputs`

### Coverage not generated
- Ensure `--coverage` flag is used
- Check that test files don't import `main.dart`
