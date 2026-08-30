package conformance

import (
	"bufio"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime"
	"net/http"
	"net/url"
	"reflect"
	"strings"
	"sync/atomic"
)

const (
	ProtocolVersion       = "2026-07-28"
	LegacyProtocolVersion = "2025-06-18"
	maxResponseBytes      = 8 << 20
	maxSSETokenBytes      = 2 << 20
)

type Options struct {
	URL                     string
	DirectURL               string
	Token                   string
	DirectToken             string
	AuthenticatedUser       string
	DirectAuthenticatedUser string
	ResourceURI             string
	RequireAuth             bool
	WaitForUpdate           bool
	RequireKeepAlive        bool
	RequireNoBuffering      bool
	TriggerTool             string
	TriggerArguments        map[string]any
	Output                  io.Writer
	HTTPClient              *http.Client
	DirectHTTPClient        *http.Client
}

type client struct {
	endpoint   *url.URL
	token      string
	user       string
	httpClient *http.Client
	nextID     atomic.Int64
}

type rpcEnvelope struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

type rpcError struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

func Verify(ctx context.Context, opts Options) error {
	if opts.Output == nil {
		opts.Output = io.Discard
	}
	if opts.HTTPClient == nil {
		opts.HTTPClient = http.DefaultClient
	}
	if opts.DirectHTTPClient == nil {
		opts.DirectHTTPClient = opts.HTTPClient
	}
	if opts.URL == "" {
		return errors.New("--url は必須です")
	}
	if opts.TriggerTool != "" && opts.ResourceURI == "" {
		return errors.New("trigger tool を使う場合は --resource-uri が必須です")
	}
	if (opts.WaitForUpdate || opts.RequireKeepAlive) && opts.ResourceURI == "" {
		return errors.New("subscription 検証には --resource-uri が必須です")
	}

	gateway, err := newClient(opts.URL, opts.Token, opts.AuthenticatedUser, opts.HTTPClient)
	if err != nil {
		return err
	}
	if opts.RequireAuth {
		if err := gateway.verifyAuthChallenge(ctx); err != nil {
			return fmt.Errorf("認証境界: %w", err)
		}
		pass(opts.Output, "未認証リクエストは Bearer challenge 付き 401 で拒否")
		if opts.Token == "" {
			return errors.New("認証済み検証用トークンがありません。--token-env で指定した環境変数を設定してください")
		}
	}

	discovery, err := gateway.verifyDiscovery(ctx)
	if err != nil {
		return fmt.Errorf("server/discover: %w", err)
	}
	pass(opts.Output, "server/discover が 2026-07-28 を広告し session を発行しない")

	if opts.DirectURL != "" {
		direct, err := newClient(opts.DirectURL, opts.DirectToken, opts.DirectAuthenticatedUser, opts.DirectHTTPClient)
		if err != nil {
			return fmt.Errorf("direct endpoint: %w", err)
		}
		directDiscovery, err := direct.verifyDiscovery(ctx)
		if err != nil {
			return fmt.Errorf("direct server/discover: %w", err)
		}
		if !reflect.DeepEqual(discovery, directDiscovery) {
			return errors.New("gateway 経由と direct endpoint の server/discover result が一致しません")
		}
		pass(opts.Output, "gateway 経由と direct endpoint の discovery result が一致")
	}

	if err := gateway.verifyMethodRejection(ctx); err != nil {
		return fmt.Errorf("stateless method: %w", err)
	}
	pass(opts.Output, "GET / DELETE は 405 で session 経路を提供しない")

	if err := gateway.verifyLegacyRejection(ctx); err != nil {
		return fmt.Errorf("legacy initialize: %w", err)
	}
	pass(opts.Output, "legacy initialize は 400 / -32022 で拒否される")

	for range 2 {
		if err := gateway.verifyToolsList(ctx); err != nil {
			return fmt.Errorf("tools/list: %w", err)
		}
	}
	pass(opts.Output, "連続する tools/list が Mcp-Session-Id なしで成功")

	if opts.ResourceURI == "" {
		return nil
	}
	if err := gateway.verifyResource(ctx, opts.ResourceURI); err != nil {
		return fmt.Errorf("resource operation: %w", err)
	}
	pass(opts.Output, "resources/list と resources/read が成功")

	trigger := func(context.Context) error { return nil }
	if opts.TriggerTool != "" {
		trigger = func(triggerCtx context.Context) error {
			return gateway.callTool(triggerCtx, opts.TriggerTool, opts.TriggerArguments)
		}
	}
	updated, err := gateway.verifySubscription(
		ctx,
		opts.ResourceURI,
		opts.WaitForUpdate || opts.TriggerTool != "",
		opts.RequireKeepAlive,
		opts.RequireNoBuffering,
		trigger,
	)
	if err != nil {
		return fmt.Errorf("subscriptions/listen: %w", err)
	}
	pass(opts.Output, "subscriptions/listen の最初のJSON-RPC messageが acknowledged")
	if opts.RequireKeepAlive {
		pass(opts.Output, "idle中のSSE keep-alive commentが到達")
	}
	if updated {
		if err := gateway.verifyResourceRead(ctx, opts.ResourceURI); err != nil {
			return fmt.Errorf("notification後のresources/read: %w", err)
		}
		pass(opts.Output, "resources/updated の subscriptionId を検証し resource を再read")
	} else {
		pass(opts.Output, "client側closeでsubscription streamを終了")
	}
	return nil
}

