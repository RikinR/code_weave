/// Provider for live indexing job progress on the pipeline screen.
///
/// Holds job id, status, stages, and repository id on completion. Polls
/// `GET /api/jobs/{id}`, streams `GET /api/jobs/{id}/events` via SSE, and
/// calls `POST /api/jobs/{id}/retry` when a job was interrupted.
library;
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/sse_client.dart';
import '../../domain/pipeline_stage.dart';

/// ChangeNotifier backing [PipelineScreen] stage list and progress UI.
class PipelineProvider extends ChangeNotifier {
  PipelineProvider(this._api);

  final ApiClient _api;

  /// Active indexing job identifier from upload or route.
  String? jobId;

  /// Display name passed from upload or query parameter.
  String? repositoryName;

  /// Set when indexing completes; used to navigate to explorer.
  String? repositoryId;

  /// Job status: `pending`, `running`, `completed`, or `failed`.
  String status = 'pending';

  /// Error detail when [status] is `failed`.
  String? error;

  /// True while a retry request is in flight.
  bool retrying = false;

  /// Ordered ingestion stages with progress and logs.
  List<PipelineStage> stages = [];

  DateTime? _startedAt;
  DateTime? _lastEventAt;
  Timer? _uiTicker;
  Timer? _pollTimer;
  Timer? _notifyDebounce;
  int _session = 0;

  /// The stage currently marked `running`, if any.
  PipelineStage? get runningStage {
    for (final stage in stages) {
      if (stage.status == 'running') return stage;
    }
    return null;
  }

  /// Human-readable label for the active or next pipeline stage.
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

  /// Most recent log line from the running stage.
  String? get lastLog {
    final running = runningStage;
    if (running == null || running.logs.isEmpty) return null;
    return running.logs.last;
  }

  /// Elapsed time since job start, formatted as `m:ss`.
  String get elapsedLabel {
    if (_startedAt == null) return '0:00';
    final seconds = DateTime.now().difference(_startedAt!).inSeconds;
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  /// Contextual hint shown under the processing banner.
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

  /// True when failure was caused by a backend restart during indexing.
  bool get isInterrupted =>
      status == 'failed' &&
      (error?.toLowerCase().contains('interrupted') ?? false);

  /// Retry is only offered for interrupted jobs.
  bool get canRetry => isInterrupted;

  /// Resets state for a new [id] without starting polling or SSE.
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

  /// Starts polling, SSE, and UI timers for job [id].
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

  /// Retries an interrupted job. Returns true if retry started successfully.
  Future<bool> retry() async {
    if (jobId == null || !canRetry) return false;
    _session++;
    final session = _session;
    retrying = true;
    _notify();
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
    } finally {
      if (_session == session) {
        retrying = false;
        _notify();
      }
    }
  }

  /// Progress fraction (0–1) from the running stage, if available.
  double? get overallProgress {
    final running = runningStage;
    if (running == null || running.progress <= 0) return null;
    return running.progress / 100;
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
