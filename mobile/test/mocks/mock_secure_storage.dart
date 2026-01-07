import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:paraclete/core/storage/secure_storage.dart';

@GenerateMocks([SecureStorageService])
class MockSecureStorageService extends Mock implements SecureStorageService {}
