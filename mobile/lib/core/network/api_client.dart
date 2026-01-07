import 'package:dio/dio.dart';
import 'package:paraclete/core/config/app_config.dart';
import 'package:paraclete/core/config/env_config.dart';
import 'package:paraclete/core/network/interceptors/auth_interceptor.dart';
import 'package:paraclete/core/network/interceptors/error_interceptor.dart';
import 'package:paraclete/core/network/interceptors/logging_interceptor.dart';
import 'package:paraclete/core/storage/secure_storage.dart';

/// Main API client for all HTTP requests
class ApiClient {
  late final Dio _dio;
  final SecureStorageService _secureStorage;

  ApiClient({required SecureStorageService secureStorage})
      : _secureStorage = secureStorage {
    _dio = Dio(_baseOptions);
    _setupInterceptors();
  }

  BaseOptions get _baseOptions => BaseOptions(
        baseUrl: '${EnvConfig.apiBaseUrl}/v1',
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        sendTimeout: AppConfig.sendTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-App-Version': AppConfig.appVersion,
          'X-Platform': 'mobile',
        },
        validateStatus: (status) => status != null && status < 500,
      );

  void _setupInterceptors() {
    _dio.interceptors.addAll([
      AuthInterceptor(secureStorage: _secureStorage, dio: _dio),
      ErrorInterceptor(),
      if (EnvConfig.enableLogging) LoggingInterceptor(),
    ]);
  }

  // Sessions API
  Future<Response> createSession({
    String? repoUrl,
    String? branchName,
    String? desktopSessionId,
  }) async {
    return _dio.post(
      '/sessions',
      data: {
        'repo_url': repoUrl,
        'branch_name': branchName,
        'desktop_session_id': desktopSessionId,
      },
    );
  }

  Future<Response> getSessions({
    int page = 1,
    int limit = AppConfig.defaultPageSize,
  }) async {
    return _dio.get(
      '/sessions',
      queryParameters: {
        'page': page,
        'limit': limit,
      },
    );
  }

  Future<Response> getSession(String sessionId) async {
    return _dio.get('/sessions/$sessionId');
  }

  Future<Response> deleteSession(String sessionId) async {
    return _dio.delete('/sessions/$sessionId');
  }

  Future<Response> syncSession(
    String sessionId,
    Map<String, dynamic> syncData,
  ) async {
    return _dio.post(
      '/sessions/$sessionId/sync',
      data: syncData,
    );
  }

  // Agent API
  Future<Response> invokeAgent(
    String sessionId, {
    String? voiceTranscript,
    String? textInput,
    Map<String, dynamic>? context,
  }) async {
    return _dio.post(
      '/sessions/$sessionId/invoke',
      data: {
        'voice_transcript': voiceTranscript,
        'text_input': textInput,
        'context': context,
      },
    );
  }

  Future<Response> getAgentStatuses(String sessionId) async {
    return _dio.get('/sessions/$sessionId/agents');
  }

  Future<Response> approveAction(String sessionId, String actionId) async {
    return _dio.post(
      '/sessions/$sessionId/approve',
      data: {'action_id': actionId},
    );
  }

  Future<Response> cancelTask(String sessionId, {String? reason}) async {
    return _dio.post(
      '/sessions/$sessionId/cancel',
      data: {'reason': reason},
    );
  }

  // Voice API
  Future<Response> transcribeAudio(List<int> audioBytes) async {
    final formData = FormData.fromMap({
      'audio': MultipartFile.fromBytes(
        audioBytes,
        filename: 'audio.wav',
      ),
    });
    return _dio.post(
      '/voice/transcribe',
      data: formData,
      options: Options(
        headers: {'Content-Type': 'multipart/form-data'},
      ),
    );
  }

  Future<Response> synthesizeSpeech(String text, {String? voiceId}) async {
    return _dio.post(
      '/voice/synthesize',
      data: {
        'text': text,
        'voice_id': voiceId,
      },
      options: Options(responseType: ResponseType.bytes),
    );
  }

  // MCP Proxy API
  Future<Response> getMcpServers() async {
    return _dio.get('/mcp/servers');
  }

  Future<Response> callMcpTool(
    String server,
    String tool,
    Map<String, dynamic> arguments,
  ) async {
    return _dio.post(
      '/mcp/$server/tools/$tool',
      data: {'arguments': arguments},
    );
  }

  // Compute API
  Future<Response> createMachine({
    required String name,
    String size = 'shared-cpu-1x',
    String region = 'iad',
    Map<String, String>? env,
  }) async {
    return _dio.post(
      '/compute/machines',
      data: {
        'name': name,
        'size': size,
        'region': region,
        'env': env,
      },
    );
  }

  Future<Response> getMachine(String machineId) async {
    return _dio.get('/compute/machines/$machineId');
  }

  Future<Response> deleteMachine(String machineId) async {
    return _dio.delete('/compute/machines/$machineId');
  }

  Future<Response> getMachineSshCredentials(String machineId) async {
    return _dio.post('/compute/machines/$machineId/ssh');
  }

  // Auth API
  Future<Response> login({
    required String email,
    required String password,
  }) async {
    return _dio.post(
      '/auth/login',
      data: {
        'email': email,
        'password': password,
      },
    );
  }

  Future<Response> loginWithGitHub(String code) async {
    return _dio.post(
      '/auth/github',
      data: {'code': code},
    );
  }

  Future<Response> refreshToken(String refreshToken) async {
    return _dio.post(
      '/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
  }

  Future<Response> logout() async {
    return _dio.post('/auth/logout');
  }

  // User API
  Future<Response> getCurrentUser() async {
    return _dio.get('/user/me');
  }

  Future<Response> updateUser(Map<String, dynamic> updates) async {
    return _dio.patch('/user/me', data: updates);
  }

  Future<Response> updateApiKeys(Map<String, String?> keys) async {
    return _dio.post('/user/api-keys', data: keys);
  }

  // Git API
  Future<Response> getPullRequests({
    String? repo,
    String? state,
    int page = 1,
    int limit = AppConfig.defaultPageSize,
  }) async {
    return _dio.get(
      '/git/prs',
      queryParameters: {
        if (repo != null) 'repo': repo,
        if (state != null) 'state': state,
        'page': page,
        'limit': limit,
      },
    );
  }

  Future<Response> getPullRequest(String prId) async {
    return _dio.get('/git/prs/$prId');
  }

  Future<Response> reviewPullRequest(
    String prId,
    Map<String, dynamic> review,
  ) async {
    return _dio.post(
      '/git/prs/$prId/review',
      data: review,
    );
  }

  // Generic request methods
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return _dio.get(
      path,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return _dio.post(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return _dio.put(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return _dio.patch(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    return _dio.delete(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  // Download file
  Future<Response> download(
    String urlPath,
    String savePath, {
    void Function(int, int)? onReceiveProgress,
    CancelToken? cancelToken,
  }) async {
    return _dio.download(
      urlPath,
      savePath,
      onReceiveProgress: onReceiveProgress,
      cancelToken: cancelToken,
    );
  }

  // Cancel request
  CancelToken createCancelToken() => CancelToken();

  void cancelRequest(CancelToken token) {
    token.cancel('Request cancelled by user');
  }
}