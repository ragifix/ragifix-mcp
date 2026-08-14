"""Authentification de ragifix-mcp.

Un token bearer dédié (indépendant de celui de ragifix), comparé en temps
constant. Implémenté comme un middleware ASGI pur plutôt qu'un mécanisme
propre au SDK MCP (ex: OAuth), pour rester cohérent avec l'approche simple
utilisée dans le reste du projet (ragifix, ragifix-collector) et parce que
le SDK MCP ne fournit pas nativement de bearer token statique — seulement
un cadre OAuth 2.1, disproportionné pour ce besoin.
"""

from __future__ import annotations

import hmac

from starlette.types import ASGIApp, Receive, Scope, Send


class BearerAuthASGIMiddleware:
    def __init__(self, app: ASGIApp, expected_token: str):
        if not expected_token:
            raise ValueError("BearerAuthASGIMiddleware: le token attendu ne peut pas être vide")
        self._app = app
        self._expected_token = expected_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Laisse passer les scopes "lifespan" (démarrage/arrêt du
            # gestionnaire de session streamable-http) sans vérification.
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        if not auth.startswith("Bearer ") or not hmac.compare_digest(
            auth.removeprefix("Bearer ").strip(), self._expected_token
        ):
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": b'{"detail":"Token invalide ou manquant"}'})
            return

        await self._app(scope, receive, send)
