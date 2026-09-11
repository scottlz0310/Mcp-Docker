package main

import "testing"

func TestResolveVersion(t *testing.T) {
	tests := []struct {
		name          string
		linkedVersion string
		moduleVersion string
		want          string
	}{
		{name: "linked release version", linkedVersion: "2.21.1", moduleVersion: "v2.20.0", want: "2.21.1"},
		{name: "linked version with v prefix", linkedVersion: "v2.21.1", want: "2.21.1"},
		{name: "module release version", moduleVersion: "v2.21.1", want: "2.21.1"},
		{name: "module pseudo version", moduleVersion: "v2.21.2-0.20260910225750-17859fc3606c+dirty", want: "2.21.2-0.20260910225750-17859fc3606c+dirty"},
		{name: "development build", linkedVersion: "dev", moduleVersion: "(devel)", want: "dev"},
		{name: "empty build info", want: "dev"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := resolveVersion(tt.linkedVersion, tt.moduleVersion); got != tt.want {
				t.Fatalf("resolveVersion(%q, %q) = %q, want %q", tt.linkedVersion, tt.moduleVersion, got, tt.want)
			}
		})
	}
}
