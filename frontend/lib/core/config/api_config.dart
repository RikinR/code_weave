/// Backend base URL configuration for HTTP and SSE clients.
///
/// Reads `API_BASE_URL` from compile-time environment variables and defaults
/// to the local FastAPI server used during development.
library;
class ApiConfig {
  /// Base URL for all REST and SSE requests to the Code Weave backend.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );
}
