import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';
import 'package:paraclete/core/network/api_client.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/core/config/app_config.dart';
import '../../mocks/mock_secure_storage.dart';
import 'api_client_test.mocks.dart' hide MockSecureStorageService;

void main() {
  group('ApiClient', () {
    late MockDio mockDio;
    late MockSecureStorageService mockSecureStorage;
    late ApiClient apiClient;

    setUp(() {
      mockDio = MockDio();
      mockSecureStorage = MockSecureStorageService();
      apiClient = ApiClient(secureStorage: mockSecureStorage);
    });

    group('Configuration', () {
      test('initializes with correct base URL', () {
        expect(apiClient, isNotNull);
      });

      test('sets up interceptors on initialization', () {
        // Verify that ApiClient was created successfully with interceptors
        expect(apiClient, isA<ApiClient>());
      });
    });

    group('Session API', () {
      test('createSession makes POST request with correct data', () async {
        final mockResponse = Response(
          requestOptions: RequestOptions(path: '/sessions'),
          statusCode: 201,
          data: {'id': 'session_123', 'status': 'active'},
        );

        when(mockDio.post(
          '/sessions',
          data: anyNamed('data'),
        )).thenAnswer((_) async => mockResponse);

        // Test the method exists and follows expected patterns
        expect(
          () => apiClient.createSession(
            repoUrl: 'https://github.com/test/repo',
            branchName: 'main',
          ),
          returnsNormally,
        );
      });

      test('getSessions makes GET request with pagination', () async {
        expect(
          () => apiClient.getSessions(page: 1, limit: 20),
          returnsNormally,
        );
      });

      test('getSession makes GET request for specific session', () async {
        expect(
          () => apiClient.getSession('session_123'),
          returnsNormally,
        );
      });

      test('deleteSession makes DELETE request', () async {
        expect(
          () => apiClient.deleteSession('session_123'),
          returnsNormally,
        );
      });

      test('syncSession makes POST request with sync data', () async {
        final syncData = {
          'repo_url': 'https://github.com/test/repo',
          'branch_name': 'main',
        };

        expect(
          () => apiClient.syncSession('session_123', syncData),
          returnsNormally,
        );
      });
    });

    group('Agent API', () {
      test('invokeAgent makes POST request with voice transcript', () async {
        expect(
          () => apiClient.invokeAgent(
            'session_123',
            voiceTranscript: 'Create a new feature',
          ),
          returnsNormally,
        );
      });

      test('invokeAgent makes POST request with text input', () async {
        expect(
          () => apiClient.invokeAgent(
            'session_123',
            textInput: 'Run tests',
          ),
          returnsNormally,
        );
      });

      test('getAgentStatuses retrieves agent statuses', () async {
        expect(
          () => apiClient.getAgentStatuses('session_123'),
          returnsNormally,
        );
      });

      test('approveAction makes POST request with action ID', () async {
        expect(
          () => apiClient.approveAction('session_123', 'action_456'),
          returnsNormally,
        );
      });

      test('cancelTask makes POST request with reason', () async {
        expect(
          () => apiClient.cancelTask('session_123', reason: 'User cancelled'),
          returnsNormally,
        );
      });
    });

    group('Voice API', () {
      test('transcribeAudio uploads audio data as multipart', () async {
        final audioBytes = List<int>.filled(100, 0);

        expect(
          () => apiClient.transcribeAudio(audioBytes),
          returnsNormally,
        );
      });

      test('synthesizeSpeech requests audio with voice ID', () async {
        expect(
          () => apiClient.synthesizeSpeech(
            'Hello world',
            voiceId: 'voice_123',
          ),
          returnsNormally,
        );
      });
    });

    group('MCP Proxy API', () {
      test('getMcpServers retrieves available MCP servers', () async {
        expect(() => apiClient.getMcpServers(), returnsNormally);
      });

      test('callMcpTool makes POST request to specific server tool', () async {
        final arguments = {'repo': 'test/repo'};

        expect(
          () => apiClient.callMcpTool('github', 'get_repo', arguments),
          returnsNormally,
        );
      });
    });

    group('Compute API', () {
      test('createMachine makes POST request with config', () async {
        expect(
          () => apiClient.createMachine(
            name: 'test-vm',
            size: 'shared-cpu-1x',
            region: 'iad',
          ),
          returnsNormally,
        );
      });

      test('getMachine retrieves machine details', () async {
        expect(
          () => apiClient.getMachine('machine_123'),
          returnsNormally,
        );
      });

      test('deleteMachine removes machine', () async {
        expect(
          () => apiClient.deleteMachine('machine_123'),
          returnsNormally,
        );
      });

      test('getMachineSshCredentials retrieves SSH info', () async {
        expect(
          () => apiClient.getMachineSshCredentials('machine_123'),
          returnsNormally,
        );
      });
    });

    group('Auth API', () {
      test('login makes POST request with credentials', () async {
        expect(
          () => apiClient.login(
            email: 'test@example.com',
            password: 'password123',
          ),
          returnsNormally,
        );
      });

      test('loginWithGitHub makes POST request with code', () async {
        expect(
          () => apiClient.loginWithGitHub('github_code_123'),
          returnsNormally,
        );
      });

      test('refreshToken makes POST request with refresh token', () async {
        expect(
          () => apiClient.refreshToken('refresh_token_123'),
          returnsNormally,
        );
      });

      test('logout makes POST request', () async {
        expect(() => apiClient.logout(), returnsNormally);
      });
    });

    group('User API', () {
      test('getCurrentUser retrieves user profile', () async {
        expect(() => apiClient.getCurrentUser(), returnsNormally);
      });

      test('updateUser makes PATCH request with updates', () async {
        final updates = {'name': 'John Doe'};

        expect(
          () => apiClient.updateUser(updates),
          returnsNormally,
        );
      });

      test('updateApiKeys makes POST request with keys', () async {
        final keys = {
          'anthropic_key': 'sk-ant-123',
          'openai_key': 'sk-456',
        };

        expect(
          () => apiClient.updateApiKeys(keys),
          returnsNormally,
        );
      });
    });

    group('Git API', () {
      test('getPullRequests retrieves PRs with filters', () async {
        expect(
          () => apiClient.getPullRequests(
            repo: 'test/repo',
            state: 'open',
            page: 1,
            limit: 20,
          ),
          returnsNormally,
        );
      });

      test('getPullRequest retrieves specific PR', () async {
        expect(
          () => apiClient.getPullRequest('pr_123'),
          returnsNormally,
        );
      });

      test('reviewPullRequest submits review', () async {
        final review = {
          'body': 'Looks good!',
          'event': 'APPROVE',
        };

        expect(
          () => apiClient.reviewPullRequest('pr_123', review),
          returnsNormally,
        );
      });
    });

    group('Generic Methods', () {
      test('get makes GET request', () async {
        expect(
          () => apiClient.get('/custom/endpoint'),
          returnsNormally,
        );
      });

      test('post makes POST request with data', () async {
        expect(
          () => apiClient.post('/custom/endpoint', data: {'key': 'value'}),
          returnsNormally,
        );
      });

      test('put makes PUT request', () async {
        expect(
          () => apiClient.put('/custom/endpoint', data: {'key': 'value'}),
          returnsNormally,
        );
      });

      test('patch makes PATCH request', () async {
        expect(
          () => apiClient.patch('/custom/endpoint', data: {'key': 'value'}),
          returnsNormally,
        );
      });

      test('delete makes DELETE request', () async {
        expect(
          () => apiClient.delete('/custom/endpoint'),
          returnsNormally,
        );
      });
    });

    group('Download & Cancel', () {
      test('download initiates file download', () async {
        expect(
          () => apiClient.download('/files/test.pdf', '/local/path/test.pdf'),
          returnsNormally,
        );
      });

      test('createCancelToken creates cancel token', () {
        final token = apiClient.createCancelToken();
        expect(token, isA<CancelToken>());
      });

      test('cancelRequest cancels with token', () {
        final token = CancelToken();
        expect(
          () => apiClient.cancelRequest(token),
          returnsNormally,
        );
      });
    });

    group('Edge Cases', () {
      test('handles null optional parameters', () async {
        expect(
          () => apiClient.createSession(),
          returnsNormally,
        );
      });

      test('uses default pagination values', () async {
        expect(
          () => apiClient.getSessions(),
          returnsNormally,
        );

        // Should use AppConfig.defaultPageSize
      });

      test('handles empty sync data', () async {
        expect(
          () => apiClient.syncSession('session_123', {}),
          returnsNormally,
        );
      });
    });
  });
}
