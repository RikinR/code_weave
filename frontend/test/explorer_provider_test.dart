/// Tests for [ExplorerProvider] graph selection, node detail, and chat state.
library;
import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/core/network/api_client.dart';
import 'package:code_weave_frontend/features/explorer/presentation/providers/explorer_provider.dart';

class _StubApi extends ApiClient {
  _StubApi(this._chatByRepo);

  final Map<String, List<Map<String, dynamic>>> _chatByRepo;
  final Map<String, Map<String, dynamic>> _hierarchyByRepo = {};
  final Map<String, Map<String, dynamic>> _graphByRepo = {};

  void seedRepo({
    required String repoId,
    List<Map<String, dynamic>>? messages,
    String rootId = 'root',
  }) {
    _chatByRepo[repoId] = messages ?? [];
    _hierarchyByRepo[repoId] = {
      'root_id': rootId,
      'nodes': [
        {
          'id': rootId,
          'type': 'folder',
          'name': repoId,
          'parent_id': null,
          'children': [],
        },
      ],
    };
    _graphByRepo[repoId] = {'edges': []};
  }

  @override
  Future<List<dynamic>> getChatMessages(String repositoryId) async {
    return _chatByRepo[repositoryId] ?? [];
  }

  @override
  Future<Map<String, dynamic>> getHierarchy(String repositoryId) async {
    return _hierarchyByRepo[repositoryId]!;
  }

  @override
  Future<Map<String, dynamic>> getGraph(String repositoryId) async {
    return _graphByRepo[repositoryId]!;
  }
}

void main() {
  test('load replaces chat history when switching repositories', () async {
    final api = _StubApi({});
    api.seedRepo(
      repoId: 'repo-a',
      messages: [
        {'role': 'user', 'content': 'Question for A', 'citations': []},
      ],
    );
    api.seedRepo(
      repoId: 'repo-b',
      messages: [
        {'role': 'user', 'content': 'Question for B', 'citations': []},
      ],
    );

    final provider = ExplorerProvider(api);

    await provider.load('repo-a');
    expect(provider.messages.length, 1);
    expect(provider.messages.first.text, 'Question for A');

    await provider.load('repo-b');
    expect(provider.messages.length, 1);
    expect(provider.messages.first.text, 'Question for B');
  });
}