func newClient(rawURL, token, user string, httpClient *http.Client) (*client, error) {
	endpoint, err := url.Parse(rawURL)
	if err != nil {
		return nil, fmt.Errorf("URLを解析できません: %w", err)
	}
	if endpoint.Scheme != "http" && endpoint.Scheme != "https" {
		return nil, fmt.Errorf("未対応のURL schemeです: %q", endpoint.Scheme)
	}
	if endpoint.Host == "" {
		return nil, errors.New("URLにhostがありません")
	}
	return &client{endpoint: endpoint, token: token, user: user, httpClient: httpClient}, nil
}

func (c *client) verifyAuthChallenge(ctx context.Context) (err error) {
	unauthenticated := &client{endpoint: c.endpoint, httpClient: c.httpClient}
	resp, err := unauthenticated.modernRequest(ctx, "server/discover", map[string]any{}, "")
	if err != nil {
		return err
	}
	defer closeResponseBody(resp.Body, &err)
	if resp.StatusCode != http.StatusUnauthorized {
		return fmt.Errorf("status = %d, want 401", resp.StatusCode)
	}
	challenge := resp.Header.Get("WWW-Authenticate")
	if !strings.Contains(strings.ToLower(challenge), "bearer") || !strings.Contains(challenge, "resource_metadata=") {
		return fmt.Errorf("WWW-Authenticate = %q, want Bearer resource_metadata challenge", challenge)
	}
	return nil
}

func (c *client) verifyDiscovery(ctx context.Context) (any, error) {
	resp, envelope, err := c.callModern(ctx, "server/discover", map[string]any{}, "")
	if err != nil {
		return nil, err
	}
	if err := requireNoSession(resp); err != nil {
		return nil, err
	}
	var result struct {
		ResultType        string   `json:"resultType"`
		SupportedVersions []string `json:"supportedVersions"`
	}
	if err := json.Unmarshal(envelope.Result, &result); err != nil {
		return nil, fmt.Errorf("resultを解析できません: %w", err)
	}
	if result.ResultType != "complete" {
		return nil, fmt.Errorf("resultType = %q, want complete", result.ResultType)
	}
	if !contains(result.SupportedVersions, ProtocolVersion) {
		return nil, fmt.Errorf("supportedVersions = %v, want %s", result.SupportedVersions, ProtocolVersion)
	}
	var canonical any
	if err := json.Unmarshal(envelope.Result, &canonical); err != nil {
		return nil, err
	}
	return canonical, nil
}

func (c *client) verifyMethodRejection(ctx context.Context) error {
	for _, method := range []string{http.MethodGet, http.MethodDelete} {
		req, err := http.NewRequestWithContext(ctx, method, c.endpoint.String(), nil)
		if err != nil {
			return err
		}
		c.setAuthorization(req)
		req.Header.Set("Accept", "application/json, text/event-stream")
		resp, err := c.httpClient.Do(req)
		if err != nil {
			return err
		}
		if err := drainAndCloseResponse(resp.Body); err != nil {
			return fmt.Errorf("%s response: %w", method, err)
		}
		if resp.StatusCode != http.StatusMethodNotAllowed {
			return fmt.Errorf("%s status = %d, want 405", method, resp.StatusCode)
		}
		if err := requireNoSession(resp); err != nil {
			return fmt.Errorf("%s: %w", method, err)
		}
	}
	return nil
}

