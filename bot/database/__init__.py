# -*- coding: utf-8 -*-
"""Пакет работы с базой данных."""
from bot.database.db import Database
from bot.database.repositories import RepositoryRegistry

__all__ = ["Database", "RepositoryRegistry"]
