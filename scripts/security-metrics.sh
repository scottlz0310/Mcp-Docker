#!/bin/bash
set -euo pipefail

# セキュリティメトリクス収集スクリプト
# Usage: ./scripts/security-metrics.sh [--output-dir DIR]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/security-reports"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)

# オプション解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--output-dir DIR]"
            echo "  --output-dir DIR  Output directory for reports (default: ./security-reports)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 出力ディレクトリ作成
mkdir -p "$OUTPUT_DIR"

echo "🔍 セキュリティメトリクス収集開始"
echo "📁 出力ディレクトリ: $OUTPUT_DIR"

# 1. Docker イメージビルド
echo "🐳 Docker イメージビルド"
cd "$PROJECT_ROOT"
docker build -t mcp-docker:security-check .

# 2. Trivy スキャン
echo "🔍 Trivy 脆弱性スキャン"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image \
    --format json \
    --output "/tmp/trivy-${TIMESTAMP}.json" \
    mcp-docker:security-check

# Trivy結果をホストにコピー
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$OUTPUT_DIR:/output" \
    aquasec/trivy:latest image \
    --format json \
    --output "/output/trivy-${TIMESTAMP}.json" \
    mcp-docker:security-check

# 3. SBOM生成
echo "📋 SBOM生成"
docker run --rm -v "$PROJECT_ROOT:/workspace" \
    -v "$OUTPUT_DIR:/output" \
    anchore/syft:latest \
    /workspace -o spdx-json="/output/sbom-${TIMESTAMP}.spdx.json"

# 4. 依存関係脆弱性スキャン
echo "🔍 依存関係脆弱性スキャン"
docker run --rm -v "$OUTPUT_DIR:/output" \
    anchore/grype:latest \
    "sbom:/output/sbom-${TIMESTAMP}.spdx.json" \
    -o json="/output/grype-${TIMESTAMP}.json"

# 5. メトリクス集計
echo "📊 メトリクス集計"
cat > "$OUTPUT_DIR/security-summary-${TIMESTAMP}.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "scan_id": "${TIMESTAMP}",
    "repository": "$(git remote get-url origin 2>/dev/null || echo 'unknown')",
    "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
    "files": {
        "trivy_report": "trivy-${TIMESTAMP}.json",
        "sbom": "sbom-${TIMESTAMP}.spdx.json",
        "grype_report": "grype-${TIMESTAMP}.json"
    }
}
EOF

# 6. 脆弱性統計
if command -v jq >/dev/null 2>&1 && [ -f "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" ]; then
    echo "📈 脆弱性統計生成"

    CRITICAL=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" 2>/dev/null || echo "0")
    HIGH=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" 2>/dev/null || echo "0")
    MEDIUM=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" 2>/dev/null || echo "0")
    LOW=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW")] | length' "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" 2>/dev/null || echo "0")

    # 統計をサマリーに追加
    jq --argjson critical "$CRITICAL" \
       --argjson high "$HIGH" \
       --argjson medium "$MEDIUM" \
       --argjson low "$LOW" \
       '. + {
           vulnerability_stats: {
               critical: $critical,
               high: $high,
               medium: $medium,
               low: $low,
               total: ($critical + $high + $medium + $low)
           }
       }' "$OUTPUT_DIR/security-summary-${TIMESTAMP}.json" > "$OUTPUT_DIR/security-summary-${TIMESTAMP}.tmp"

    mv "$OUTPUT_DIR/security-summary-${TIMESTAMP}.tmp" "$OUTPUT_DIR/security-summary-${TIMESTAMP}.json"

    echo "📊 脆弱性統計:"
    echo "  Critical: $CRITICAL"
    echo "  High: $HIGH"
    echo "  Medium: $MEDIUM"
    echo "  Low: $LOW"
    echo "  Total: $((CRITICAL + HIGH + MEDIUM + LOW))"
fi

# 7. レポート生成
echo "📄 セキュリティレポート生成"
cat > "$OUTPUT_DIR/security-report-${TIMESTAMP}.md" << EOF
# Security Report

**Generated**: $(date -u +%Y-%m-%d\ %H:%M:%S\ UTC)
**Scan ID**: ${TIMESTAMP}
**Repository**: $(git remote get-url origin 2>/dev/null || echo 'unknown')
**Commit**: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')
**Branch**: $(git branch --show-current 2>/dev/null || echo 'unknown')

## Vulnerability Summary

$(if command -v jq >/dev/null 2>&1 && [ -f "$OUTPUT_DIR/trivy-${TIMESTAMP}.json" ]; then
    echo "| Severity | Count |"
    echo "|----------|-------|"
    echo "| Critical | $CRITICAL |"
    echo "| High     | $HIGH |"
    echo "| Medium   | $MEDIUM |"
    echo "| Low      | $LOW |"
    echo "| **Total** | **$((CRITICAL + HIGH + MEDIUM + LOW))** |"
else
    echo "Vulnerability statistics not available (jq not installed or Trivy report missing)"
fi)

## Files Generated

- \`trivy-${TIMESTAMP}.json\` - Trivy vulnerability scan results
- \`sbom-${TIMESTAMP}.spdx.json\` - Software Bill of Materials
- \`grype-${TIMESTAMP}.json\` - Grype vulnerability analysis
- \`security-summary-${TIMESTAMP}.json\` - Aggregated metrics

## Recommendations

$(if [ "${CRITICAL:-0}" -gt 0 ]; then
    echo "🚨 **CRITICAL**: $CRITICAL critical vulnerabilities found. Immediate action required."
fi)

$(if [ "${HIGH:-0}" -gt 5 ]; then
    echo "⚠️ **HIGH**: $HIGH high-severity vulnerabilities found. Review and remediate."
fi)

- Review vulnerability details in Trivy report
- Update dependencies with security patches
- Consider base image updates
- Monitor for new vulnerabilities regularly

EOF

echo "✅ セキュリティメトリクス収集完了"
echo "📁 レポート保存先: $OUTPUT_DIR"
echo "📄 メインレポート: security-report-${TIMESTAMP}.md"

# アラート判定
if [ "${CRITICAL:-0}" -gt 0 ] || [ "${HIGH:-0}" -gt 10 ]; then
    echo ""
    echo "🚨 セキュリティアラート!"
    echo "   Critical: ${CRITICAL:-0}, High: ${HIGH:-0}"
    echo "   即座に対応が必要です。"
    exit 1
fi

echo "✅ セキュリティ状況: 正常"
