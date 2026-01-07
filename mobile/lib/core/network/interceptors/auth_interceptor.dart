import 'package:dio/dio.dart';
import 'package:paraclete/core/storage/secure_storage.dart';

/// Interceptor to handle authentication tokens
class AuthInterceptor extends Interceptor {
  final SecureStorageService secureStorage;
  final Dio dio;
  String? _accessToken;
  bool _isRefreshing = false;
  final List<RequestOptions> _pendingRequests = [];

  AuthInterceptor({
    required this.secureStorage,
    required this.dio,
  });

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip auth for public endpoints
    if (_isPublicEndpoint(options.path)) {
      return handler.next(options);
    }

    // Get token from storage if not cached
    _accessToken ??= await secureStorage.getAccessToken();

    if (_accessToken != null) {
      options.headers['Authorization'] = 'Bearer $_accessToken';
    }

    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      // Handle token expiration
      if (_isRefreshing) {
        // Add to pending queue
        _pendingRequests.add(err.requestOptions);
        return;
      }

      _isRefreshing = true;

      try {
        // Attempt to refresh token
        final refreshToken = await secureStorage.getRefreshToken();
        if (refreshToken == null) {
          // No refresh token, redirect to login
          await _handleLogout();
          return handler.reject(err);
        }

        final response = await dio.post(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
        );

        if (response.statusCode == 200) {
          final newAccessToken = response.data['access_token'] as String;
          final newRefreshToken = response.data['refresh_token'] as String?;

          // Store new tokens
          await secureStorage.storeAccessToken(newAccessToken);
          if (newRefreshToken != null) {
            await secureStorage.storeRefreshToken(newRefreshToken);
          }

          _accessToken = newAccessToken;

          // Retry original request
          Response clonedRequest;
          try {
            clonedRequest = await _retryRequest(err.requestOptions);
          } catch (e) {
            await _handleLogout();
            return handler.reject(err);
          }

          // Retry pending requests (with error handling for each)
          for (final pending in _pendingRequests) {
            try {
              await _retryRequest(pending);
            } catch (e) {
              // Continue with other pending requests
            }
          }
          _pendingRequests.clear();

          return handler.resolve(clonedRequest);
        }
      } catch (e, stackTrace) {
        // Refresh failed, redirect to login
        await _handleLogout();
        return handler.reject(err);
      } finally {
        _isRefreshing = false;
      }
    }

    return handler.next(err);
  }

  Future<Response> _retryRequest(RequestOptions requestOptions) async {
    final options = Options(
      method: requestOptions.method,
      headers: {
        ...requestOptions.headers,
        'Authorization': 'Bearer $_accessToken',
      },
    );

    return dio.request(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }

  Future<void> _handleLogout() async {
    _accessToken = null;
    await secureStorage.clearAuthentication();
    // Navigate to login will be handled by the app layer
  }

  bool _isPublicEndpoint(String path) {
    final publicPaths = [
      '/auth/login',
      '/auth/github',
      '/auth/refresh',
      '/auth/register',
      '/health',
      '/version',
    ];

    return publicPaths.any((public) => path.contains(public));
  }

  void clearToken() {
    _accessToken = null;
  }
}