func (c *client) verifyLegacyRejection(ctx context.Context) (err error) {
	body := map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "initialize",
		"params": map[string]any{
			"protocolVersion": LegacyProtocolVersion,
			"capabilities":    map[string]any{},
			"clientInfo": map[string]any{
				"name":    "mcp-docker-conformance",
				"version": "1.0.0",
			},
		},
	}
	encoded, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint.String(), bytes.NewReader(encoded))
	if err != nil {
		return err
	}
	c.setAuthorization(req)
	req.Header.Set("Accept", "application/json, text/event-stream")
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer closeResponseBody(resp.Body, &err)
	if resp.StatusCode != http.StatusBadRequest {
		return fmt.Errorf("status = %d, want 400", resp.StatusCode)
	}
	if got := resp.Header.Get("WWW-Authenticate"); got != "" {
		return fmt.Errorf("protocol errorにWWW-Authenticateが付与されました: %q", got)
	}
	if err := requireNoSession(resp); err != nil {
		return err
	}
	envelope, _, err := readRPCEnvelope(resp, json.RawMessage("1"))
	if err != nil {
		return err
	}
	if envelope.Error == nil || envelope.Error.Code != -32022 {
		return fmt.Errorf("error = %+v, want code -32022", envelope.Error)
	}
	var data struct {
		Supported []string `json:"supported"`
		Requested string   `json:"requested"`
	}
	if err := json.Unmarshal(envelope.Error.Data, &data); err != nil {
		return fmt.Errorf("error.dataを解析できません: %w", err)
	}
	if data.Requested != LegacyProtocolVersion || !contains(data.Supported, ProtocolVersion) {
		return fmt.Errorf("error.data = %+v, want requested=%s supported=%s", data, LegacyProtocolVersion, ProtocolVersion)
	}
	return nil
}

func (c *client) verifyToolsList(ctx context.Context) error {
	resp, envelope, err := c.callModern(ctx, "tools/list", map[string]any{}, "")
	if err != nil {
		return err
	}
	if err := requireNoSession(resp); err != nil {
		return err
	}
	var result struct {
		ResultType string            `json:"resultType"`
		Tools      []json.RawMessage `json:"tools"`
	}
	if err := json.Unmarshal(envelope.Result, &result); err != nil {
		return err
	}
	if result.ResultType != "complete" {
		return fmt.Errorf("resultType = %q, want complete", result.ResultType)
	}
	return nil
}

func (c *client) verifyResource(ctx context.Context, uri string) error {
	_, envelope, err := c.callModern(ctx, "resources/list", map[string]any{}, "")
	if err != nil {
		return err
	}
	var result struct {
		Resources []struct {
			URI string `json:"uri"`
		} `json:"resources"`
	}
	if err := json.Unmarshal(envelope.Result, &result); err != nil {
		return err
	}
	found := false
	for _, resource := range result.Resources {
		if resource.URI == uri {
			found = true
			break
		}
	}
	if !found {
		return fmt.Errorf("resources/listに %q がありません", uri)
	}
	return c.verifyResourceRead(ctx, uri)
}

func (c *client) verifyResourceRead(ctx context.Context, uri string) error {
	resp, envelope, err := c.callModern(ctx, "resources/read", map[string]any{"uri": uri}, uri)
	if err != nil {
		return err
	}
	if err := requireNoSession(resp); err != nil {
		return err
	}
	var result struct {
		ResultType string            `json:"resultType"`
		Contents   []json.RawMessage `json:"contents"`
	}
	if err := json.Unmarshal(envelope.Result, &result); err != nil {
		return err
	}
	if result.ResultType != "complete" || len(result.Contents) == 0 {
		return fmt.Errorf("resources/read resultType=%q contents=%d", result.ResultType, len(result.Contents))
	}
	return nil
}

