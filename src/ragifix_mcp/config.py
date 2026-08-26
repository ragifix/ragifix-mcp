"""Modèle de configuration de ragifix-mcp.

Fichier YAML unique, indépendant de ragifix et ragifix-collector. Sa seule
responsabilité de configuration : où écouter (server), et où se trouve le
serveur ragifix principal à interroger (ragifix).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ConfigError(Exception):
    """Erreur de configuration (fichier invalide ou secret manquant)."""


class ServerConfig(BaseModel):
    # Local par défaut. Peut être mis à "0.0.0.0" (ou une IP précise) pour
    # un accès distant — voir le README pour la recommandation de placer un
    # reverse-proxy TLS devant dans ce cas.
    host: str = "127.0.0.1"
    port: int = 8422
    auth_token_env: str
    instructions: str = ""

    @property
    def auth_token(self) -> str:
        value = os.environ.get(self.auth_token_env)
        if not value:
            raise ConfigError(f"Variable d'environnement manquante: {self.auth_token_env}")
        return value


class RagifixConfig(BaseModel):
    base_url: str = "http://127.0.0.1:8421"
    api_token_env: str
    timeout_seconds: float = 60.0

    @property
    def api_token(self) -> str:
        value = os.environ.get(self.api_token_env)
        if not value:
            raise ConfigError(f"Variable d'environnement manquante: {self.api_token_env}")
        return value


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class McpSourceConfig(BaseModel):
    name: str
    description: str


class AppConfig(BaseModel):
    server: ServerConfig
    ragifix: RagifixConfig
    mcp_sources: list[McpSourceConfig] = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Fichier de configuration introuvable: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ConfigError(f"Fichier de configuration vide: {path}")
    try:
        return AppConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Configuration invalide ({path}): {exc}") from exc
