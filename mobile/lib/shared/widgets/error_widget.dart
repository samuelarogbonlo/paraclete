import 'package:flutter/material.dart';
import 'package:paraclete/core/theme/colors.dart';

/// Custom error widget for displaying error states
class AppErrorWidget extends StatelessWidget {
  final String title;
  final String? message;
  final VoidCallback? onRetry;
  final IconData icon;
  final Color? iconColor;

  const AppErrorWidget({
    super.key,
    this.title = 'Something went wrong',
    this.message,
    this.onRetry,
    this.icon = Icons.error_outline,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 64,
              color: iconColor ?? AppColors.error,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: 8),
              Text(
                message!,
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Network error widget
class NetworkErrorWidget extends StatelessWidget {
  final VoidCallback? onRetry;

  const NetworkErrorWidget({
    super.key,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return AppErrorWidget(
      icon: Icons.wifi_off,
      title: 'No Internet Connection',
      message: 'Please check your internet connection and try again.',
      onRetry: onRetry,
      iconColor: AppColors.neutral500,
    );
  }
}

/// Empty state widget
class EmptyStateWidget extends StatelessWidget {
  final String title;
  final String? message;
  final VoidCallback? onAction;
  final String? actionLabel;
  final IconData icon;
  final Widget? customAction;

  const EmptyStateWidget({
    super.key,
    this.title = 'No data found',
    this.message,
    this.onAction,
    this.actionLabel,
    this.icon = Icons.inbox_outlined,
    this.customAction,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 64,
              color: AppColors.neutral400,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: AppColors.neutral600,
                  ),
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: 8),
              Text(
                message!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.neutral500,
                    ),
                textAlign: TextAlign.center,
              ),
            ],
            if (customAction != null) ...[
              const SizedBox(height: 24),
              customAction!,
            ] else if (onAction != null) ...[
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: onAction,
                child: Text(actionLabel ?? 'Get Started'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Permission denied widget
class PermissionDeniedWidget extends StatelessWidget {
  final String permission;
  final VoidCallback? onRequestPermission;

  const PermissionDeniedWidget({
    super.key,
    required this.permission,
    this.onRequestPermission,
  });

  @override
  Widget build(BuildContext context) {
    return AppErrorWidget(
      icon: Icons.lock_outline,
      title: 'Permission Required',
      message: 'Please grant $permission permission to continue.',
      onRetry: onRequestPermission,
      iconColor: AppColors.warning,
    );
  }
}

/// Maintenance widget
class MaintenanceWidget extends StatelessWidget {
  final DateTime? estimatedTime;

  const MaintenanceWidget({
    super.key,
    this.estimatedTime,
  });

  @override
  Widget build(BuildContext context) {
    String message = 'We are currently performing maintenance. Please check back later.';

    if (estimatedTime != null) {
      final difference = estimatedTime!.difference(DateTime.now());
      if (difference.isNegative) {
        message = 'Maintenance should be complete soon. Please try again.';
      } else if (difference.inHours > 0) {
        message = 'We will be back in approximately ${difference.inHours} hours.';
      } else if (difference.inMinutes > 0) {
        message = 'We will be back in approximately ${difference.inMinutes} minutes.';
      }
    }

    return AppErrorWidget(
      icon: Icons.construction,
      title: 'Under Maintenance',
      message: message,
      iconColor: AppColors.warning,
    );
  }
}

/// Error boundary widget
class ErrorBoundary extends StatefulWidget {
  final Widget child;
  final Widget Function(Object error, StackTrace? stackTrace)? errorBuilder;

  const ErrorBoundary({
    super.key,
    required this.child,
    this.errorBuilder,
  });

  @override
  State<ErrorBoundary> createState() => _ErrorBoundaryState();
}

class _ErrorBoundaryState extends State<ErrorBoundary> {
  Object? _error;
  StackTrace? _stackTrace;

  @override
  void initState() {
    super.initState();
    FlutterError.onError = (FlutterErrorDetails details) {
      setState(() {
        _error = details.exception;
        _stackTrace = details.stack;
      });
    };
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      if (widget.errorBuilder != null) {
        return widget.errorBuilder!(_error!, _stackTrace);
      }
      return AppErrorWidget(
        title: 'An unexpected error occurred',
        message: _error.toString(),
        onRetry: () {
          setState(() {
            _error = null;
            _stackTrace = null;
          });
        },
      );
    }
    return widget.child;
  }
}