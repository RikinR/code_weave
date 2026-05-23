import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/sse_client.dart';
import '../../domain/pipeline_stage.dart';

class PipelineProvider extends ChangeNotifier {
  PipelineProvider(this._api);

  final ApiClient _api;

  String? jobId;
  String? repositoryName;
  String? repositoryId;
  String status = 'pending';
  String? error;
  List<PipelineStage> stages = [];

  DateTime? _startedAt;
  DateTime? _lastEventAt;
  Timer? _uiTicker;
  Timer? _pollTimer;
  Timer? _notifyDebounce;
  int _session = 0;

  PipelineStage? get runningStage {
    for (final stage in stages) {
      if (stage.status == 'running') return stage;
    }
    return null;
  }

  String get activeStageLabel {
    final running = runningStage;
    if (running != null) return running.label;
    if (status == 'completed') return 'Indexing complete';
    if (status == 'failed') return 'Indexing failed';
    for (final stage in stages) {
      if (stage.status == 'pending') return stage.label;
    }
    return 'Preparing pipeline';
  }

  String? get lastLog {
    final running = runningStage;
    if (running == null || running.logs.isEmpty) return null;
    return running.logs.last;
  }

  String get elapsedLabel {
    if (_startedAt == null) return '0:00';
    final seconds = DateTime.now().difference(_startedAt!).inSeconds;
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  String get activityHint {
    if (status == 'failed') {
      return 'Indexing stopped. Retry below or upload again from home.';
    }
    if (_lastEventAt == null) {
      return 'Starting ingestion pipeline…';
    }
    final idle = DateTime.now().difference(_lastEventAt!).inSeconds;
    if (idle >= 8) {
      return 'Large repos and first-time embedding downloads can take several minutes. Still working…';
    }
    return 'Live updates from the server. Stages advance as parsing and indexing complete.';
  }

  bool get isInterrupted =>
      status == 'failed' &&
      (error?.toLowerCase().contains('interrupted') ?? false);

  bool get canRetry => isInterrupted;

  void prepareForJob(String id, {String? repoName}) {
    _uiTicker?.cancel();
    _pollTimer?.cancel();
    _notifyDebounce?.cancel();
    jobId = id;
    repositoryName = repoName;
    repositoryId = null;
    status = 'pending';
    error = null;
    stages = [];
    _startedAt = null;
    _lastEventAt = null;
  }

  Future<void> start(String id, {String? repoName}) async {
    _session++;
    final session = _session;

    prepareForJob(id, repoName: repoName);
    _startedAt = DateTime.now();
    _lastEventAt = _startedAt;

    _uiTicker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_session != session) return;
      notifyListeners();
    });

    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (_session != session) return;
      if (status != 'pending' && status != 'running') return;
      _refresh(session);
    });

    _notify();
    await _refresh(session);
    if (_session != session) return;
    _listen(session);
  }

  @override
  void dispose() {
    _session++;
    _uiTicker?.cancel();
    _pollTimer?.cancel();
    _notifyDebounce?.cancel();
    super.dispose();
  }

  void _notify() {
    _notifyDebounce?.cancel();
    _notifyDebounce = Timer(const Duration(milliseconds: 80), () {
      _notifyDebounce = null;
      notifyListeners();
    });
  }

  Future<void> _refresh(int session) async {
    if (jobId == null || _session != session) return;
    try {
      final data = await _api.getJob(jobId!);
      if (_session != session) return;
      _applySnapshot(data);
    } catch (e) {
      if (_session != session) return;
      if (_isJobNotFound(e)) {
        await Future<void>.delayed(const Duration(milliseconds: 400));
        if (_session != session) return;
        try {
          final data = await _api.getJob(jobId!);
          if (_session != session) return;
          _applySnapshot(data);
          _notify();
          return;
        } catch (_) {
        }
      }
      error = _friendlyNetworkError(e);
    }
    _notify();
  }

  static bool _isJobNotFound(Object e) {
    if (e is! DioException || e.response?.statusCode != 404) return false;
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString().toLowerCase().contains('job not found');
    }
    return true;
  }

  void _listen(int session) {
    if (jobId == null || _session != session) return;
    listenSse(
      '/api/jobs/$jobId/events',
      receiveTimeout: const Duration(hours: 2),
      onEvent: (event, data) {
        if (_session != session) return;
        if (data.containsKey('stages')) {
          _applySnapshot(data);
          _notify();
        }
      },
      onError: (e) {
        if (_session != session) return;
        error = _friendlyNetworkError(e);
        _notify();
      },
      onDone: () {
        if (_session != session) return;
        _notify();
      },
    );
  }

  static String _friendlyNetworkError(Object e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
      if (e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.connectionTimeout) {
        return 'Lost connection to the server while waiting for updates. '
            'Indexing may still be running — refresh the page or check the backend logs.';
      }
    }
    final msg = e.toString();
    if (msg.contains('receive timeout') || msg.contains('ReceiveTimeout')) {
      return 'Lost connection to the server while waiting for updates. '
          'Indexing may still be running — refresh the page or check the backend logs.';
    }
    return msg;
  }

  Future<bool> retry() async {
    if (jobId == null || !canRetry) return false;
    _session++;
    final session = _session;
    try {
      final data = await _api.retryJob(jobId!);
      if (_session != session) return false;
      _applySnapshot(data);
      _startedAt = DateTime.now();
      _lastEventAt = _startedAt;
      _uiTicker?.cancel();
      _pollTimer?.cancel();
      _uiTicker = Timer.periodic(const Duration(seconds: 1), (_) {
        if (_session != session) return;
        notifyListeners();
      });
      _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
        if (_session != session) return;
        if (status != 'pending' && status != 'running') return;
        _refresh(session);
      });
      _listen(session);
      _notify();
      return true;
    } catch (e) {
      if (_session != session) return false;
      error = e.toString();
      _notify();
      return false;
    }
  }

  void _applySnapshot(Map<String, dynamic> data) {
    _lastEventAt = DateTime.now();
    status = data['status'] as String? ?? status;
    repositoryId = data['repository_id'] as String?;
    error = data['error'] as String?;
    stages = (data['stages'] as List<dynamic>? ?? [])
        .map((e) => PipelineStage.fromJson(e as Map<String, dynamic>))
        .toList();
    if (status == 'completed' || status == 'failed') {
      _uiTicker?.cancel();
      _pollTimer?.cancel();
    }
  }
}
