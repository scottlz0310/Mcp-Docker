#!/usr/bin/env node
/**
 * MCP エンドポイント疎通確認スクリプト
 * Usage: node scripts/verify-mcp-endpoint.js [url]
 */
const http = require('http');
const https = require('https');
const url = process.argv[2] || 'http://127.0.0.1:8082';

const parsed = new URL(url);
const isHttps = parsed.protocol === 'https:';
const transport = isHttps ? https : http;
const body = JSON.stringify({
  jsonrpc: '2.0',
  id: 1,
  method: 'initialize',
  params: {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'verify-script', version: '0.0.1' }
  }
});

const options = {
  hostname: parsed.hostname,
  port: parseInt(parsed.port) || (isHttps ? 443 : 80),
  path: (parsed.pathname || '/') + (parsed.search || ''),
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  },
};

console.log(`\n🔍 MCP エンドポイント確認: ${url}`);

const req = transport.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => {
    const status = res.statusCode || 0;

    if (status < 200 || status >= 300) {
      console.error(`❌ HTTP Status: ${status}`);
      if (data) {
        console.error(`   Response body (first 200 chars): ${data.slice(0, 200)}`);
      }
      process.exit(1);
    }

    console.log(`✅ HTTP Status: ${status}`);
    try {
      const json = JSON.parse(data);
      const hasValidResult =
        json &&
        typeof json === 'object' &&
        json.result &&
        typeof json.result === 'object' &&
        typeof json.result.protocolVersion === 'string';

      if (hasValidResult) {
        console.log(`✅ MCP initialize 成功`);
        console.log(`   Server info: ${JSON.stringify(json.result.serverInfo || {})}`);
        console.log(`   protocolVersion: ${json.result.protocolVersion}`);
        process.exit(0);
      } else if (json && typeof json === 'object' && json.error) {
        console.error(`❌ MCP error: ${JSON.stringify(json.error)}`);
        process.exit(1);
      } else {
        console.error('❌ レスポンスが有効な JSON-RPC initialize 結果ではありません。');
        console.error(`   Response (first 200 chars): ${data.slice(0, 200)}`);
        process.exit(1);
      }
    } catch (err) {
      console.error('❌ レスポンスの JSON パースに失敗しました。');
      if (err && err.message) {
        console.error(`   Error: ${err.message}`);
      }
      console.error(`   Response (raw, first 200 chars): ${data.slice(0, 200)}`);
      process.exit(1);
    }
  });
});

req.on('error', (e) => {
  console.error(`❌ 接続エラー: ${e.message}`);
  if (e.code === 'ECONNREFUSED') {
    console.error('   コンテナが起動していない可能性があります。');
    console.error('   make start-custom を実行してください。');
  }
  process.exit(1);
});

req.setTimeout(5000, () => {
  console.error('❌ タイムアウト (5秒)');
  req.destroy();
  process.exit(1);
});

req.write(body);
req.end();
