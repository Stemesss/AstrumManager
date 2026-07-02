#!/usr/bin/env bash
# scripts/push.sh — отправляет ветку main в GitHub через GITHUB_TOKEN

set -euo pipefail

REMOTE_URL="https://github.com/Stemesss/AstrumManager"
BRANCH="main"

echo "========================================"
echo "  GIT PUSH — AstrumManager"
echo "========================================"

# Проверка токена
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ОШИБКА: GITHUB_TOKEN не установлен в Replit Secrets."
  exit 1
fi

# Текущая ветка
CURRENT_BRANCH=$(git --no-optional-locks rev-parse --abbrev-ref HEAD)
echo "Текущая ветка : ${CURRENT_BRANCH}"
echo "Репозиторий   : ${REMOTE_URL}"

# Список новых коммитов (по локальным данным, трекинг-реф может быть устаревшим)
echo ""
echo "Последние коммиты:"
git --no-optional-locks log --oneline -5
echo ""

# Push через прямой URL с токеном
echo "Отправка в GitHub..."
git --no-optional-locks push \
    "https://${GITHUB_TOKEN}@github.com/Stemesss/AstrumManager" \
    "${CURRENT_BRANCH}:${BRANCH}" 2>&1

echo ""
echo "✅ Push выполнен успешно."
echo "========================================"
