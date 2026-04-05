package tools

import (
	"context"
	"fmt"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	ghclient "github.com/scottlz0310/copilot-review-mcp/internal/github"
)

// ─── Classification keywords ──────────────────────────────────────────────────

var blockingKeywords = []string{
	// エラー・クラッシュ系
	"panic", "nil pointer", "null reference", "index out of", "runtime error",
	"will fail", "causes error", "throws exception", "crash",
	// セキュリティ系
	"sql injection", "xss", "csrf", "authentication", "authorization",
	"unvalidated", "unsanitized", "hardcoded secret", "exposed credential",
	// データ整合性系
	"data loss", "data corruption", "race condition", "deadlock",
	"transaction", "rollback", "inconsistent state",
	// 型・互換性系
	"type mismatch", "breaking change", "incompatible", "removed api",
	"deprecated and removed",
}

var nonBlockingKeywords = []string{
	"consider adding test", "missing test", "log", "logging",
	"consider", "might want to", "optional",
}

var suggestionKeywords = []string{
	"rename", "refactor", "extract", "naming", "abstract", "simplify",
	"nit:", "style:", "minor:",
}

// classifyThread returns the classification and reason for a thread based on its comments.
// Priority: blocking > non-blocking > suggestion.
func classifyThread(comments []ghclient.ThreadComment) (classification, reason string) {
	var bodyBuilder strings.Builder
	for _, c := range comments {
		bodyBuilder.WriteByte(' ')
		bodyBuilder.WriteString(strings.ToLower(c.Body))
	}
	body := bodyBuilder.String()

	for _, kw := range blockingKeywords {
		if strings.Contains(body, kw) {
			return "blocking", fmt.Sprintf("keyword matched: %q", kw)
		}
	}
	for _, kw := range nonBlockingKeywords {
		if strings.Contains(body, kw) {
			return "non-blocking", fmt.Sprintf("keyword matched: %q", kw)
		}
	}
	for _, kw := range suggestionKeywords {
		if strings.Contains(body, kw) {
			return "suggestion", fmt.Sprintf("keyword matched: %q", kw)
		}
	}
	return "suggestion", "no keywords matched"
}

// ─── Tool 4: get_review_threads ───────────────────────────────────────────────

// GetReviewThreadsInput is the input schema for get_review_threads.
type GetReviewThreadsInput struct {
	Owner string `json:"owner"`
	Repo  string `json:"repo"`
	PR    int    `json:"pr"`
}

// ThreadCommentOutput is a single comment within a thread result.
type ThreadCommentOutput struct {
	Author    string `json:"author"`
	Body      string `json:"body"`
	CreatedAt string `json:"createdAt"`
}

// ThreadResult is the result for a single review thread.
type ThreadResult struct {
	ID                   string                `json:"id"`
	Path                 string                `json:"path"`
	Line                 *int32                `json:"line"`
	IsResolved           bool                  `json:"isResolved"`
	Classification       string                `json:"classification"`
	ClassificationReason string                `json:"classificationReason"`
	Comments             []ThreadCommentOutput `json:"comments"`
}

// ThreadSummary holds aggregate counts across all threads.
type ThreadSummary struct {
	Total       int `json:"total"`
	Blocking    int `json:"blocking"`
	NonBlocking int `json:"nonBlocking"`
	Suggestion  int `json:"suggestion"`
	Unresolved  int `json:"unresolved"`
}

// GetReviewThreadsOutput is the output schema for get_review_threads.
type GetReviewThreadsOutput struct {
	Threads []ThreadResult `json:"threads"`
	Summary ThreadSummary  `json:"summary"`
}

var getReviewThreadsTool = &mcp.Tool{
	Name:        "get_review_threads",
	Description: "PR のレビュースレッド一覧を分類情報付きで返す。各スレッドに PRRT_xxx 形式の ID を含む。ページネーション対応。",
}

