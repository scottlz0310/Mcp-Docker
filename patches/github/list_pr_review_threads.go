// Package github provides MCP tools for interacting with GitHub.
// This file adds the list_pull_request_review_threads tool, which exposes
// GraphQL-only thread node IDs (PRRT_xxx) needed by
// resolve_pull_request_review_thread.
package github

import (
	"context"
	"fmt"
	"time"

	ghErrors "github.com/github/github-mcp-server/pkg/errors"
	"github.com/github/github-mcp-server/pkg/inventory"
	"github.com/github/github-mcp-server/pkg/scopes"
	"github.com/github/github-mcp-server/pkg/translations"
	"github.com/github/github-mcp-server/pkg/utils"
	"github.com/google/jsonschema-go/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/shurcooL/githubv4"
)

// prListReviewThreadsQuery is the GraphQL query for listing PR review threads.
// Distinct type names are used to avoid conflicts with reviewThreadsQuery /
// reviewThreadNode defined in pullrequests.go.
type prListReviewThreadsQuery struct {
	Repository struct {
		PullRequest struct {
			ReviewThreads struct {
				Nodes    []prListReviewThreadNode
				PageInfo struct {
					HasNextPage githubv4.Boolean
					EndCursor   githubv4.String
				}
				TotalCount githubv4.Int
			} `graphql:"reviewThreads(first: 100)"`
		} `graphql:"pullRequest(number: $prNum)"`
	} `graphql:"repository(owner: $owner, name: $repo)"`
}

type prListReviewThreadNode struct {
	ID         githubv4.ID
	IsResolved githubv4.Boolean
	IsOutdated githubv4.Boolean
	Path       githubv4.String
	Line       *githubv4.Int
	StartLine  *githubv4.Int
	Comments   struct {
		Nodes []struct {
			Body   githubv4.String
			Author struct {
				Login githubv4.String
			}
			CreatedAt githubv4.DateTime
		}
	} `graphql:"comments(first: 1)"`
}

type prReviewThreadListResult struct {
	ID           string                      `json:"id"`
	IsResolved   bool                        `json:"isResolved"`
	IsOutdated   bool                        `json:"isOutdated"`
	Path         string                      `json:"path"`
	Line         *int32                      `json:"line,omitempty"`
	StartLine    *int32                      `json:"startLine,omitempty"`
	FirstComment *prReviewThreadFirstComment `json:"firstComment,omitempty"`
}

type prReviewThreadFirstComment struct {
	Body      string `json:"body"`
	Author    string `json:"author"`
	CreatedAt string `json:"createdAt"`
}