func (c *client) callTool(ctx context.Context, name string, arguments map[string]any) error {
	if arguments == nil {
		arguments = map[string]any{}
	}
	_, envelope, err := c.callModern(ctx, "tools/call", map[string]any{
		"name":      name,
		"arguments": arguments,
	}, name)
	if err != nil {
		return err
	}
	var result struct {
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(envelope.Result, &result); err != nil {
		return err
	}
	if result.IsError {
		return fmt.Errorf("tool %q returned isError=true", name)
	}
	return nil
}

func (c *client) verifySubscription(
	ctx context.Context,
	uri string,
	waitForUpdate bool,
	requireKeepAlive bool,
	requireNoBuffering bool,
	trigger func(context.Context) error,
) (updated bool, err error) {
	params := map[string]any{
		"notifications": map[string]any{
			"resourceSubscriptions": []string{uri},
		},
	}
	resp, requestID, err := c.modernRequestWithID(ctx, "subscriptions/listen", params, "")
	if err != nil {
		return false, err
	}
	defer closeResponseBody(resp.Body, &err)
	if resp.StatusCode != http.StatusOK {
		body, readErr := readBounded(resp.Body)
		if readErr != nil {
			return false, fmt.Errorf("status = %d, want 200; response bodyを読み取れません: %w", resp.StatusCode, readErr)
		}
		return false, fmt.Errorf("status = %d, want 200; body=%s", resp.StatusCode, body)
	}
	mediaType, _, err := mime.ParseMediaType(resp.Header.Get("Content-Type"))
	if err != nil || mediaType != "text/event-stream" {
		return false, fmt.Errorf("Content-Type = %q, want text/event-stream", resp.Header.Get("Content-Type"))
	}
	if requireNoBuffering {
		if got := strings.ToLower(resp.Header.Get("X-Accel-Buffering")); got != "no" {
			return false, fmt.Errorf("X-Accel-Buffering = %q, want no", got)
		}
	}
	if err := requireNoSession(resp); err != nil {
		return false, err
	}

	stream := newSSEReader(resp.Body)
	first, _, err := stream.nextJSON()
	if err != nil {
		return false, fmt.Errorf("acknowledgementを受信できません: %w", err)
	}
	if first.Method != "notifications/subscriptions/acknowledged" {
		return false, fmt.Errorf("first method = %q, want notifications/subscriptions/acknowledged", first.Method)
	}
	if err := validateSubscriptionID(first.Params, requestID); err != nil {
		return false, fmt.Errorf("acknowledgement: %w", err)
	}
	if err := validateHonoredResource(first.Params, uri); err != nil {
		return false, err
	}

	var pending *rpcEnvelope
	if requireKeepAlive {
		for {
			event, err := stream.next()
			if err != nil {
				return false, fmt.Errorf("keep-alive待機中: %w", err)
			}
			if event.comment {
				break
			}
			if len(event.data) == 0 {
				continue
			}
			var message rpcEnvelope
			if err := json.Unmarshal(event.data, &message); err != nil {
				return false, fmt.Errorf("SSE messageを解析できません: %w", err)
			}
			pending = &message
		}
	}

	if err := trigger(ctx); err != nil {
		return false, fmt.Errorf("trigger tool: %w", err)
	}
	if !waitForUpdate {
		return false, nil
	}

	for {
		var message rpcEnvelope
		if pending != nil {
			message = *pending
			pending = nil
		} else {
			var err error
			message, _, err = stream.nextJSON()
			if err != nil {
				return false, fmt.Errorf("resource update待機中: %w", err)
			}
		}
		if message.Method == "notifications/resources/updated" {
			if err := validateSubscriptionID(message.Params, requestID); err != nil {
				return false, fmt.Errorf("resources/updated: %w", err)
			}
			var params struct {
				URI string `json:"uri"`
			}
			if err := json.Unmarshal(message.Params, &params); err != nil {
				return false, err
			}
			if params.URI != uri {
				return false, fmt.Errorf("notification uri = %q, want %q", params.URI, uri)
			}
			return true, nil
		}
	}
}

func (c *client) callModern(ctx context.Context, method string, params map[string]any, name string) (response *http.Response, envelope rpcEnvelope, err error) {
	resp, requestID, err := c.modernRequestWithID(ctx, method, params, name)
	if err != nil {
		return nil, rpcEnvelope{}, err
	}
	defer closeResponseBody(resp.Body, &err)
	if resp.StatusCode != http.StatusOK {
		body, readErr := readBounded(resp.Body)
		if readErr != nil {
			return resp, rpcEnvelope{}, fmt.Errorf("status = %d, want 200; response bodyを読み取れません: %w", resp.StatusCode, readErr)
		}
		return resp, rpcEnvelope{}, fmt.Errorf("status = %d, want 200; body=%s", resp.StatusCode, body)
	}
	envelope, _, err = readRPCEnvelope(resp, requestID)
	if err != nil {
		return resp, rpcEnvelope{}, err
	}
	if envelope.Error != nil {
		return resp, rpcEnvelope{}, fmt.Errorf("JSON-RPC error %d: %s", envelope.Error.Code, envelope.Error.Message)
	}
	if len(envelope.Result) == 0 {
		return resp, rpcEnvelope{}, errors.New("JSON-RPC resultがありません")
	}
	return resp, envelope, nil
}

func closeResponseBody(body io.Closer, errp *error) {
	if closeErr := body.Close(); closeErr != nil {
		*errp = errors.Join(*errp, fmt.Errorf("response bodyをcloseできません: %w", closeErr))
	}
}

func drainAndCloseResponse(body io.ReadCloser) error {
	_, readErr := io.Copy(io.Discard, io.LimitReader(body, maxResponseBytes))
	closeErr := body.Close()
	if readErr != nil {
		readErr = fmt.Errorf("response bodyを読み取れません: %w", readErr)
	}
	if closeErr != nil {
		closeErr = fmt.Errorf("response bodyをcloseできません: %w", closeErr)
	}
	return errors.Join(readErr, closeErr)
}

func (c *client) modernRequest(ctx context.Context, method string, params map[string]any, name string) (*http.Response, error) {
	resp, _, err := c.modernRequestWithID(ctx, method, params, name)
	return resp, err
}

func (c *client) modernRequestWithID(ctx context.Context, method string, params map[string]any, name string) (*http.Response, json.RawMessage, error) {
	requestID := c.nextID.Add(1)
	if params == nil {
		params = map[string]any{}
	}
	params["_meta"] = map[string]any{
		"io.modelcontextprotocol/protocolVersion": ProtocolVersion,
		"io.modelcontextprotocol/clientInfo": map[string]any{
			"name":    "mcp-docker-conformance",
			"version": "1.0.0",
		},
		"io.modelcontextprotocol/clientCapabilities": map[string]any{},
	}
	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0",
		"id":      requestID,
		"method":  method,
		"params":  params,
	})
	if err != nil {
		return nil, nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint.String(), bytes.NewReader(body))
	if err != nil {
		return nil, nil, err
	}
	c.setAuthorization(req)
	req.Header.Set("Accept", "application/json, text/event-stream")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("MCP-Protocol-Version", ProtocolVersion)
	req.Header.Set("Mcp-Method", method)
	if name != "" {
		req.Header.Set("Mcp-Name", encodeHeaderValue(name))
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, nil, err
	}
	return resp, json.RawMessage(fmt.Sprintf("%d", requestID)), nil
}

