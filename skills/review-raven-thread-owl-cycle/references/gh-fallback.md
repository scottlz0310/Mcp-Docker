# gh CLI の補完経路（GraphQL）

SKILL.md の「Phase U2」「Phase 4」から移した手順（内容は変更していない）。R-00 の discovery が成功している場合に限り、MCP の呼び出しを補うために使う read / write の補完経路で、discovery 失敗・未接続・schema 不一致・read 検証失敗から、この経路へ切り替えてはならない。

## inline review thread の取得（R-03 の補完。Phase U2）

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            isResolved
            comments(first: 10) {
              nodes {
                databaseId
                body
                path
                line
                author { login }
                createdAt
              }
            }
          }
        }
      }
    }
  }
' -f owner=<owner> -f repo=<repo> -F pr=<pr>
```
`pageInfo.hasNextPage` が `true` の場合、`-f cursor=<endCursor>` で繰り返します。

## thread の resolve（R-09 の補完。Phase 4）

```bash
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { id isResolved }
    }
  }
' -f threadId=<PRRT_node_id>
```
