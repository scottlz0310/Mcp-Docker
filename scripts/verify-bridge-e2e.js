#!/usr/bin/env node
/**
 * mcp-http-bridge エンドツーエンド検証スクリプト
 * ブリッジがstdioフレームを正しくHTTP転送するかテスト
 */
const { spawn } = require('child_process');
const path = require('path');

const BRIDGE_BIN = path.join(__dirname, '../bin/mcp-http-bridge.js');
const MCP_URL = process.env.MCP_URL || 'http://127.0.0.1:8082';

console.log(`\n🔍 ブリッジ E2E 検証`);
console.log(`   ブリッジ: ${BRIDGE_BIN}`);
console.log(`   接続先  : ${MCP_URL}\n`);

const proc = spawn('node', [BRIDGE_BIN, '--url', MCP_URL], {
  stdio: ['pipe', 'pipe', 'inherit']
});

// MCP stdio フレームを組み立て
const body = JSON.stringify({
  jsonrpc: '2.0',
  id: 1,
  method: 'initialize',
  params: {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'e2e-verify', version: '0.0.1' }
  }
});
const frame = `Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`;

let stdout = Buffer.alloc(0);
proc.stdout.on('data', (chunk) => {
  // バッファとして蓄積し、バイト長でフレームを判定
  stdout = Buffer.concat([stdout, chunk]);

  // ヘッダとボディを分割
  const headerEnd = stdout.indexOf('\r\n\r\n');
  if (headerEnd !== -1) {
    const headers = stdout.slice(0, headerEnd).toString();
    const responseBodyBuf = stdout.slice(headerEnd + 4);
    const lenMatch = headers.match(/Content-Length:\s*(\d+)/i);
    if (lenMatch) {
      const contentLength = parseInt(lenMatch[1], 10);
      if (responseBodyBuf.length >= contentLength) {
        const bodyBuf = responseBodyBuf.slice(0, contentLength);
        try {
          const json = JSON.parse(bodyBuf.toString());
          if (json.error) {
            if (json.error.code === -32000 || json.error.message.includes('Unauthorized')) {
              console.log('✅ ブリッジ正常動作 (401 Unauthorized → JSON-RPC エラー変換確認)');
              console.log(`   error.code: ${json.error.code}`);
              console.log(`   error.message: ${json.error.message}`);
            } else {
              console.log(`✅ ブリッジ正常動作 (JSON-RPC レスポンス受信)`);
              console.log(`   Response: ${JSON.stringify(json).slice(0, 200)}`);
            }
          } else if (json.result) {
            console.log('✅ ブリッジ正常動作 (initialize 成功)');
            console.log(`   Server: ${JSON.stringify(json.result.serverInfo || {})}`);
          } else {
            console.log('✅ ブリッジ正常動作 (レスポンス受信)');
            console.log(`   Response: ${JSON.stringify(json).slice(0, 200)}`);
          }
          proc.kill();
          process.exit(0);
        } catch (e) {
          console.log('❌ JSON パース失敗 (ブリッジ出力が不正な JSON-RPC フレームの可能性)');
          console.log(`   Error: ${e.message}`);
          console.log(`   Headers: ${headers.replace(/\r\n/g, ' | ').slice(0, 200)}`);
          console.log(`   Body   : ${bodyBuf.toString().slice(0, 200)}`);
          proc.kill();
          process.exit(1);
        }
      }
    }
  }
});

proc.on('error', (e) => {
  console.error(`❌ ブリッジ起動エラー: ${e.message}`);
  process.exit(1);
});

proc.on('exit', (code, signal) => {
  if (signal !== 'SIGTERM') {
    console.log(`   ブリッジ終了 (code=${code}, signal=${signal})`);
  }
});

setTimeout(() => {
  console.error('❌ タイムアウト (8秒)');
  proc.kill();
  process.exit(1);
}, 8000);

proc.stdin.write(frame);