func getReviewThreadsHandler(
	gh *ghclient.Client,
) func(context.Context, *mcp.CallToolRequest, GetReviewThreadsInput) (*mcp.CallToolResult, GetReviewThreadsOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in GetReviewThreadsInput) (*mcp.CallToolResult, GetReviewThreadsOutput, error) {
		if in.Owner == "" || in.Repo == "" || in.PR <= 0 {
			return nil, GetReviewThreadsOutput{}, fmt.Errorf("owner, repo, and pr are required")
		}

		rawThreads, err := gh.GetReviewThreads(ctx, in.Owner, in.Repo, in.PR)
		if err != nil {
			return nil, GetReviewThreadsOutput{}, err
		}

		summary := ThreadSummary{Total: len(rawThreads)}
		results := make([]ThreadResult, 0, len(rawThreads))
		for _, t := range rawThreads {
			classification, reason := classifyThread(t.Comments)

			switch classification {
			case "blocking":
				summary.Blocking++
			case "non-blocking":
				summary.NonBlocking++
			default:
				summary.Suggestion++
			}
			if !t.IsResolved {
				summary.Unresolved++
			}

			comments := make([]ThreadCommentOutput, 0, len(t.Comments))
			for _, c := range t.Comments {
				comments = append(comments, ThreadCommentOutput{
					Author:    c.Author,
					Body:      c.Body,
					CreatedAt: c.CreatedAt,
				})
			}
			results = append(results, ThreadResult{
				ID:                   t.ID,
				Path:                 t.Path,
				Line:                 t.Line,
				IsResolved:           t.IsResolved,
				Classification:       classification,
				ClassificationReason: reason,
				Comments:             comments,
			})
		}

		return nil, GetReviewThreadsOutput{Threads: results, Summary: summary}, nil
	}
}

// RegisterGetReviewThreadsTool adds get_review_threads to the MCP server.
func RegisterGetReviewThreadsTool(server *mcp.Server, gh *ghclient.Client) {
	mcp.AddTool(server, getReviewThreadsTool, getReviewThreadsHandler(gh))
}

// ─── Tool 5: reply_to_review_thread ──────────────────────────────────────────

// ReplyToThreadInput is the input schema for reply_to_review_thread.
type ReplyToThreadInput struct {
	ThreadID string `json:"threadId"`
	Body     string `json:"body"`
}

// ReplyToThreadOutput is the output schema for reply_to_review_thread.
type ReplyToThreadOutput struct {
	CommentID string  `json:"commentId"`
	CreatedAt string  `json:"createdAt"`
	Warn      *string `json:"warn,omitempty"`
}

var replyToThreadTool = &mcp.Tool{
	Name:        "reply_to_review_thread",
	Description: "指定したレビュースレッド（PRRT_xxx）に返信コメントを投稿する。スレッドが解決済みの場合は warn フィールドに thread_already_resolved を含む。",
}

func replyToThreadHandler(
	gh *ghclient.Client,
) func(context.Context, *mcp.CallToolRequest, ReplyToThreadInput) (*mcp.CallToolResult, ReplyToThreadOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in ReplyToThreadInput) (*mcp.CallToolResult, ReplyToThreadOutput, error) {
		if in.ThreadID == "" {
			return nil, ReplyToThreadOutput{}, fmt.Errorf("threadId is required")
		}
		if strings.TrimSpace(in.Body) == "" {
			return nil, ReplyToThreadOutput{}, fmt.Errorf("body must not be empty or whitespace-only")
		}

		alreadyResolved, err := gh.IsThreadResolved(ctx, in.ThreadID)
		if err != nil {
			return nil, ReplyToThreadOutput{}, err
		}

		result, err := gh.ReplyToThread(ctx, in.ThreadID, in.Body)
		if err != nil {
			return nil, ReplyToThreadOutput{}, err
		}

		out := ReplyToThreadOutput{
			CommentID: result.CommentID,
			CreatedAt: result.CreatedAt,
		}
		if alreadyResolved {
			w := "thread_already_resolved"
			out.Warn = &w
		}
		return nil, out, nil
	}
}

// RegisterReplyToThreadTool adds reply_to_review_thread to the MCP server.
func RegisterReplyToThreadTool(server *mcp.Server, gh *ghclient.Client) {
	mcp.AddTool(server, replyToThreadTool, replyToThreadHandler(gh))
}

// ─── Tool 6: resolve_review_thread ───────────────────────────────────────────

// ResolveThreadInput is the input schema for resolve_review_thread.
type ResolveThreadInput struct {
	ThreadID string `json:"threadId"`
}

// ResolveThreadOutput is the output schema for resolve_review_thread.
type ResolveThreadOutput struct {
	Resolved        bool `json:"resolved"`
	AlreadyResolved bool `json:"already_resolved,omitempty"`
}

