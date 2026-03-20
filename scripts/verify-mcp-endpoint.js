#!/usr/bin/env node
/**
 * MCP エンドポイント疎通確認スクリプト
 * Usage: node scripts/verify-mcp-endpoint.js [url]
 */
const http = require('http');
const url = process.argv[2] || 'http://127.0.0.1:8082';

const parsed = new URL(url);
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
  port: parseInt(parsed.port) || 80,
  path: parsed.pathname || '/',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  },
};

console.log(`\n🔍 MCP エンドポイント確認: ${url}`);

const req = http.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => {
    console.log(`✅ HTTP Status: ${res.statusCode}`);
    try {
      const json = JSON.parse(data);
      if (json.result) {
        console.log(`✅ MCP initialize 成功`);
        console.log(`   Server info: ${JSON.stringify(json.result.serverInfo || {})}`);
        console.log(`   protocolVersion: ${json.result.protocolVersion}`);
      } else if (json.error) {
        console.log(`⚠️  MCP error: ${JSON.stringify(json.error)}`);
      } else {
        console.log(`   Response: ${data.slice(0, 200)}`);
      }
    } catch {
      console.log(`   Response (raw): ${data.slice(0, 200)}`);
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
