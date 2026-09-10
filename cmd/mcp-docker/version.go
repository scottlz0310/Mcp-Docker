package main

import (
	"runtime/debug"
	"strings"
)

// version はリリースビルド時に -X main.version=<VERSION> で設定できる。
// 通常の go install では Go が埋め込む module build info を使う。
var version string

func currentVersion() string {
	moduleVersion := ""
	if info, ok := debug.ReadBuildInfo(); ok {
		moduleVersion = info.Main.Version
	}
	return resolveVersion(version, moduleVersion)
}

func resolveVersion(linkedVersion, moduleVersion string) string {
	if normalized := normalizeVersion(linkedVersion); normalized != "" {
		return normalized
	}
	if normalized := normalizeVersion(moduleVersion); normalized != "" {
		return normalized
	}
	return "dev"
}

func normalizeVersion(value string) string {
	value = strings.TrimSpace(value)
	if value == "" || value == "dev" || value == "(devel)" {
		return ""
	}
	return strings.TrimPrefix(value, "v")
}
