// Package mcpdocker はリポジトリ同梱アセットをバイナリへ埋め込む。
// skills/ をルートに置いたまま埋め込むため、モジュールルートに配置している。
package mcpdocker

import "embed"

// SkillsFS は skills/ 配下の skill カタログ。
// mcp-docker バイナリ 1 つで skill を配置できるよう埋め込む。
//
//go:embed all:skills
var SkillsFS embed.FS

// SkillsRoot は SkillsFS 内の skill カタログのルートディレクトリ。
const SkillsRoot = "skills"
