package main

import (
	"errors"
	"fmt"
	"io/fs"

	"github.com/scottlz0310/mcp-docker/v2/internal/profile"
	"github.com/scottlz0310/mcp-docker/v2/internal/register"
)

const defaultProfilePath = "config/mcp-profiles.yml"

// resolveProfile はプロファイルを読んで検証する。
// 既定のパスにファイルが無い場合は、プロファイルを使わない（nil）。--profile で明示したファイルが無ければエラーにする。
func resolveProfile(path string, explicit bool, agentNames, serverNames []string) (*profile.Profile, error) {
	p, err := profile.Load(path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) && !explicit {
			return nil, nil
		}
		return nil, fmt.Errorf("プロファイル: %w", err)
	}
	if err := p.Validate(agentNames, serverNames); err != nil {
		return nil, fmt.Errorf("プロファイル %s: %w", path, err)
	}
	return p, nil
}

// serversForAgent は agent に登録するサーバーを返す。
//   - explicit（--server の指定、対話選択）: 全 agent に chosen を登録する。
//   - プロファイルに宣言のある agent: 宣言されたサーバーだけ。
//   - 宣言のない agent、プロファイルが無い場合: 定義の全サーバー（従来どおり）。
func serversForAgent(agent string, all, chosen []register.Server, explicit bool, p *profile.Profile) []register.Server {
	if explicit {
		return chosen
	}
	if names, ok := p.Servers(agent); ok {
		return pickServers(all, selectIndices(all, names))
	}
	return all
}

// keepForAgent は prune で残す（削除候補にしない）サーバーを返す。
// プロファイルに宣言のある agent では、宣言と今回登録するサーバーの和集合。
// 今回登録したサーバーを、同じ実行の prune で消さないためである。
// 宣言のない agent、プロファイルが無い場合は、定義の全サーバー（従来どおり）。
func keepForAgent(agent string, all, registered []register.Server, p *profile.Profile) []register.Server {
	names, ok := p.Servers(agent)
	if !ok {
		return all
	}
	keep := make(map[string]struct{}, len(names)+len(registered))
	for _, name := range names {
		keep[name] = struct{}{}
	}
	for _, server := range registered {
		keep[server.Name] = struct{}{}
	}
	out := make([]register.Server, 0, len(keep))
	for _, server := range all {
		if _, ok := keep[server.Name]; ok {
			out = append(out, server)
		}
	}
	return out
}
