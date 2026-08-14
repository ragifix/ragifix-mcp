"""Point d'entrée de ragifix-mcp.

Transport Streamable HTTP (le standard actuel du protocole MCP pour un
serveur déployé/distant, par opposition à stdio qui suppose un lancement
en sous-processus local par le client).
"""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server.mcpserver import MCPServer

from .auth import BearerAuthASGIMiddleware
from .config import AppConfig, ConfigError, load_config
from .ragifix_client import RagifixAsyncClient
from .tools import register_tools

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"


def build_app(config: AppConfig):
    client = RagifixAsyncClient(
        base_url=config.ragifix.base_url,
        token=config.ragifix.api_token,
        timeout=config.ragifix.timeout_seconds,
    )

    mcp = MCPServer(
        name="ragifix-mcp",
        instructions=(
            "Donne accès à la base documentaire ragifix : recherche sémantique "
            "(rag_query), ajout et suppression de documents, et listing de ce qui "
            "est indexé. Utilise rag_query pour répondre à des questions à partir "
            "des documents indexés."
        ),
    )
    register_tools(mcp, client)

    inner_app = mcp.streamable_http_app(host=config.server.host, streamable_http_path=MCP_PATH)
    app = BearerAuthASGIMiddleware(inner_app, expected_token=config.server.auth_token)
    return app


def create_app(config_path: str) -> tuple:
    config = load_config(config_path)

    logging.basicConfig(
        level=config.logging.level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if config.server.host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            "ragifix-mcp est configuré pour écouter sur '%s' (accès non strictement "
            "local). Assurez-vous qu'un reverse-proxy TLS protège cet accès avant "
            "toute exposition réseau — voir le README, section 'Accès distant'.",
            config.server.host,
        )

    app = build_app(config)
    return app, config


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="ragifix-mcp — serveur MCP pour ragifix")
    parser.add_argument("--config", required=True, help="Chemin vers le fichier config.yaml")
    args = parser.parse_args()

    try:
        app, config = create_app(args.config)
    except ConfigError as exc:
        print(f"Erreur de configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(app, host=config.server.host, port=config.server.port, log_level=config.logging.level.lower())


if __name__ == "__main__":
    main()
