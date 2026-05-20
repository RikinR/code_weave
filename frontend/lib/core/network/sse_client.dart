import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../config/api_config.dart';

typedef SseHandler = void Function(String event, Map<String, dynamic> data);

Future<void> listenSse(
  String path, {
  required SseHandler onEvent,
  void Function(Object error)? onError,
  void Function()? onDone,
  String method = 'GET',
  Map<String, dynamic>? body,
  Duration receiveTimeout = const Duration(hours: 2),
}) async {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      responseType: ResponseType.stream,
      receiveTimeout: receiveTimeout,
      connectTimeout: const Duration(seconds: 30),
      headers: {
        'Accept': 'text/event-stream',
        if (body != null) 'Content-Type': 'application/json',
      },
    ),
  );

  try {
    final Response<ResponseBody> response;
    if (method.toUpperCase() == 'POST') {
      response = await dio.post<ResponseBody>(
        path,
        data: body == null ? null : jsonEncode(body),
      );
    } else {
      response = await dio.get<ResponseBody>(path);
    }

    final status = response.statusCode ?? 0;
    if (status < 200 || status >= 300) {
      throw DioException(
        requestOptions: response.requestOptions,
        response: response,
        message: 'SSE request failed with status $status',
      );
    }

    final stream = response.data?.stream;
    if (stream == null) {
      onDone?.call();
      return;
    }

    final decoder = utf8.decoder;
    var buffer = '';

    await for (final chunk in stream) {
      buffer += decoder.convert(chunk);
      buffer = _dispatchSseBlocks(buffer, onEvent);
    }
    if (buffer.trim().isNotEmpty) {
      _dispatchSseBlocks('$buffer\n\n', onEvent);
    }
    onDone?.call();
  } catch (e) {
    if (onError != null) {
      onError(e);
      return;
    }
    rethrow;
  }
}

String _dispatchSseBlocks(String buffer, SseHandler onEvent) {
  while (buffer.contains('\n\n')) {
    final index = buffer.indexOf('\n\n');
    final block = buffer.substring(0, index);
    buffer = buffer.substring(index + 2);

    String? eventName;
    final dataLines = <String>[];
    for (final line in block.split('\n')) {
      if (line.startsWith('event:')) {
        eventName = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.add(line.substring(5).trim());
      }
    }
    if (dataLines.isEmpty) continue;
    final raw = dataLines.join('\n');
    Map<String, dynamic> data;
    try {
      final decoded = jsonDecode(raw);
      data = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{'value': decoded};
    } catch (_) {
      data = {'raw': raw};
    }
    onEvent(eventName ?? 'message', data);
  }
  return buffer;
}
