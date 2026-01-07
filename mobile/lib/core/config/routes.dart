import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:paraclete/features/agents/presentation/screens/agent_dashboard_screen.dart';
import 'package:paraclete/features/home/presentation/screens/home_screen.dart';
import 'package:paraclete/features/sessions/presentation/screens/sessions_list_screen.dart';
import 'package:paraclete/features/settings/presentation/screens/settings_screen.dart';
import 'package:paraclete/features/terminal/presentation/screens/terminal_screen.dart';
import 'package:paraclete/features/voice/presentation/screens/voice_input_screen.dart';

/// Route names as constants
class Routes {
  Routes._();

  static const String home = '/';
  static const String voice = '/voice';
  static const String terminal = '/terminal';
  static const String agents = '/agents';
  static const String agentDetails = '/agents/:id';
  static const String sessions = '/sessions';
  static const String sessionDetails = '/sessions/:id';
  static const String git = '/git';
  static const String gitPrs = '/git/prs';
  static const String gitPrDetails = '/git/prs/:id';
  static const String settings = '/settings';
  static const String apiKeys = '/settings/api-keys';
  static const String auth = '/auth';
  static const String login = '/auth/login';
  static const String onboarding = '/onboarding';
}

/// Route configuration
class AppRouter {
  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>();

  static final GoRouter router = GoRouter(
    navigatorKey: navigatorKey,
    initialLocation: Routes.home,
    debugLogDiagnostics: true,
    routes: [
      GoRoute(
        path: Routes.home,
        name: 'home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: Routes.voice,
        name: 'voice',
        builder: (context, state) => const VoiceInputScreen(),
      ),
      GoRoute(
        path: Routes.terminal,
        name: 'terminal',
        builder: (context, state) => const TerminalScreen(),
      ),
      GoRoute(
        path: Routes.agents,
        name: 'agents',
        builder: (context, state) => const AgentDashboardScreen(),
        routes: [
          GoRoute(
            path: ':id',
            name: 'agent-details',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return Scaffold(
                body: Center(
                  child: Text('Agent Details Screen - ID: $id'),
                ),
              );
            },
          ),
        ],
      ),
      GoRoute(
        path: Routes.sessions,
        name: 'sessions',
        builder: (context, state) => const SessionsListScreen(),
        routes: [
          GoRoute(
            path: ':id',
            name: 'session-details',
            builder: (context, state) {
              final id = state.pathParameters['id']!;
              return Scaffold(
                body: Center(
                  child: Text('Session Details Screen - ID: $id'),
                ),
              );
            },
          ),
        ],
      ),
      GoRoute(
        path: Routes.git,
        name: 'git',
        builder: (context, state) => const Scaffold(
          body: Center(
            child: Text('Git Screen - Placeholder'),
          ),
        ),
        routes: [
          GoRoute(
            path: 'prs',
            name: 'git-prs',
            builder: (context, state) => const Scaffold(
              body: Center(
                child: Text('Pull Requests Screen - Placeholder'),
              ),
            ),
            routes: [
              GoRoute(
                path: ':id',
                name: 'git-pr-details',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return Scaffold(
                    body: Center(
                      child: Text('PR Details Screen - ID: $id'),
                    ),
                  );
                },
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: Routes.settings,
        name: 'settings',
        builder: (context, state) => const SettingsScreen(),
        routes: [
          GoRoute(
            path: 'api-keys',
            name: 'api-keys',
            builder: (context, state) => const Scaffold(
              body: Center(
                child: Text('API Keys Screen - Placeholder'),
              ),
            ),
          ),
        ],
      ),
      GoRoute(
        path: Routes.auth,
        name: 'auth',
        builder: (context, state) => const Scaffold(
          body: Center(
            child: Text('Auth Screen - Placeholder'),
          ),
        ),
        routes: [
          GoRoute(
            path: 'login',
            name: 'login',
            builder: (context, state) => const Scaffold(
              body: Center(
                child: Text('Login Screen - Placeholder'),
              ),
            ),
          ),
        ],
      ),
      GoRoute(
        path: Routes.onboarding,
        name: 'onboarding',
        builder: (context, state) => const Scaffold(
          body: Center(
            child: Text('Onboarding Screen - Placeholder'),
          ),
        ),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 48,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              state.uri.toString(),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(Routes.home),
              child: const Text('Go to Home'),
            ),
          ],
        ),
      ),
    ),
  );

  /// Navigation helpers
  static void go(String location) {
    router.go(location);
  }

  static void push(String location) {
    router.push(location);
  }

  static void replace(String location) {
    router.replace(location);
  }

  static void pop() {
    if (router.canPop()) {
      router.pop();
    }
  }

  static bool canPop() {
    return router.canPop();
  }
}