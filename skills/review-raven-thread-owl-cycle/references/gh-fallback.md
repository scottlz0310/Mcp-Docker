# gh CLIのresolve補完（R-09）

R-00で固定したwrite経路の条件に従う。本文取得は`comment-reader.md`のreaderだけを使用し、GraphQLの本文readへ迂回しない。

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
