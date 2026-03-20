#!/usr/bin/env node

'use strict';

const process = require('node:process');
const { DEFAULT_TIMEOUT_MS, parseArgs, startBridge } = require('../src/mcp-http-bridge');

function printUsage() {
  process.stdout.write(`mcp-http-bridge

Usage:
  mcp-http-bridge --url <http-url> [--header "Name: Value"]... [--timeout <ms>] [--max-frame-size <bytes>]
  mcp-http-bridge --help
  mcp-http-bridge --version

Options:
  --url       MCP HTTP endpoint URL. Required.
  --header    Additional HTTP header. Repeatable. Example: --header "Authorization: Bearer token"
  --timeout   Request timeout in milliseconds. Default: ${DEFAULT_TIMEOUT_MS}
  --max-frame-size   Maximum accepted MCP frame size in bytes. Default: 1048576
  --help      Show this help.
  --version   Show the package version.
`);
}

function printVersion() {
  const packageJson = require('../package.json');
  process.stdout.write(`${packageJson.version}\n`);
}

function failCli(message) {
  process.stderr.write(`[mcp-http-bridge] ${message}\n`);
  process.exitCode = 1;
}

function logError(message, error) {
  const suffix = error && error.message ? `: ${error.message}` : '';
  process.stderr.write(`[mcp-http-bridge] ${message}${suffix}\n`);
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes('--help') || argv.includes('-h')) {
    printUsage();
    return;
  }

  if (argv.includes('--version') || argv.includes('-v')) {
    printVersion();
    return;
  }

  let options;
  try {
    options = parseArgs(argv);
  } catch (error) {
    failCli(error.message);
    printUsage();
    return;
  }

  startBridge(options);
  process.on('SIGINT', () => process.exit(0));
  process.on('SIGTERM', () => process.exit(0));
}

main().catch((error) => {
  logError('Fatal error', error);
  process.exit(1);
});
