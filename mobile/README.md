# Paraclete Mobile App

Mobile-first AI coding platform - Voice-first, model-agnostic, no laptop required.

## Foundation Status

✅ **Complete Flutter foundation infrastructure ready for feature development**

## Architecture

### Clean Architecture + Feature-First Organization

```
lib/
├── core/                          # Shared infrastructure
│   ├── config/                    # App configuration
│   ├── network/                   # API & WebSocket clients
│   ├── storage/                   # Secure storage & preferences
│   ├── theme/                     # App theming
│   └── utils/                     # Utilities & extensions
├── features/                      # Feature modules
│   ├── voice/                     # Voice input (Deepgram STT, ElevenLabs TTS)
│   ├── terminal/                  # SSH terminal (dartssh2, xterm)
│   ├── agents/                    # AI agents dashboard
│   ├── sessions/                  # Session management
│   ├── git/                       # Git & PR features
│   └── settings/                  # App settings
├── shared/                        # Shared components
│   ├── widgets/                   # Reusable widgets
│   └── providers/                 # Riverpod providers
├── main.dart                      # App entry point
└── app.dart                       # App configuration
```

## Tech Stack

- **Flutter**: 3.27+
- **Dart**: 3.6+
- **State Management**: Riverpod 3
- **Navigation**: go_router
- **HTTP Client**: dio
- **WebSocket**: web_socket_channel
- **Storage**: flutter_secure_storage

## Core Infrastructure (Implemented)

### ✅ Config Module
- Environment configuration (dev/staging/prod)
- App constants and settings
- Complete routing structure with GoRouter

### ✅ Network Module
- Comprehensive API client with all endpoints
- WebSocket client with automatic reconnection
- Auth interceptor with token refresh
- Error handling and transformation
- Request/response logging

### ✅ Storage Module
- Type-safe secure storage for API keys
- SharedPreferences wrapper
- Encryption for sensitive data

### ✅ Theme Module
- Light/dark theme support
- Material 3 design system
- Agent-specific color palette

### ✅ Utils Module
- Structured logging
- String, DateTime, List extensions
- Input validators
- Text formatters

### ✅ Shared Components
- Loading indicators & shimmer effects
- Error widgets & empty states
- Base scaffolds
- Riverpod providers structure

## Getting Started

### Prerequisites

- Flutter SDK 3.27+
- Dart SDK 3.6+
- iOS/Android development environment

### Installation

```bash
# Get dependencies
flutter pub get

# Run code generation (if needed)
flutter pub run build_runner build --delete-conflicting-outputs

# Run the app
flutter run

# Run on specific device
flutter run -d iPhone  # iOS Simulator
flutter run -d chrome  # Web browser
```

### Environment Variables

Create a `.env` file in the mobile directory (for local development):

```env
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000
```

## Development

### Code Generation

Some features use code generation (freezed, json_serializable):

```bash
flutter pub run build_runner watch
```

### Running Tests

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# Run specific test file
flutter test test/core/network/api_client_test.dart
```

### Building for Release

```bash
# iOS
flutter build ios --release

# Android
flutter build appbundle --release

# APK for testing
flutter build apk --release
```

## Project Status

### ✅ Completed
- Project structure and architecture
- All core infrastructure modules
- Shared widgets and providers
- Main app setup with Riverpod
- Placeholder screens for all features
- Navigation and routing
- Theme and styling

### 🔄 Ready for Implementation (Other Subagents)
- Voice input features (Deepgram STT, ElevenLabs TTS)
- Terminal functionality (SSH, xterm)
- Agent dashboard (LangGraph integration)
- Session management
- Git/PR features
- Settings and API key management

## Architecture Decisions

1. **Riverpod over BLoC**: Less boilerplate, compile-time safety
2. **Feature-First Organization**: Better scalability for large apps
3. **Clean Architecture**: Clear separation of concerns
4. **Type-Safe Storage**: Enum-based keys prevent typos
5. **Comprehensive Error Handling**: Typed exceptions, graceful degradation

## Code Quality

- Strict analysis options enabled
- No implicit casts or dynamics
- Comprehensive error handling
- Structured logging
- Type-safe throughout

## Notes for Other Subagents

This foundation provides:

1. **Ready-to-use API Client**: All endpoints implemented in `core/network/api_client.dart`
2. **WebSocket Support**: Real-time communication in `core/network/websocket_client.dart`
3. **Secure Storage**: API key management in `core/storage/secure_storage.dart`
4. **Providers Structure**: State management in `shared/providers/core_providers.dart`
5. **Navigation**: All routes configured in `core/config/routes.dart`
6. **Theme**: Complete design system in `core/theme/`
7. **Placeholder Screens**: All features have basic screens ready for implementation

Simply implement your feature in the appropriate `features/` directory following the established patterns.

## License

See main project LICENSE file.