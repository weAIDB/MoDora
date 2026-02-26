import hashlib
import logging

import chromadb
from chromadb.config import Settings as ChromaSettings

from modora.core.domain import CCTree, CCTreeNode, RetrievalResult
from modora.core.infra.llm import AsyncLLMFactory
from modora.core.settings import Settings

logger = logging.getLogger(__name__)


class VectorRetriever:
    def __init__(
        self,
        settings: Settings | None = None,
        instance_id: str | None = None,
        *,
        top_k: int = 5,
        min_score: float = 0.15,
        max_workers: int = 8,
    ):
        self.settings = settings or Settings.load()
        self.embedding_client = AsyncLLMFactory.create_embedding(self.settings)
        self.rerank_client = AsyncLLMFactory.create_rerank(self.settings)
        self.top_k = top_k
        self.min_score = min_score
        self.max_workers = max_workers
        if self.settings.chroma_persist_path:
            self.chroma_client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            self.chroma_client = chromadb.Client(
                ChromaSettings(anonymized_telemetry=False)
            )

    async def retrieve(
        self,
        tree: CCTree,
        query: str,
        source_path: str | dict[str, str],
    ) -> RetrievalResult:
        logger.info(f"Starting vector retrieval for query: {query}")
        result = RetrievalResult()

        nodes: list[tuple[str, CCTreeNode]] = []
        self._collect_nodes(tree.root, "root", source_path, nodes)
        if not nodes:
            return result

        documents: list[str] = []
        ids: list[str] = []
        metadatas: list[dict[str, str]] = []
        node_map: dict[str, CCTreeNode] = {}
        path_map: dict[str, str] = {}
        sources: set[str] = set()

        for path, node in nodes:
            text = self._build_node_text(path, node)
            if not text:
                continue
            source = self._get_node_source(path, source_path)
            doc_id = f"{source}::{path}"
            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

            documents.append(text)
            ids.append(doc_id)
            metadatas.append({"source": source, "path": path, "hash": text_hash})
            node_map[doc_id] = node
            path_map[doc_id] = path
            sources.add(source)

        if not documents:
            return result

        collection = self.chroma_client.get_or_create_collection(
            name="modora_kb",
            metadata={"hnsw:space": "cosine"},
        )

        existing = collection.get(ids=ids, include=["metadatas"])
        existing_map: dict[str, str] = {}
        if existing and existing.get("ids"):
            for i, doc_id in enumerate(existing["ids"]):
                meta = existing["metadatas"][i] if existing.get("metadatas") else None
                if meta and "hash" in meta:
                    existing_map[doc_id] = meta["hash"]

        missing_indices: list[int] = []
        for i, doc_id in enumerate(ids):
            if (
                doc_id not in existing_map
                or existing_map[doc_id] != metadatas[i]["hash"]
            ):
                missing_indices.append(i)

        if missing_indices:
            logger.info(
                f"Found {len(missing_indices)} documents missing embeddings. Generating..."
            )
            missing_docs = [documents[i] for i in missing_indices]
            missing_ids = [ids[i] for i in missing_indices]
            missing_metadatas = [metadatas[i] for i in missing_indices]

            new_embeddings = await self.embedding_client.embed(missing_docs)
            if not new_embeddings or len(new_embeddings) != len(missing_docs):
                return result
            collection.upsert(
                documents=missing_docs,
                ids=missing_ids,
                embeddings=new_embeddings,
                metadatas=missing_metadatas,
            )
            logger.info(f"Upserted {len(missing_docs)} new embeddings to Chroma.")

        query_embeddings = await self.embedding_client.embed([query])
        if not query_embeddings:
            return result

        where_filter: dict[str, object] | None = None
        if len(sources) == 1:
            where_filter = {"source": list(sources)[0]}
        elif len(sources) > 1:
            where_filter = {"source": {"$in": list(sources)}}

        raw = collection.query(
            query_embeddings=query_embeddings,
            n_results=min(len(documents), self.top_k * 4),
            where=where_filter,
        )
        logger.info(f"Chroma query returned {len(raw.get('ids', [[]])[0])} raw results")
        scored: list[tuple[float, str, CCTreeNode]] = []
        if raw.get("ids") and raw.get("distances"):
            found_ids = raw["ids"][0]
            found_distances = raw["distances"][0]
            for doc_id, dist in zip(found_ids, found_distances):
                score = 1.0 - dist
                if score >= self.min_score and doc_id in node_map:
                    scored.append((score, doc_id, node_map[doc_id]))

        if not scored:
            return result

        scored.sort(key=lambda x: x[0], reverse=True)
        rerank_candidates = scored[: self.top_k * 3]
        logger.info(f"Reranking {len(rerank_candidates)} candidates...")
        reranked = await self._rerank(query, rerank_candidates)
        final_candidates = reranked[: self.top_k]
        logger.info(
            f"Vector retrieval finished. Found {len(final_candidates)} relevant docs."
        )

        for _score, doc_id, node in final_candidates:
            path = path_map.get(doc_id, doc_id)
            if node.data:
                result.text_map[path] = node.data
            if node.location:
                result.locations.extend(node.location)
                result.locations_by_path.setdefault(path, []).extend(node.location)

        result.normalize_locations()
        return result

    def _get_node_source(self, path: str, source_path: str | dict[str, str]) -> str:
        if isinstance(source_path, str):
            return source_path
        parts = path.split("--")
        if len(parts) > 1:
            return parts[1]
        return list(source_path.keys())[0] if source_path else "unknown"

    async def _rerank(
        self, query: str, candidates: list[tuple[float, str, CCTreeNode]]
    ) -> list[tuple[float, str, CCTreeNode]]:
        if not candidates:
            return candidates

        documents: list[str] = []
        for _score, path, node in candidates:
            documents.append(self._build_node_text(path, node))

        scores = await self.rerank_client.rerank(query, documents)

        reranked: list[tuple[float, str, CCTreeNode]] = []
        for score, (_base, path, node) in zip(scores, candidates):
            if score >= self.min_score:
                reranked.append((score, path, node))

        if not reranked:
            return candidates

        reranked.sort(key=lambda x: x[0], reverse=True)
        return reranked

    def _collect_nodes(
        self,
        node: CCTreeNode,
        path: str,
        source_path: str | dict[str, str],
        out: list[tuple[str, CCTreeNode]],
    ) -> None:
        if isinstance(source_path, dict):
            parts = path.split("--")
            if len(parts) > 1:
                file_name = parts[1]
                if node.location:
                    for loc in node.location:
                        if not loc.file_name:
                            loc.file_name = file_name

        if node.data and node.has_content():
            out.append((path, node))

        for child_key, child_node in node.children.items():
            child_path = f"{path}--{child_key}"
            self._collect_nodes(child_node, child_path, source_path, out)

    def _build_node_text(self, path: str, node: CCTreeNode) -> str:
        base_path = path.split("--")[-1] if "--" in path else path
        parts = [base_path]
        if node.metadata:
            parts.append(str(node.metadata))
        if node.data:
            parts.append(node.data)
        return "\n".join(parts).strip()
