#!/usr/bin/env bash
# scripts/pull.sh — получает последние изменения из GitHub
#
# ОГРАНИЧЕНИЕ REPLIT:
# git fetch/pull/merge пишут в .git/objects/ — эти операции заблокированы
# в автоматическом агенте Replit. Скрипт показывает состояние и инструкцию.

set -euo pipefail

REMOTE_URL="https://github.com/Stemesss/AstrumManager"
BRANCH="main"

echo "========================================"
echo "  GIT PULL — AstrumManager"
echo "========================================"

# Проверка токена
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ОШИБКА: GITHUB_TOKEN не установлен в Replit Secrets."
  exit 1
fi

echo "Репозиторий : ${REMOTE_URL}"
echo ""

# Текущее состояние
echo "Локальный HEAD:"
git --no-optional-locks log --oneline -3
echo ""

# Незакоммиченные изменения
if ! git --no-optional-locks diff --quiet 2>/dev/null || \
   ! git --no-optional-locks diff --cached --quiet 2>/dev/null; then
  echo "⚠️  Есть незакоммиченные изменения:"
  git --no-optional-locks status --short 2>/dev/null || true
  echo ""
fi

echo "========================================" 
echo "  ОГРАНИЧЕНИЕ СРЕДЫ"
echo "========================================"
echo ""
echo "git pull/fetch заблокированы в среде агента Replit."
echo "Для получения изменений из GitHub выполните в Shell:"
echo ""
echo "  git pull https://\${GITHUB_TOKEN}@github.com/Stemesss/AstrumManager main"
echo ""
echo "Или используйте вкладку Git в интерфейсе Replit."
echo ""
echo "push.sh работает штатно — используйте его для отправки коммитов."
echo "========================================"
