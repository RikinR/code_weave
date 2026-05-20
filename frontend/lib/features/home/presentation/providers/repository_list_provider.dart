import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../domain/repository_summary.dart';

class RepositoryListProvider extends ChangeNotifier {
  RepositoryListProvider(this._api);

  final ApiClient _api;

  List<RepositorySummary> repositories = [];
  List<String> supportedLanguages = [];
  bool loading = false;
  bool deleting = false;
  String? error;

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
