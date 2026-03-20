'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const { once } = require('node:events');
const test = require('node:test');
const { PassThrough } = require('node:stream');
const { frameMessage, startBridge } = require('../../src/mcp-http-bridge');

function readFramedMessage(stream) {
  return new Promise((resolve, reject) => {
    let buffer = Buffer.alloc(0);

    const cleanup = () => {
      stream.off('data', onData);
      stream.off('error', onError);
      stream.off('end', onEnd);
    };

    const onError = (error) => {
      cleanup();
      reject(error);
    };

    const onEnd = () => {
      cleanup();
      reject(new Error('Stream ended before a complete frame was received'));
    };

    const onData = (chunk) => {
      buffer = Buffer.concat([buffer, chunk]);
      const headerBoundary = buffer.indexOf('\r\n\r\n');
      if (headerBoundary === -1) {
        return;
      }

      const headerText = buffer.slice(0, headerBoundary).toString('utf8');
      const contentLengthLine = headerText
        .split(/\r?\n/)
        .find((line) => line.toLowerCase().startsWith('content-length:'));

      if (!contentLengthLine) {
        return;
      }

      const contentLength = Number.parseInt(contentLengthLine.split(':')[1].trim(), 10);
      const frameLength = headerBoundary + 4 + contentLength;
      if (buffer.length < frameLength) {
        return;
      }

      const body = buffer.slice(headerBoundary + 4, frameLength).toString('utf8');
      cleanup();
      resolve(JSON.parse(body));
    };

    stream.on('data', onData);
    stream.on('error', onError);
    stream.on('end', onEnd);
  });
}

async function startServer(handler) {
  const server = http.createServer(handler);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();

  return {
    server,
    url: `http://127.0.0.1:${address.port}/mcp`
  };
}

test('forwards a stdio JSON-RPC frame to HTTP and returns the upstream response', async () => {
  const receivedRequests = [];
  const { server, url } = await startServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }

    receivedRequests.push(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ jsonrpc: '2.0', id: 1, result: { ok: true } }));
  });

  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();
  const bridge = startBridge(
    {
      url,
      timeoutMs: 5000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      }
    },
    { input, output, error }
  );

  try {
    const responsePromise = readFramedMessage(output);

    input.write(
      frameMessage(
        JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'tools/list',
          params: {}
        })
      )
    );

    const response = await responsePromise;
    assert.deepEqual(response, { jsonrpc: '2.0', id: 1, result: { ok: true } });
    assert.deepEqual(receivedRequests, [
      {
        jsonrpc: '2.0',
        id: 1,
        method: 'tools/list',
        params: {}
      }
    ]);
  } finally {
    bridge.close();
    input.end();
    output.end();
    error.end();
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test('returns a JSON-RPC error when the upstream HTTP request fails', async () => {
  const { server, url } = await startServer(async (_req, res) => {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('bad gateway');
  });

  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();
  const bridge = startBridge(
    {
      url,
      timeoutMs: 5000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      }
    },
    { input, output, error }
  );

  try {
    const responsePromise = readFramedMessage(output);

    input.write(
      frameMessage(
        JSON.stringify({
          jsonrpc: '2.0',
          id: 7,
          method: 'initialize',
          params: {}
        })
      )
    );

    const response = await responsePromise;
    assert.equal(response.jsonrpc, '2.0');
    assert.equal(response.id, 7);
    assert.equal(response.error.code, -32000);
    assert.equal(response.error.message, 'HTTP transport failed');
    assert.match(response.error.data, /HTTP 502 Bad Gateway/i);
  } finally {
    bridge.close();
    input.end();
    output.end();
    error.end();
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test('close removes input listeners including error handler', () => {
  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();

  const bridge = startBridge(
    {
      url: 'http://127.0.0.1:65535/mcp',
      timeoutMs: 100,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      }
    },
    { input, output, error }
  );

  assert.equal(input.listenerCount('error'), 1);
  assert.equal(input.listenerCount('data'), 1);
  assert.equal(input.listenerCount('end'), 1);

  bridge.close();

  assert.equal(input.listenerCount('error'), 0);
  assert.equal(input.listenerCount('data'), 0);
  assert.equal(input.listenerCount('end'), 0);
  input.end();
  output.end();
  error.end();
});

test('forwards SSE (text/event-stream) response and emits multiple framed JSON-RPC messages', async () => {
  const msg1 = JSON.stringify({ jsonrpc: '2.0', id: 1, result: { tool: 'first' } });
  const msg2 = JSON.stringify({ jsonrpc: '2.0', id: 2, result: { tool: 'second' } });

  const { server, url } = await startServer(async (_req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/event-stream' });
    res.write(`data: ${msg1}\n\n`);
    res.write(`data: ${msg2}\n\n`);
    res.end();
  });

  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();
  const bridge = startBridge(
    {
      url,
      timeoutMs: 5000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json, text/event-stream'
      }
    },
    { input, output, error }
  );

  try {
    // Register listener before writing to ensure no data is missed.
    const firstPromise = readFramedMessage(output);

    input.write(
      frameMessage(
        JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'tools/call',
          params: { name: 'test' }
        })
      )
    );

    // Await first message; the bridge writes both messages synchronously so the
    // second frame is buffered in the stream by the time we set up the next read.
    assert.deepEqual(await firstPromise, { jsonrpc: '2.0', id: 1, result: { tool: 'first' } });
    assert.deepEqual(await readFramedMessage(output), { jsonrpc: '2.0', id: 2, result: { tool: 'second' } });
  } finally {
    bridge.close();
    input.end();
    output.end();
    error.end();
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test('returns a JSON-RPC transport error when SSE upstream responds with non-2xx status', async () => {
  const { server, url } = await startServer(async (_req, res) => {
    res.writeHead(401, { 'Content-Type': 'text/event-stream' });
    res.end('Unauthorized');
  });

  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();
  const bridge = startBridge(
    {
      url,
      timeoutMs: 5000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json, text/event-stream'
      }
    },
    { input, output, error }
  );

  try {
    const responsePromise = readFramedMessage(output);

    input.write(
      frameMessage(
        JSON.stringify({
          jsonrpc: '2.0',
          id: 9,
          method: 'initialize',
          params: {}
        })
      )
    );

    const response = await responsePromise;
    assert.equal(response.jsonrpc, '2.0');
    assert.equal(response.id, 9);
    assert.equal(response.error.code, -32000);
    assert.equal(response.error.message, 'HTTP transport failed');
    assert.match(response.error.data, /HTTP 401/i);
  } finally {
    bridge.close();
    input.end();
    output.end();
    error.end();
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test('returns parse error when frame exceeds max frame size', async () => {
  const input = new PassThrough();
  const output = new PassThrough();
  const error = new PassThrough();
  const bridge = startBridge(
    {
      url: 'http://127.0.0.1:65535/mcp',
      timeoutMs: 100,
      maxFrameSizeBytes: 8,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      }
    },
    { input, output, error }
  );

  try {
    const responsePromise = readFramedMessage(output);
    input.write(Buffer.from('Content-Length: 9\r\n\r\n123456789', 'utf8'));

    const response = await responsePromise;
    assert.equal(response.error.code, -32700);
    assert.equal(response.error.message, 'Invalid MCP stdio frame');
    assert.match(response.error.data, /exceeds max frame size/i);
  } finally {
    bridge.close();
    input.end();
    output.end();
    error.end();
  }
});
