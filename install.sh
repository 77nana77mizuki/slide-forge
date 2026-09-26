#!/usr/bin/env bash
# Slide Forge 手動インストール（プラグインを使わない場合）
#   ./install.sh            → ~/.claude/skills と ~/.claude/agents にコピー（全プロジェクトで使える）
#   ./install.sh --project  → ./.claude/ にコピー（このプロジェクトだけ）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude"
[[ "${1:-}" == "--project" ]] && DEST="$(pwd)/.claude"
mkdir -p "$DEST/skills" "$DEST/agents"
rm -rf "$DEST/skills/slide-forge"
cp -R "$HERE/skills/slide-forge" "$DEST/skills/slide-forge"
cp "$HERE/agents/"*.md "$DEST/agents/"
echo "✓ skill  → $DEST/skills/slide-forge"
echo "✓ agents → $DEST/agents/ (slide-storyteller, slide-reviewer)"
if ! python3 -c "import playwright, PIL" 2>/dev/null; then
  echo "… installing Python deps (playwright, pillow)"
  python3 -m pip install --user playwright pillow || python3 -m pip install --break-system-packages playwright pillow
fi
python3 -m playwright install chromium >/dev/null && echo "✓ Chromium for Playwright ready"
echo "完了。Claude Code を再起動し「/slide-forge 〇〇の発表資料を作って」と話しかけてください。"