var resolveThreadTool = &mcp.Tool{
	Name:        "resolve_review_thread",
	Description: "指定したレビュースレッド（PRRT_xxx）を解決済みにする。すでに解決済みの場合は no-op で already_resolved: true を返す。",
}

func resolveThreadHandler(
	gh *ghclient.Client,
) func(context.Context, *mcp.CallToolRequest, ResolveThreadInput) (*mcp.CallToolResult, ResolveThreadOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in ResolveThreadInput) (*mcp.CallToolResult, ResolveThreadOutput, error) {
		if in.ThreadID == "" {
			return nil, ResolveThreadOutput{}, fmt.Errorf("threadId is required")
		}

		alreadyResolved, err := gh.ResolveThread(ctx, in.ThreadID)
		if err != nil {
			return nil, ResolveThreadOutput{}, err
		}
		return nil, ResolveThreadOutput{
			Resolved:        true,
			AlreadyResolved: alreadyResolved,
		}, nil
	}
}

// RegisterResolveThreadTool adds resolve_review_thread to the MCP server.
func RegisterResolveThreadTool(server *mcp.Server, gh *ghclient.Client) {
	mcp.AddTool(server, resolveThreadTool, resolveThreadHandler(gh))
}

// ─── Tool 7: reply_and_resolve_review_thread ──────────────────────────────────

// ReplyAndResolveInput is the input schema for reply_and_resolve_review_thread.
type ReplyAndResolveInput struct {
	ThreadID string `json:"threadId"`
	Body     string `json:"body"`
	Resolve  bool   `json:"resolve"`
}

// ReplyAndResolveOutput is the output schema for reply_and_resolve_review_thread.
type ReplyAndResolveOutput struct {
	Replied      bool    `json:"replied"`
	Resolved     bool    `json:"resolved"`
	CommentID    *string `json:"commentId"`
	ReplyError   *string `json:"replyError"`
	ResolveError *string `json:"resolveError"`
}

var replyAndResolveTool = &mcp.Tool{
	Name:        "reply_and_resolve_review_thread",
	Description: "レビュースレッドへの返信と Resolve をベストエフォートで順次実行する。返信失敗時は Resolve を実行しない。各操作の成否は replied / resolved フィールドで個別に返す。",
}

func replyAndResolveHandler(
	gh *ghclient.Client,
) func(context.Context, *mcp.CallToolRequest, ReplyAndResolveInput) (*mcp.CallToolResult, ReplyAndResolveOutput, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, in ReplyAndResolveInput) (*mcp.CallToolResult, ReplyAndResolveOutput, error) {
		if in.ThreadID == "" {
			return nil, ReplyAndResolveOutput{}, fmt.Errorf("threadId is required")
		}
		if strings.TrimSpace(in.Body) == "" {
			return nil, ReplyAndResolveOutput{}, fmt.Errorf("body must not be empty or whitespace-only")
		}

		out := ReplyAndResolveOutput{}

		// Step 1: Reply.
		replyResult, err := gh.ReplyToThread(ctx, in.ThreadID, in.Body)
		if err != nil {
			errStr := err.Error()
			out.ReplyError = &errStr
			// replied == false → skip Resolve.
			return nil, out, nil
		}
		out.Replied = true
		out.CommentID = &replyResult.CommentID

		// Step 2: Resolve (only if requested and reply succeeded).
		if !in.Resolve {
			return nil, out, nil
		}
		_, err = gh.ResolveThread(ctx, in.ThreadID)
		if err != nil {
			errStr := err.Error()
			out.ResolveError = &errStr
			return nil, out, nil
		}
		out.Resolved = true
		return nil, out, nil
	}
}

// RegisterReplyAndResolveTool adds reply_and_resolve_review_thread to the MCP server.
func RegisterReplyAndResolveTool(server *mcp.Server, gh *ghclient.Client) {
	mcp.AddTool(server, replyAndResolveTool, replyAndResolveHandler(gh))
}

// RegisterThreadTools registers Tools 4–7 (ISSUE#26) on the MCP server.
func RegisterThreadTools(server *mcp.Server, gh *ghclient.Client) {
	RegisterGetReviewThreadsTool(server, gh)
	RegisterReplyToThreadTool(server, gh)
	RegisterResolveThreadTool(server, gh)
	RegisterReplyAndResolveTool(server, gh)
}
