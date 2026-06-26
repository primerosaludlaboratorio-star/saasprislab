"""
Motor RAG (Cerebro Prislab)

- Ingesta de PDFs (PyPDF): extrae texto por página
- Chunking: 1000 caracteres (con solapamiento leve)
- Embeddings: Google (text-embedding-004)

Vector DB:
- Preferido: Chroma (chromadb) persistente
- Fallback (Windows/Python nuevos sin wheels): SQLite local + búsqueda por coseno (persistente)

Requiere:
  - GOOGLE_API_KEY en variables de entorno
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.conf import settings
import logging


@dataclass
class FuenteChunk:
    titulo: str
    categoria: str
    pagina: int
    chunk_id: str
    contenido: str


def _normalizar_texto(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extraer_texto_pdf_por_pagina(pdf_path: str) -> List[Tuple[int, str]]:
    """
    Extrae texto por página usando pypdf.
    Retorna lista de (numero_pagina_1based, texto).
    """
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    paginas = []
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en extraer_texto_pdf_por_pagina (rag_engine.py)")
            txt = ""
        txt = _normalizar_texto(txt)
        if txt:
            paginas.append((i + 1, txt))
    return paginas


def chunkear_texto(texto: str, chunk_size: int = 1000, overlap: int = 120) -> List[str]:
    """
    Divide texto en chunks por caracteres.
    """
    if not texto:
        return []
    chunks = []
    i = 0
    n = len(texto)
    while i < n:
        j = min(i + chunk_size, n)
        chunk = texto[i:j].strip()
        if chunk:
            chunks.append(chunk)
        if j == n:
            break
        i = max(j - overlap, 0)
    return chunks


def _persist_dir() -> str:
    persist_dir = os.path.join(getattr(settings, "BASE_DIR", "."), "rag_store")
    os.makedirs(persist_dir, exist_ok=True)
    return persist_dir


def _chroma_available() -> bool:
    try:
        import chromadb  # noqa: F401

        return True
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _chroma_available (rag_engine.py)")
        return False


def _get_chroma_client():
    import chromadb

    persist_dir = os.path.join(_persist_dir(), "chroma")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def _sqlite_path() -> str:
    return os.path.join(_persist_dir(), "rag.sqlite3")


def _sqlite_init():
    import sqlite3

    con = sqlite3.connect(_sqlite_path())
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_chunks (
            collection TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            documento_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            pagina INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            embedding BLOB NOT NULL,
            PRIMARY KEY (collection, chunk_id)
        )
        """
    )
    con.commit()
    con.close()


def _get_google_client():
    """Obtiene cliente de Google Generative AI usando cliente centralizado."""
    from core.utils.gemini_client import get_gemini_client
    return get_gemini_client()


def _collection_name(empresa_id: int, categoria: str) -> str:
    # Chroma requiere nombres simples
    categoria = (categoria or "GENERAL").upper()
    return f"prislab_{empresa_id}_{categoria}".lower()


def _embed_textos(textos: List[str]) -> List[List[float]]:
    """Genera embeddings usando Google text-embedding-004."""
    genai = _get_google_client()
    
    # Google Generative AI para embeddings
    # text-embedding-004 genera embeddings de 768 dimensiones
    embeddings = []
    for texto in textos:
        try:
            # Usar embed_content con el modelo text-embedding-004
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=texto,
                task_type="retrieval_document"
            )
            # El resultado es un dict con 'embedding' como lista
            if isinstance(result, dict) and 'embedding' in result:
                embeddings.append(result['embedding'])
            elif hasattr(result, 'embedding'):
                embeddings.append(result.embedding)
            else:
                # Si el formato es diferente, intentar acceder directamente
                embeddings.append(list(result) if hasattr(result, '__iter__') else [0.0] * 768)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _embed_textos (rag_engine.py)")
            # Si falla, generar embedding vacío del tamaño correcto (768 para text-embedding-004)
            embeddings.append([0.0] * 768)
    
    return embeddings