func (c *client) setAuthorization(req *http.Request) {
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	if c.user != "" {
		req.Header.Set("X-Authenticated-User", c.user)
	}
}

func readRPCEnvelope(resp *http.Response, expectedID json.RawMessage) (rpcEnvelope, []byte, error) {
	mediaType, _, err := mime.ParseMediaType(resp.Header.Get("Content-Type"))
	if err != nil {
		return rpcEnvelope{}, nil, fmt.Errorf("Content-Typeを解析できません: %w", err)
	}
	if mediaType == "application/json" {
		body, err := readBounded(resp.Body)
		if err != nil {
			return rpcEnvelope{}, nil, err
		}
		var envelope rpcEnvelope
		if err := json.Unmarshal(body, &envelope); err != nil {
			return rpcEnvelope{}, body, fmt.Errorf("JSON-RPC responseを解析できません: %w", err)
		}
		if !sameID(envelope.ID, expectedID) {
			return rpcEnvelope{}, body, fmt.Errorf("response id = %s, want %s", envelope.ID, expectedID)
		}
		return envelope, body, nil
	}
	if mediaType != "text/event-stream" {
		return rpcEnvelope{}, nil, fmt.Errorf("Content-Type = %q, want application/json or text/event-stream", mediaType)
	}
	stream := newSSEReader(resp.Body)
	for {
		envelope, raw, err := stream.nextJSON()
		if err != nil {
			return rpcEnvelope{}, nil, err
		}
		if len(envelope.ID) != 0 && sameID(envelope.ID, expectedID) {
			return envelope, raw, nil
		}
	}
}

