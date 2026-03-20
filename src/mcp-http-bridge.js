'use strict';

const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_MAX_FRAME_SIZE_BYTES = 1024 * 1024;
const JSON_RPC_VERSION = '2.0';
const JSON_RPC_PARSE_ERROR = -32700;
const JSON_RPC_SERVER_ERROR = -32000;

function parseArgs(argv) {
  const headers = {};
  let url = '';
  let timeoutMs = DEFAULT_TIMEOUT_MS;
  let maxFrameSizeBytes = DEFAULT_MAX_FRAME_SIZE_BYTES;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    switch (arg) {
      case '--url': {
        const value = argv[index + 1];
        if (!value) {
          throw new Error('Missing value for --url');
        }
        url = value;
        index += 1;
        break;
      }
      case '--header': {
        const value = argv[index + 1];
        if (!value) {
          throw new Error('Missing value for --header');
        }

        const separatorIndex = value.indexOf(':');
        if (separatorIndex <= 0) {
          throw new Error(`Invalid header format: ${value}`);
        }

        const name = value.slice(0, separatorIndex).trim();
        const headerValue = value.slice(separatorIndex + 1).trim();

        if (!name) {
          throw new Error(`Invalid header name: ${value}`);
        }

        headers[name] = headerValue;
        index += 1;
        break;
      }
      case '--timeout': {
        const value = argv[index + 1];
        if (!value) {
          throw new Error('Missing value for --timeout');
        }

        const parsed = Number.parseInt(value, 10);
        if (!Number.isFinite(parsed) || parsed <= 0) {
          throw new Error(`Invalid timeout value: ${value}`);
        }

        timeoutMs = parsed;
        index += 1;
        break;
      }
      case '--max-frame-size': {
        const value = argv[index + 1];
        if (!value) {
          throw new Error('Missing value for --max-frame-size');
        }

        const parsed = Number.parseInt(value, 10);
        if (!Number.isFinite(parsed) || parsed <= 0) {
          throw new Error(`Invalid max frame size value: ${value}`);
        }

        maxFrameSizeBytes = parsed;
        index += 1;
        break;
      }
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!url) {
    throw new Error('Missing required --url');
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch (_error) {
    throw new Error(`Invalid URL: ${url}`);
  }

  if (!/^https?:$/.test(parsedUrl.protocol)) {
    throw new Error(`Unsupported protocol: ${parsedUrl.protocol}`);
  }

  if (!hasHeader(headers, 'content-type')) {
    headers['Content-Type'] = 'application/json';
  }

  if (!hasHeader(headers, 'accept')) {
    headers.Accept = 'application/json';
  }

  return {
    headers,
    maxFrameSizeBytes,
    timeoutMs,
    url: parsedUrl.toString()
  };
}

function hasHeader(headers, targetName) {
  return Object.keys(headers).some((name) => name.toLowerCase() === targetName.toLowerCase());
}

function frameMessage(payload) {
  const content = Buffer.from(payload, 'utf8');
  const header = Buffer.from(
    `Content-Length: ${content.length}\r\nContent-Type: application/json\r\n\r\n`,
    'utf8'
  );
  return Buffer.concat([header, content]);
}

function writeMessage(output, message) {
  output.write(frameMessage(JSON.stringify(message)));
}

function createJsonRpcError(id, code, message, data) {
  const error = {
    jsonrpc: JSON_RPC_VERSION,
    id: id ?? null,
    error: {
      code,
      message
    }
  };

  if (data !== undefined) {
    error.error.data = data;
  }

  return error;
}

function findHeaderBoundary(buffer) {
  const crlfIndex = buffer.indexOf('\r\n\r\n');
  const lfIndex = buffer.indexOf('\n\n');

  if (crlfIndex === -1 && lfIndex === -1) {
    return null;
  }

  if (crlfIndex !== -1 && (lfIndex === -1 || crlfIndex < lfIndex)) {
    return { headerEnd: crlfIndex, separatorLength: 4 };
  }

  return { headerEnd: lfIndex, separatorLength: 2 };
}

function parseHeaders(headerText, maxFrameSizeBytes) {
  const headers = {};
  const lines = headerText.split(/\r?\n/).filter(Boolean);

  for (const line of lines) {
    const separatorIndex = line.indexOf(':');
    if (separatorIndex <= 0) {
      throw new Error(`Malformed header line: ${line}`);
    }

    const name = line.slice(0, separatorIndex).trim().toLowerCase();
    const value = line.slice(separatorIndex + 1).trim();
    headers[name] = value;
  }

  if (!headers['content-length']) {
    throw new Error('Missing Content-Length header');
  }

  const contentLength = Number.parseInt(headers['content-length'], 10);
  if (!Number.isFinite(contentLength) || contentLength < 0) {
    throw new Error(`Invalid Content-Length value: ${headers['content-length']}`);
  }
  if (contentLength > maxFrameSizeBytes) {
    throw new Error(`Content-Length exceeds max frame size: ${contentLength} > ${maxFrameSizeBytes}`);
  }

  return {
    contentLength
  };
}

function getRequestId(request) {
  if (!request || typeof request !== 'object' || Array.isArray(request)) {
    return undefined;
  }

  return Object.prototype.hasOwnProperty.call(request, 'id') ? request.id : undefined;
}

function truncate(text, maxLength = 500) {
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength)}...`;
}

function logError(errorStream, message, error) {
  const suffix = error && error.message ? `: ${error.message}` : '';
  errorStream.write(`[mcp-http-bridge] ${message}${suffix}\n`);
}

async function forwardRequest(rawPayload, options) {
  const response = await fetch(options.url, {
    method: 'POST',
    headers: options.headers,
    body: rawPayload,
    signal: AbortSignal.timeout(options.timeoutMs)
  });

  const contentType = response.headers.get('content-type') || '';
  if (contentType.toLowerCase().startsWith('text/event-stream')) {
    throw new Error('text/event-stream responses are not supported');
  }

  const responseText = await response.text();

  if (!response.ok) {
    const statusLabel = `HTTP ${response.status} ${response.statusText}`.trim();
    const details = responseText.trim();
    throw new Error(details ? `${statusLabel}: ${truncate(details)}` : statusLabel);
  }

  return responseText.trim() ? responseText : null;
}

function startBridge(options, io = {}) {
  const input = io.input ?? process.stdin;
  const output = io.output ?? process.stdout;
  const error = io.error ?? process.stderr;
  const maxFrameSizeBytes = Number.isFinite(options.maxFrameSizeBytes)
    ? options.maxFrameSizeBytes
    : DEFAULT_MAX_FRAME_SIZE_BYTES;

  input.resume();
  const onInputError = (streamError) => {
    logError(error, 'stdin error', streamError);
  };
  input.on('error', onInputError);

  let buffer = Buffer.alloc(0);
  let expectedBodyLength = null;
  const queue = [];
  let processing = false;

  const flushQueue = async () => {
    if (processing) {
      return;
    }

    processing = true;

    try {
      while (queue.length > 0) {
        const rawBuffer = queue.shift();
        const rawPayload = rawBuffer.toString('utf8');

        let request;
        try {
          request = JSON.parse(rawPayload);
        } catch (parseError) {
          logError(error, 'Failed to parse JSON-RPC request', parseError);
          writeMessage(
            output,
            createJsonRpcError(null, JSON_RPC_PARSE_ERROR, 'Failed to parse JSON-RPC request', parseError.message)
          );
          continue;
        }

        try {
          const responseText = await forwardRequest(rawPayload, options);
          if (responseText === null) {
            continue;
          }

          let responsePayload;
          try {
            responsePayload = JSON.parse(responseText);
          } catch (upstreamParseError) {
            logError(error, 'Upstream returned invalid JSON', upstreamParseError);
            const requestId = getRequestId(request);
            if (requestId !== undefined) {
              writeMessage(
                output,
                createJsonRpcError(
                  requestId,
                  JSON_RPC_SERVER_ERROR,
                  'Upstream returned invalid JSON',
                  truncate(responseText)
                )
              );
            }
            continue;
          }

          writeMessage(output, responsePayload);
        } catch (requestError) {
          logError(error, 'HTTP forwarding failed', requestError);
          const requestId = getRequestId(request);
          if (requestId !== undefined) {
            writeMessage(
              output,
              createJsonRpcError(requestId, JSON_RPC_SERVER_ERROR, 'HTTP transport failed', requestError.message)
            );
          }
        }
      }
    } finally {
      processing = false;
    }
  };

  const extractMessages = () => {
    while (true) {
      if (expectedBodyLength === null) {
        const headerBoundary = findHeaderBoundary(buffer);
        if (!headerBoundary) {
          break;
        }

        const headerText = buffer.slice(0, headerBoundary.headerEnd).toString('utf8');
        let parsedHeaders;
        try {
          parsedHeaders = parseHeaders(headerText, maxFrameSizeBytes);
        } catch (frameError) {
          logError(error, 'Invalid MCP stdio frame', frameError);
          writeMessage(
            output,
            createJsonRpcError(null, JSON_RPC_PARSE_ERROR, 'Invalid MCP stdio frame', frameError.message)
          );
          buffer = Buffer.alloc(0);
          expectedBodyLength = null;
          break;
        }

        expectedBodyLength = parsedHeaders.contentLength;
        buffer = buffer.slice(headerBoundary.headerEnd + headerBoundary.separatorLength);
      }

      if (buffer.length < expectedBodyLength) {
        break;
      }

      queue.push(buffer.slice(0, expectedBodyLength));
      buffer = buffer.slice(expectedBodyLength);
      expectedBodyLength = null;
    }

    flushQueue().catch((unexpectedError) => {
      logError(error, 'Unexpected bridge error', unexpectedError);
    });
  };

  const onData = (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    extractMessages();
  };

  const onEnd = () => {
    if (buffer.length > 0) {
      logError(error, 'stdin closed with an incomplete MCP frame');
    }
  };

  input.on('data', onData);
  input.on('end', onEnd);

  return {
    close() {
      input.off('data', onData);
      input.off('end', onEnd);
      input.off('error', onInputError);
      if (typeof input.pause === 'function') {
        input.pause();
      }
    }
  };
}

module.exports = {
  DEFAULT_MAX_FRAME_SIZE_BYTES,
  DEFAULT_TIMEOUT_MS,
  parseArgs,
  startBridge,
  frameMessage
};
