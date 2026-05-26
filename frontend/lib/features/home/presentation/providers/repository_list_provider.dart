/// Provider for the home screen repository list and supported languages.
///
/// Holds indexed repository summaries and loading/delete state. Calls
/// `GET /api/repositories`, `GET /api/languages/supported`, and
/// `DELETE /api/repositories/{id}` via [ApiClient].
library;
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../domain/repository_summary.dart';

/// ChangeNotifier backing [HomeScreen] repository grid and language sidebar.
class RepositoryListProvider extends ChangeNotifier {
  RepositoryListProvider(this._api);

  final ApiClient _api;

  /// Indexed repositories shown on the home grid.
  List<RepositorySummary> repositories = [];

  /// Tree-sitter languages reported by the backend.
  List<String> supportedLanguages = [];

  /// True while fetching the repository list.
  bool loading = false;

  /// True while a delete request is in flight.
  bool deleting = false;

  /// Last error message from load or delete, if any.
  String? error;

  /// True when [loading] or [deleting].
  bool get isBusy => loading || deleting;

  /// Message shown in the progress overlay while busy.
  String get busyMessage {
    if (deleting) return 'Deleting repository…';
    if (loading) return 'Loading repositories…';
    return 'Working…';
  }

  /// Reloads repositories and supported languages from the backend.
  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final repos = await _api.listRepositories();
      repositories =
          repos.map((e) => RepositorySummary.fromJson(e as Map<String, dynamic>)).toList();
      supportedLanguages = await _api.supportedLanguages();
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Deletes a repository by [id]. Returns true on success.
  Future<bool> deleteRepository(String id) async {
    deleting = true;
    error = null;
    notifyListeners();
    try {
      await _api.deleteRepository(id);
      repositories = repositories.where((r) => r.id != id).toList();
      return true;
    } catch (e) {
      error = e.toString();
      return false;
    } finally {
      deleting = false;
      notifyListeners();
    }
  }
}