type sseEvent struct {
	data    []byte
	comment bool
}

type sseReader struct {
	scanner *bufio.Scanner
}

func newSSEReader(r io.Reader) *sseReader {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 64*1024), maxSSETokenBytes)
	return &sseReader{scanner: scanner}
}

func (r *sseReader) next() (sseEvent, error) {
	var data []string
	for r.scanner.Scan() {
		line := strings.TrimSuffix(r.scanner.Text(), "\r")
		if strings.HasPrefix(line, ":") {
			return sseEvent{comment: true}, nil
		}
		if line == "" {
			if len(data) != 0 {
				return sseEvent{data: []byte(strings.Join(data, "\n"))}, nil
			}
			continue
		}
		if value, ok := strings.CutPrefix(line, "data:"); ok {
			data = append(data, strings.TrimSpace(value))
		}
	}
	if err := r.scanner.Err(); err != nil {
		return sseEvent{}, err
	}
	return sseEvent{}, io.EOF
}

func (r *sseReader) nextJSON() (rpcEnvelope, []byte, error) {
	for {
		event, err := r.next()
		if err != nil {
			return rpcEnvelope{}, nil, err
		}
		if len(event.data) == 0 {
			continue
		}
		var envelope rpcEnvelope
		if err := json.Unmarshal(event.data, &envelope); err != nil {
			return rpcEnvelope{}, event.data, err
		}
		return envelope, event.data, nil
	}
}

func validateSubscriptionID(paramsJSON json.RawMessage, expected json.RawMessage) error {
	var params struct {
		Meta map[string]json.RawMessage `json:"_meta"`
	}
	if err := json.Unmarshal(paramsJSON, &params); err != nil {
		return err
	}
	got, ok := params.Meta["io.modelcontextprotocol/subscriptionId"]
	if !ok {
		return errors.New("io.modelcontextprotocol/subscriptionId がありません")
	}
	if !sameID(got, expected) {
		return fmt.Errorf("subscriptionId = %s, want %s", got, expected)
	}
	return nil
}

func validateHonoredResource(paramsJSON json.RawMessage, uri string) error {
	var params struct {
		Notifications struct {
			ResourceSubscriptions []string `json:"resourceSubscriptions"`
		} `json:"notifications"`
	}
	if err := json.Unmarshal(paramsJSON, &params); err != nil {
		return err
	}
	if !contains(params.Notifications.ResourceSubscriptions, uri) {
		return fmt.Errorf("acknowledged filterが %q をhonorしていません: %v", uri, params.Notifications.ResourceSubscriptions)
	}
	return nil
}

func requireNoSession(resp *http.Response) error {
	if sessionID := resp.Header.Get("Mcp-Session-Id"); sessionID != "" {
		return fmt.Errorf("Mcp-Session-Idが発行されました: %q", sessionID)
	}
	return nil
}

func readBounded(r io.Reader) ([]byte, error) {
	limited := io.LimitReader(r, maxResponseBytes+1)
	body, err := io.ReadAll(limited)
	if err != nil {
		return nil, err
	}
	if len(body) > maxResponseBytes {
		return nil, fmt.Errorf("response bodyが%d bytesを超えました", maxResponseBytes)
	}
	return body, nil
}

func encodeHeaderValue(value string) string {
	plain := value != "" && value == strings.TrimSpace(value) &&
		!strings.HasPrefix(value, "=?base64?") && !strings.HasSuffix(value, "?=")
	if plain {
		for _, r := range value {
			if r < 0x20 || r > 0x7e {
				plain = false
				break
			}
		}
	}
	if plain {
		return value
	}
	return "=?base64?" + base64.StdEncoding.EncodeToString([]byte(value)) + "?="
}

func sameID(left, right json.RawMessage) bool {
	return bytes.Equal(bytes.TrimSpace(left), bytes.TrimSpace(right))
}

func contains(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func pass(w io.Writer, message string) {
	fmt.Fprintf(w, "✓ %s\n", message)
}
