import 'package:dio/dio.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

@GenerateMocks([Dio, Response, RequestOptions])
class MockDio extends Mock implements Dio {}

class MockResponse<T> extends Mock implements Response<T> {}

class MockRequestOptions extends Mock implements RequestOptions {}