def ingerir_documento_pdf(
    *,
    documento_id: int,
    empresa_id: int,
    titulo: str,
    categoria: str,
    pdf_path: str,
) -> int:
    """
    Ingesta un documento PDF a Chroma (persistente).
    Retorna el número de chunks insertados.
    """
    paginas = extraer_texto_pdf_por_pagina(pdf_path)
    if not paginas:
        return 0

    collection_name = _collection_name(empresa_id, categoria)

    ids: List[str] = []
    metadatas: List[Dict] = []
    documents: List[str] = []

    for pagina_num, texto_pagina in paginas:
        chunks = chunkear_texto(texto_pagina, chunk_size=1000, overlap=120)
        for idx, ch in enumerate(chunks):
            chunk_id = f"doc{documento_id}_p{pagina_num}_c{idx}"
            ids.append(chunk_id)
            documents.append(ch)
            metadatas.append(
                {
                    "documento_id": documento_id,
                    "titulo": titulo,
                    "categoria": categoria,
                    "pagina": pagina_num,
                    "chunk_id": chunk_id,
                }
            )

    # embeddings por lote (para evitar queries lentas)
    embeddings = _embed_textos(documents)

    if _chroma_available():
        chroma = _get_chroma_client()
        collection = chroma.get_or_create_collection(name=collection_name)
        # upsert: permite reingesta sin duplicar (mismo chunk_id)
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    else:
        # Fallback SQLite persistente
        _sqlite_init()
        import sqlite3
        import numpy as np

        con = sqlite3.connect(_sqlite_path())
        cur = con.cursor()
        for cid, doc, meta, emb in zip(ids, documents, metadatas, embeddings):
            emb_bytes = np.asarray(emb, dtype=np.float32).tobytes()
            cur.execute(
                """
                INSERT OR REPLACE INTO rag_chunks
                (collection, chunk_id, documento_id, titulo, categoria, pagina, contenido, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_name,
                    cid,
                    int(meta["documento_id"]),
                    meta["titulo"],
                    meta["categoria"],
                    int(meta["pagina"]),
                    doc,
                    emb_bytes,
                ),
            )
        con.commit()
        con.close()
    return len(ids)


def consultar_cerebro(*, pregunta: str, empresa_id: int, categoria: str) -> Dict:
    """
    Busca 3 chunks más similares y consulta a GPT-4o respondiendo SOLO con el contexto.
    Retorna: {respuesta: str, fuentes: [..], contexto: [..]}
    """
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"respuesta": "Pregunta vacía.", "fuentes": [], "contexto": []}

    collection_name = _collection_name(empresa_id, categoria)
    q_emb = _embed_textos([pregunta])[0]

    docs = []
    metas = []

    if _chroma_available():
        chroma = _get_chroma_client()
        collection = chroma.get_or_create_collection(name=collection_name)
        results = collection.query(query_embeddings=[q_emb], n_results=3, include=["documents", "metadatas", "distances"])
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
    else:
        # Fallback SQLite: coseno sobre embeddings
        _sqlite_init()
        import sqlite3
        import numpy as np

        con = sqlite3.connect(_sqlite_path())
        cur = con.cursor()
        cur.execute(
            "SELECT chunk_id, documento_id, titulo, categoria, pagina, contenido, embedding FROM rag_chunks WHERE collection = ?",
            (collection_name,),
        )
        rows = cur.fetchall()
        con.close()

        if rows:
            q = np.asarray(q_emb, dtype=np.float32)
            qn = np.linalg.norm(q) + 1e-12
            scored = []
            for chunk_id, documento_id, titulo, cat, pagina, contenido, emb_blob in rows:
                v = np.frombuffer(emb_blob, dtype=np.float32)
                vn = np.linalg.norm(v) + 1e-12
                sim = float(np.dot(q, v) / (qn * vn))
                scored.append((sim, chunk_id, documento_id, titulo, cat, pagina, contenido))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:3]
            for sim, chunk_id, documento_id, titulo, cat, pagina, contenido in top:
                docs.append(contenido)
                metas.append(
                    {
                        "documento_id": documento_id,
                        "titulo": titulo,
                        "categoria": cat,
                        "pagina": pagina,
                        "chunk_id": chunk_id,
                    }
                )

    fuentes: List[str] = []
    contexto: List[FuenteChunk] = []
    for d, m in zip(docs, metas):
        if not m:
            continue
        titulo = m.get("titulo", "Documento")
        pagina = int(m.get("pagina", 0) or 0)
        chunk_id = m.get("chunk_id", "")
        fuentes.append(f"Fuente: {titulo} · Pág {pagina}")
        contexto.append(
            FuenteChunk(
                titulo=titulo,
                categoria=m.get("categoria", categoria),
                pagina=pagina,
                chunk_id=chunk_id,
                contenido=d,
            )
        )

    if not contexto:
        return {
            "respuesta": "No encontré contexto suficiente en la bóveda para responder esa pregunta.",
            "fuentes": [],
            "contexto": [],
        }

    system_prompt = (
        "Eres el Asistente Experto de Prislab. "
        "Responde SOLO basándote en el CONTEXTO proporcionado. "
        "Si el contexto no contiene la respuesta, di: 'No tengo suficiente información en los documentos cargados.' "
        "Al final incluye una línea: 'Fuente: ...' citando título y página."
    )

    contexto_texto = "\n\n".join(
        [f"[{i+1}] ({c.titulo} · Pág {c.pagina})\n{c.contenido}" for i, c in enumerate(contexto)]
    )

    user_prompt = (
        f"{system_prompt}\n\n"
        f"CONTEXTO:\n{contexto_texto}\n\n"
        f"PREGUNTA:\n{pregunta}\n\n"
        "RESPUESTA (incluye citas al final):"
    )

    # Usar Google Gemini via cliente centralizado
    from core.utils.gemini_client import get_gemini_client
    _rag_client = get_gemini_client()

    response = _rag_client.models.generate_content(
        model='gemini-2.0-flash',
        contents=user_prompt,
        config={'temperature': 0.2, 'max_output_tokens': 2000}
    )

    respuesta = response.text if response.text else ""
    # Asegurar que cite algo si el modelo omitió
    if "Fuente:" not in respuesta and fuentes:
        respuesta = respuesta.rstrip() + "\n\n" + "\n".join(sorted(set(fuentes))[:3])

    return {
        "respuesta": respuesta,
        "fuentes": sorted(set(fuentes))[:3],
        "contexto": [
            {
                "titulo": c.titulo,
                "pagina": c.pagina,
                "chunk_id": c.chunk_id,
            }
            for c in contexto
        ],
    }
