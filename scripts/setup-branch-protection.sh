#!/bin/bash
# ブランチ保護設定スクリプト

set -euo pipefail

REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-}"
REPO_NAME="${GITHUB_REPOSITORY_NAME:-mcp-docker}"
BRANCH="${BRANCH:-main}"

if [[ -z "$REPO_OWNER" ]]; then
    echo "Error: GITHUB_REPOSITORY_OWNER environment variable is required"
    echo "Usage: GITHUB_REPOSITORY_OWNER=your-username $0"
    exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "Error: GITHUB_TOKEN environment variable is required"
    echo "Please set your GitHub Personal Access Token"
    exit 1
fi

echo "Setting up branch protection for $REPO_OWNER/$REPO_NAME:$BRANCH"

# ブランチ保護設定
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": [
        "lint",
        "build (ubuntu-latest, 20.10)",
        "build (ubuntu-latest, 24.0)",
        "build (macos-latest, 20.10)",
        "build (macos-latest, 24.0)",
        "build (windows-latest, 24.0)",
        "security",
        "bats-test (ubuntu-latest)",
        "bats-test (macos-latest)",
        "integration-test (ubuntu-latest)",
        "integration-test (macos-latest)"
      ]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": false
    },
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false,
    "required_linear_history": true
  }'

echo ""
echo "✅ Branch protection configured successfully!"
echo ""
echo "Protection rules applied:"
echo "- Required status checks: All CI jobs must pass"
echo "- Enforce admins: Yes"
echo "- Required reviews: 1 approving review"
echo "- Dismiss stale reviews: Yes"
echo "- Force pushes: Disabled"
echo "- Deletions: Disabled"
echo "- Linear history: Required"
