/// Typed HTTP client for the Code Weave FastAPI backend.
///
/// Wraps Dio with shared timeouts and exposes REST methods used by home
/// (repositories), pipeline (jobs), and explorer (graph, chat) features.
library;
import 'package:dio/dio.dart';
import '../config/api_config.dart';

/// Default receive timeout for most API calls.
const Duration kApiDefaultReceiveTimeout = Duration(seconds: 90);

/// Extended receive timeout for long-running operations (graph, delete, chat).
const Duration kApiLongReceiveTimeout = Duration(minutes: 30);

/// Send timeout for large zip uploads.
const Duration kApiUploadSendTimeout = Duration(minutes: 30);

/// Dio-based client for all backend REST endpoints.
class ApiClient {
  /// Creates a client pointed at [ApiConfig.baseUrl] with standard timeouts.
  ApiClient()
      : dio = Dio(
          BaseOptions(
            baseUrl: ApiConfig.baseUrl,
            connectTimeout: const Duration(seconds: 30),
            receiveTimeout: kApiDefaultReceiveTimeout,
            sendTimeout: const Duration(seconds: 90),
          ),
        );

  /// Underlying Dio instance for advanced use.
  final Dio dio;

  /// Lists indexed repositories. Calls `GET /api/repositories`.
  Future<List<dynamic>> listRepositories() async {
    final res = await dio.get('/api/repositories');
    return res.data as List<dynamic>;
  }

  /// Fetches a single repository summary. Calls `GET /api/repositories/{id}`.
  Future<Map<String, dynamic>> getRepository(String id) async {
    final res = await dio.get('/api/repositories/$id');
    return res.data as Map<String, dynamic>;
  }

  /// Deletes a repository and all indexed data. Calls `DELETE /api/repositories/{id}`.
  Future<void> deleteRepository(String id) async {
    await dio.delete(
      '/api/repositories/$id',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
  }

  /// Uploads a zip archive and starts indexing. Calls `POST /api/repositories/upload`.
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

  /// Fetches job status and stage snapshot. Calls `GET /api/jobs/{jobId}`.
  Future<Map<String, dynamic>> getJob(String jobId) async {
    final res = await dio.get('/api/jobs/$jobId');
    return res.data as Map<String, dynamic>;
  }

  /// Retries an interrupted indexing job. Calls `POST /api/jobs/{jobId}/retry`.
  Future<Map<String, dynamic>> retryJob(String jobId) async {
    final res = await dio.post(
      '/api/jobs/$jobId/retry',
      options: Options(receiveTimeout: const Duration(minutes: 5)),
    );
    return res.data as Map<String, dynamic>;
  }

  /// Lists Tree-sitter languages supported by the backend. Calls `GET /api/languages/supported`.
  Future<List<String>> supportedLanguages() async {
    final res = await dio.get('/api/languages/supported');
    final data = res.data as Map<String, dynamic>;
    return (data['languages'] as List<dynamic>).cast<String>();
  }

  /// Fetches repository hierarchy nodes. Calls `GET /api/repositories/{id}/hierarchy`.
  Future<Map<String, dynamic>> getHierarchy(String repositoryId) async {
    final res = await dio.get(
      '/api/repositories/$repositoryId/hierarchy',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
    return res.data as Map<String, dynamic>;
  }

  /// Fetches call-graph edges for a repository. Calls `GET /api/repositories/{id}/graph`.
  Future<Map<String, dynamic>> getGraph(String repositoryId) async {
    final res = await dio.get(
      '/api/repositories/$repositoryId/graph',
      options: Options(receiveTimeout: kApiLongReceiveTimeout),
    );
    return res.data as Map<String, dynamic>;
  }

  /// Fetches detail for a graph node (code, calls, AST). Calls `GET /api/nodes/{nodeId}`.
  Future<Map<String, dynamic>> getNodeDetail(String nodeId) async {
    final encoded = Uri.encodeComponent(nodeId);
    final res = await dio.get('/api/nodes/$encoded');
    return res.data as Map<String, dynamic>;
  }

  /// Loads persisted chat history. Calls `GET /api/repositories/{id}/chat/messages`.
  Future<List<dynamic>> getChatMessages(String repositoryId) async {
    final res = await dio.get('/api/repositories/$repositoryId/chat/messages');
    return res.data as List<dynamic>;
  }

  /// Sends a synchronous RAG chat query (fallback when SSE fails).
  /// Calls `POST /api/repositories/{id}/chat/sync`.
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
