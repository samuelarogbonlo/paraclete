import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/config/env_config.dart';
import 'package:paraclete/core/config/routes.dart';
import 'package:paraclete/core/theme/app_theme.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/shared/providers/core_providers.dart';

/// Main application widget
class ParacleteApp extends ConsumerStatefulWidget {
  const ParacleteApp({super.key});

  @override
  ConsumerState<ParacleteApp> createState() => _ParacleteAppState();
}

class _ParacleteAppState extends ConsumerState<ParacleteApp>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeApp();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    AppLogger.debug('App lifecycle state changed to: $state');

    switch (state) {
      case AppLifecycleState.resumed:
        _onAppResumed();
        break;
      case AppLifecycleState.paused:
        _onAppPaused();
        break;
      case AppLifecycleState.detached:
        _onAppDetached();
        break;
      default:
        break;
    }
  }

  Future<void> _initializeApp() async {
    try {
      // Load authentication state
      final auth = ref.read(authProvider);
      if (auth.isAuthenticated) {
        AppLogger.info('User authenticated: ${auth.email}');
      }

      // Initialize any startup tasks here
    } catch (e) {
      AppLogger.error('App initialization error', error: e);
    }
  }

  void _onAppResumed() {
    // Handle app resume
    AppLogger.debug('App resumed');

    // Reconnect WebSocket if needed
    final sessionId = ref.read(currentSessionIdProvider);
    if (sessionId != null) {
      final wsClient = ref.read(webSocketClientProvider);
      if (!wsClient.isConnected) {
        wsClient.connect(sessionId: sessionId);
      }
    }
  }

  void _onAppPaused() {
    // Handle app pause
    AppLogger.debug('App paused');
  }

  void _onAppDetached() {
    // Handle app detached
    AppLogger.debug('App detached');

    // Disconnect WebSocket
    final wsClient = ref.read(webSocketClientProvider);
    wsClient.disconnect();
  }

  @override
  Widget build(BuildContext context) {
    final appSettings = ref.watch(appSettingsProvider);

    return MaterialApp.router(
      title: 'Paraclete',
      debugShowCheckedModeBanner: EnvConfig.featureOverrides['showDebugBanner'] ?? false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: appSettings.isDarkMode ? ThemeMode.dark : ThemeMode.light,
      routerConfig: AppRouter.router,
      builder: (context, child) {
        // Global app wrapper for error handling, loading states, etc.
        return _AppWrapper(child: child ?? const SizedBox());
      },
    );
  }
}

/// Global app wrapper for error boundaries and overlays
class _AppWrapper extends ConsumerWidget {
  final Widget child;

  const _AppWrapper({required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isLoading = ref.watch(isLoadingProvider);
    final error = ref.watch(errorProvider);

    return Stack(
      children: [
        // Main app content
        child,

        // Global loading overlay
        if (isLoading)
          Positioned.fill(
            child: Container(
              color: Colors.black.withOpacity(0.5),
              child: const Center(
                child: Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Loading...'),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

        // Global error snackbar
        if (error != null)
          Positioned(
            bottom: MediaQuery.of(context).padding.bottom + 16,
            left: 16,
            right: 16,
            child: Material(
              color: Colors.transparent,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.error,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.error_outline,
                      color: Colors.white,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        error,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: () {
                        ref.read(errorProvider.notifier).state = null;
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}