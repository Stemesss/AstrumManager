#!/usr/bin/env bash
# scripts/push.sh — отправляет ветку main в GitHub
# Поддерживает два имени токена: GITHUB_TOKEN и AstrumManagerMain

set -euo pipefail

REMOTE_URL="https://github.com/Stemesss/AstrumManager"
BRANCH="main"

echo "========================================"
echo "  GIT PUSH — AstrumManager"
echo "========================================"

# Определить токен: GITHUB_TOKEN имеет приоритет, затем AstrumManagerMain
if [ -n "${GITHUB_TOKEN:-}" ]; then
  GIT_PAT="${GITHUB_TOKEN}"
  echo "Токен       : GITHUB_TOKEN"
elif [ -n "${AstrumManagerMain:-}" ]; then
  GIT_PAT="${AstrumManagerMain}"
  echo "Токен       : AstrumManagerMain"
else
  echo "ОШИБКА: не найден ни GITHUB_TOKEN, ни AstrumManagerMain в Replit Secrets."
  echo "Добавьте один из них в Secrets и повторите."
  exit 1
fi

# Текущая ветка
CURRENT_BRANCH=$(git --no-optional-locks rev-parse --abbrev-ref HEAD)
echo "Текущая ветка : ${CURRENT_BRANCH}"
echo "Репозиторий   : ${REMOTE_URL}"

# Список последних коммитов
echo ""
echo "Последние коммиты:"
git --no-optional-locks log --oneline -5
echo ""

# Push через прямой URL с токеном
echo "Отправка в GitHub..."
git --no-optional-locks push \
    "https://${GIT_PAT}@github.com/Stemesss/AstrumManager" \
    "${CURRENT_BRANCH}:${BRANCH}" 2>&1

echo ""
echo "✅ Push выполнен успешно."
echo "========================================"