// ListPullRequestReviewThreads creates a tool to list review threads on a pull
// request. The returned thread node IDs (PRRT_xxx) can be passed directly to
// resolve_pull_request_review_thread.
func ListPullRequestReviewThreads(t translations.TranslationHelperFunc) inventory.ServerTool {
	return NewTool(
		ToolsetMetadataPullRequests,
		mcp.Tool{
			Name: "list_pull_request_review_threads",
			Description: t("TOOL_LIST_PR_REVIEW_THREADS_DESCRIPTION",
				"List review threads on a pull request. "+
					"Use this tool when you need the thread node ID (PRRT_xxx format) to resolve a review thread with resolve_pull_request_review_thread. "+
					"Returns each thread's node ID, resolution status (isResolved, isOutdated), file path, line numbers, and the first comment's body, author, and timestamp. "+
					"Use is_resolved=false to list only unresolved threads (e.g. to find what still needs attention), "+
					"is_resolved=true for resolved threads, or omit is_resolved to return all threads. "+
					"Unlike pull_request_read with method=get_review_comments, this tool returns the PRRT_ node ID required for resolving threads."),
			Annotations: &mcp.ToolAnnotations{
				Title:        t("TOOL_LIST_PR_REVIEW_THREADS_USER_TITLE", "List pull request review threads"),
				ReadOnlyHint: true,
			},
			InputSchema: &jsonschema.Schema{
				Type: "object",
				Properties: map[string]*jsonschema.Schema{
					"owner": {
						Type:        "string",
						Description: "Repository owner",
					},
					"repo": {
						Type:        "string",
						Description: "Repository name",
					},
					"pull_number": {
						Type:        "number",
						Description: "Pull request number",
					},
					"is_resolved": {
						Type: "boolean",
						Description: "Filter by resolution status: " +
							"true returns only resolved threads, " +
							"false returns only unresolved threads, " +
							"omit (default) returns all threads",
					},
				},
				Required: []string{"owner", "repo", "pull_number"},
			},
		},
		[]scopes.Scope{scopes.Repo},
		func(ctx context.Context, deps ToolDependencies, _ *mcp.CallToolRequest, args map[string]any) (*mcp.CallToolResult, any, error) {
			owner, err := RequiredParam[string](args, "owner")
			if err != nil {
				return utils.NewToolResultError(err.Error()), nil, nil
			}
			repo, err := RequiredParam[string](args, "repo")
			if err != nil {
				return utils.NewToolResultError(err.Error()), nil, nil
			}
			pullNumber, err := RequiredInt(args, "pull_number")
			if err != nil {
				return utils.NewToolResultError(err.Error()), nil, nil
			}

			// isResolvedProvided distinguishes "not given" (all threads) from
			// explicit true/false (filter by resolution status).
			isResolved, isResolvedProvided, err := OptionalParamOK[bool](args, "is_resolved")
			if err != nil {
				return utils.NewToolResultError(err.Error()), nil, nil
			}

			gqlClient, err := deps.GetGQLClient(ctx)
			if err != nil {
				return utils.NewToolResultErrorFromErr("failed to get GitHub GQL client", err), nil, nil
			}

			var query prListReviewThreadsQuery
			vars := map[string]any{
				"owner": githubv4.String(owner),
				"repo":  githubv4.String(repo),
				"prNum": githubv4.Int(int32(pullNumber)), //nolint:gosec // pullNumber is controlled by user input validation
			}

			if err := gqlClient.Query(ctx, &query, vars); err != nil {
				return ghErrors.NewGitHubGraphQLErrorResponse(ctx,
					"failed to list pull request review threads",
					err,
				), nil, nil
			}

			results := make([]prReviewThreadListResult, 0)
			for _, node := range query.Repository.PullRequest.ReviewThreads.Nodes {
				// Apply is_resolved filter when explicitly provided.
				if isResolvedProvided && bool(node.IsResolved) != isResolved {
					continue
				}

				result := prReviewThreadListResult{
					ID:         fmt.Sprintf("%v", node.ID),
					IsResolved: bool(node.IsResolved),
					IsOutdated: bool(node.IsOutdated),
					Path:       string(node.Path),
				}

				if node.Line != nil {
					v := int32(*node.Line) //nolint:gosec // line numbers are always small positive integers
					result.Line = &v
				}
				if node.StartLine != nil {
					v := int32(*node.StartLine) //nolint:gosec // line numbers are always small positive integers
					result.StartLine = &v
				}

				if len(node.Comments.Nodes) > 0 {
					c := node.Comments.Nodes[0]
					result.FirstComment = &prReviewThreadFirstComment{
						Body:      string(c.Body),
						Author:    string(c.Author.Login),
						CreatedAt: c.CreatedAt.Time.Format(time.RFC3339),
					}
				}

				results = append(results, result)
			}

			type prReviewThreadsResponse struct {
				Threads    []prReviewThreadListResult `json:"threads"`
				TotalCount int                        `json:"totalCount"`
				// Truncated is true when the PR has more than 100 review threads
				// and results are incomplete.
				Truncated bool `json:"truncated,omitempty"`
			}

			return MarshalledTextResult(prReviewThreadsResponse{
				Threads:    results,
				TotalCount: int(query.Repository.PullRequest.ReviewThreads.TotalCount),
				Truncated:  bool(query.Repository.PullRequest.ReviewThreads.PageInfo.HasNextPage),
			}), nil, nil
		})
}
