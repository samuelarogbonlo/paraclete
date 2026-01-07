import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/app.dart';
import 'package:paraclete/core/config/env_config.dart';
import 'package:paraclete/core/storage/preferences.dart';
import 'package:paraclete/core/utils/logger.dart';

void main() async {
  // Ensure Flutter bindings are initialized
  WidgetsFlutterBinding.ensureInitialized();

  // Set up error handling
  FlutterError.onError = (FlutterErrorDetails details) {
    AppLogger.error(
      'Flutter Error',
      error: details.exception,
      stackTrace: details.stack,
    );
  };

  // Initialize services
  await _initializeApp();

  // Run the app with Riverpod provider scope
  runApp(
    const ProviderScope(
      child: ParacleteApp(),
    ),
  );
}

Future<void> _initializeApp() async {
  try {
    // Set environment
    const String environment = String.fromEnvironment(
      'ENV',
      defaultValue: 'development',
    );

    switch (environment) {
      case 'production':
        EnvConfig.setEnvironment(Environment.production);
        break;
      case 'staging':
        EnvConfig.setEnvironment(Environment.staging);
        break;
      default:
        EnvConfig.setEnvironment(Environment.development);
    }

    AppLogger.info('Starting Paraclete in ${EnvConfig.environment} mode');

    // Initialize preferences
    await PreferencesService.init();

    // Set system UI overlay style
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
        systemNavigationBarColor: Colors.white,
        systemNavigationBarIconBrightness: Brightness.dark,
        systemNavigationBarDividerColor: Colors.transparent,
      ),
    );

    // Set preferred orientations
    await SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);

    // Update launch tracking
    if (PreferencesService.firstLaunchDate == null) {
      await PreferencesService.setFirstLaunchDate(DateTime.now());
    }
    await PreferencesService.setLastLaunchDate(DateTime.now());
    await PreferencesService.incrementLaunchCount();

    AppLogger.info('App initialization complete');
  } catch (e, stackTrace) {
    AppLogger.fatal(
      'Failed to initialize app',
      error: e,
      stackTrace: stackTrace,
    );
    // Continue anyway - the app might still be usable
  }
}