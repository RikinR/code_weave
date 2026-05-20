import 'package:dio/dio.dart';
import '../config/api_config.dart';

const Duration kApiDefaultReceiveTimeout = Duration(seconds: 90);

const Duration kApiLongReceiveTimeout = Duration(minutes: 30);

const Duration kApiUploadSendTimeout = Duration(minutes: 30);

class ApiClient {
  ApiClient()
      : dio = Dio(
          BaseOptions(
            baseUrl: ApiConfig.baseUrl,
            connectTimeout: const Duration(seconds: 30),
            receiveTimeout: kApiDefaultReceiveTimeout,
            sendTimeout: const Duration(seconds: 90),
          ),
        );

  final Dio dio;

  Future<List<dynamic>> listRepositories() async {
    final res = await dio.get('/api/repositories');
    return res.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> getRepository(String id) async {
    final res = await dio.get('/api/repositories/$id');
    return res.data as Map<String, dynamic>;
  }

  Future<void> deleteRepository(String id) async {
    await dio.delete(
      '/api/repositories/$id',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
  }

  Future<Map<String, dynamic>> uploadZip({
    required String fileName,
    required List<int> bytes,
    String? name,
  }) async {
    final fields = <String, dynamic>{
      'file': MultipartFile.fromBytes(bytes, filename: fileName),
    };
    if (name != null) {
      fields['name'] = name;
    }
    final form = FormData.fromMap(fields);
    final res = await dio.post(
      '/api/repositories/upload',
      data: form,
      options: Options(
        sendTimeout: kApiUploadSendTimeout,
        receiveTimeout: const Duration(minutes: 5),
      ),
    );
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getJob(String jobId) async {
    final res = await dio.get('/api/jobs/$jobId');
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> retryJob(String jobId) async {
    final res = await dio.post(
      '/api/jobs/$jobId/retry',
      options: Options(receiveTimeout: const Duration(minutes: 5)),
    );
    return res.data as Map<String, dynamic>;
  }

  Future<List<String>> supportedLanguages() async {
    final res = await dio.get('/api/languages/supported');
    final data = res.data as Map<String, dynamic>;
    return (data['languages'] as List<dynamic>).cast<String>();
  }

  Future<Map<String, dynamic>> getHierarchy(String repositoryId) async {
    final res = await dio.get(
      '/api/repositories/$repositoryId/hierarchy',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getGraph(String repositoryId) async {
    final res = await dio.get(
      '/api/repositories/$repositoryId/graph',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getNodeDetail(String nodeId) async {
    final encoded = Uri.encodeComponent(nodeId);
    final res = await dio.get('/api/nodes/$encoded');
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> chatSync({
    required String repositoryId,
    required String query,
    int topK = 5,
    bool beginnerMode = false,
  }) async {
    final res = await dio.post(
      '/api/repositories/$repositoryId/chat/sync',
      data: {
        'query': query,
        'top_k': topK,
        'beginner_mode': beginnerMode,
      },
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
    return res.data as Map<String, dynamic>;
  }
}
