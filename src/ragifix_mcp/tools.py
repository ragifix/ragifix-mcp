"""Outils MCP exposés par ragifix-mcp.

Chaque outil relaie simplement un appel vers l'API de ragifix — aucune
logique métier ici (pas de parsing, pas de chunking, pas d'embedding :
tout ça reste entièrement dans ragifix).

Les réponses utilisent des modèles Pydantic explicites plutôt qu'un `dict`
générique : le SDK MCP ne génère un schéma de sortie structuré
(`structured_content`) que pour des types de retour dont la forme est
connue (modèle Pydantic, dict paramétré, etc.) — un simple `-> dict` ne
produit qu'un bloc texte, sans structured_content exploitable par le
client.
"""

from __future__ import annotations

import base64
import logging

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from .ragifix_client import RagifixAsyncClient

logger = logging.getLogger(__name__)


class QueryResultItem(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: dict


class QueryToolResult(BaseModel):
    results: list[QueryResultItem]


class DocumentInfo(BaseModel):
    doc_id: str
    extension: str
    chunk_count: int
    metadata: dict
    updated_at: str


class ListDocumentsToolResult(BaseModel):
    documents: list[DocumentInfo]


class GetDocumentToolResult(BaseModel):
    found: bool
    doc_id: str
    document: DocumentInfo | None = None


class DeleteDocumentToolResult(BaseModel):
    doc_id: str
    deleted: bool


class HealthToolResult(BaseModel):
    ragifix_reachable: bool


def register_tools(mcp: MCPServer, client: RagifixAsyncClient) -> None:
    @mcp.tool()
    async def rag_query(query: str, top_k: int = 5) -> QueryToolResult:
        """Recherche les passages les plus pertinents dans la base documentaire ragifix pour une question donnée.

        Args:
            query: La question ou le texte à rechercher.
            top_k: Nombre maximum de résultats à retourner (défaut: 5).
        """
        raw = await client.query(query, top_k=top_k)
        return QueryToolResult(results=[QueryResultItem(**r) for r in raw["results"]])

    @mcp.tool()
    async def rag_list_documents(prefix: str | None = None) -> ListDocumentsToolResult:
        """Liste les documents actuellement indexés dans ragifix.

        Args:
            prefix: Filtre optionnel : ne retourne que les documents dont
                l'identifiant commence par ce préfixe.
        """
        documents = await client.list_documents(prefix=prefix)
        return ListDocumentsToolResult(documents=[DocumentInfo(**d) for d in documents])

    @mcp.tool()
    async def rag_get_document(doc_id: str) -> GetDocumentToolResult:
        """Retourne le détail d'un document indexé dans ragifix (nombre de chunks, métadonnées, date de mise à jour).

        Args:
            doc_id: Identifiant du document.
        """
        document = await client.get_document(doc_id)
        if document is None:
            return GetDocumentToolResult(found=False, doc_id=doc_id)
        return GetDocumentToolResult(found=True, doc_id=doc_id, document=DocumentInfo(**document))

    @mcp.tool()
    async def rag_add_document(
        doc_id: str,
        content: str,
        extension: str,
        content_encoding: str = "utf8",
        metadata: dict | None = None,
    ) -> DocumentInfo:
        """Ajoute ou met à jour un document dans ragifix.

        Args:
            doc_id: Identifiant unique du document (une mise à jour avec le
                même doc_id remplace le document existant).
            content: Le contenu du document. Texte brut si
                content_encoding="utf8" (adapté à txt/md), ou contenu
                binaire encodé en base64 si content_encoding="base64"
                (requis pour pdf/docx/pptx/xlsx/html).
            extension: Extension du fichier sans le point (ex: "txt", "md",
                "pdf", "docx", "pptx", "xlsx", "html").
            content_encoding: "utf8" ou "base64" (défaut: "utf8").
            metadata: Métadonnées libres à associer au document.
        """
        if content_encoding == "base64":
            raw = base64.b64decode(content)
        elif content_encoding == "utf8":
            raw = content.encode("utf-8")
        else:
            raise ValueError("content_encoding doit valoir 'utf8' ou 'base64'")
        result = await client.put_document(doc_id, raw, extension, metadata or {})
        return DocumentInfo(**result)

    @mcp.tool()
    async def rag_delete_document(doc_id: str) -> DeleteDocumentToolResult:
        """Supprime un document de ragifix. Sans effet si le document n'existait pas déjà (idempotent).

        Args:
            doc_id: Identifiant du document à supprimer.
        """
        existed = await client.delete_document(doc_id)
        return DeleteDocumentToolResult(doc_id=doc_id, deleted=existed)

    @mcp.tool()
    async def rag_health() -> HealthToolResult:
        """Vérifie que le service ragifix sous-jacent est joignable."""
        reachable = await client.health()
        return HealthToolResult(ragifix_reachable=reachable)
