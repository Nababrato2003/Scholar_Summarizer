"""
storage.py - Dedicated MongoDB Atlas Storage & GridFS Engine for ScholarCritic.
Handles persistent storage and retrieval of research paper review histories
and raw binary PDF documents using GridFS chunked storage.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import gridfs
try:
    import certifi
    _ca_file = certifi.where()
except Exception:
    _ca_file = None
from dotenv import load_dotenv

load_dotenv()

# Singleton MongoDB storage client
_storage_client = None


def get_storage_db():
    """
    Returns connected MongoDB Atlas database for paper storage & GridFS.
    Uses MONGO_STORAGE_URI if provided, falling back to MONGO_URI.
    """
    global _storage_client
    uri = os.getenv("MONGO_STORAGE_URI") or os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("Neither MONGO_STORAGE_URI nor MONGO_URI is configured.")

    if _storage_client is None:
        client_kwargs = {
            "server_api": ServerApi('1'),
            "serverSelectionTimeoutMS": 5000
        }
        if _ca_file:
            client_kwargs["tlsCAFile"] = _ca_file
        _storage_client = MongoClient(uri, **client_kwargs)

    return _storage_client["scholar_critic_storage"]


def get_gridfs():
    """Returns GridFS instance attached to the storage database."""
    db = get_storage_db()
    return gridfs.GridFS(db)


def save_paper_history(
    user_email: str,
    filename: str,
    pdf_bytes: bytes,
    analysis_result: Dict[str, Any]
) -> str:
    """
    Stores binary PDF in GridFS and saves structured analysis metadata
    in the paper_history collection.
    
    Returns:
        str: String representation of the paper's history ObjectId.
    """
    clean_email = user_email.strip().lower()
    db = get_storage_db()
    fs = get_gridfs()

    # 1. Store the binary PDF in GridFS
    file_id = fs.put(
        pdf_bytes,
        filename=filename,
        content_type="application/pdf",
        uploaded_by=clean_email,
        uploaded_at=datetime.utcnow()
    )

    # 2. Extract metadata and scoring for easy indexing and listing
    meta = analysis_result.get("metadata", {})
    scores = analysis_result.get("scores", {})
    summary = analysis_result.get("summary", {})

    paper_title = meta.get("title") or filename
    
    # 3. Insert record into paper_history
    history_record = {
        "user_email": clean_email,
        "filename": filename,
        "file_size": len(pdf_bytes),
        "gridfs_file_id": file_id,
        "paper_title": paper_title,
        "created_at": datetime.utcnow(),
        "scores": scores,
        "tldr": summary.get("tldr", "No summary available."),
        "analysis_result": analysis_result
    }

    result = db["paper_history"].insert_one(history_record)
    return str(result.inserted_id)


def get_user_history(user_email: str) -> List[Dict[str, Any]]:
    """
    Retrieves all past papers analyzed by the user, sorted newest first.
    Lightweight projection (omits full raw analysis payload for faster loading).
    """
    clean_email = user_email.strip().lower()
    db = get_storage_db()

    cursor = db["paper_history"].find(
        {"user_email": clean_email},
        {
            "_id": 1,
            "filename": 1,
            "file_size": 1,
            "paper_title": 1,
            "created_at": 1,
            "scores": 1,
            "tldr": 1
        }
    ).sort("created_at", -1)

    items = []
    for doc in cursor:
        items.append({
            "id": str(doc["_id"]),
            "filename": doc.get("filename", "paper.pdf"),
            "file_size": doc.get("file_size", 0),
            "paper_title": doc.get("paper_title", "Untitled Research Paper"),
            "created_at": doc.get("created_at").strftime("%Y-%m-%d %H:%M UTC") if doc.get("created_at") else "N/A",
            "scores": doc.get("scores", {}),
            "tldr": doc.get("tldr", "")
        })

    return items


def get_paper_review(paper_id: str, user_email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the full analysis result JSON for a specific paper,
    ensuring it belongs to the authenticated user.
    """
    clean_email = user_email.strip().lower()
    db = get_storage_db()

    try:
        oid = ObjectId(paper_id)
    except Exception:
        return None

    doc = db["paper_history"].find_one({"_id": oid, "user_email": clean_email})
    if not doc:
        return None

    return doc.get("analysis_result")


def get_paper_pdf(paper_id: str, user_email: str) -> Optional[Tuple[str, bytes]]:
    """
    Retrieves the original PDF file bytes from GridFS.
    Returns:
        tuple (filename, bytes) or None if not found/unauthorized.
    """
    clean_email = user_email.strip().lower()
    db = get_storage_db()
    fs = get_gridfs()

    try:
        oid = ObjectId(paper_id)
    except Exception:
        return None

    doc = db["paper_history"].find_one({"_id": oid, "user_email": clean_email})
    if not doc or "gridfs_file_id" not in doc:
        return None

    try:
        grid_file = fs.get(doc["gridfs_file_id"])
        pdf_bytes = grid_file.read()
        filename = doc.get("filename", "research_paper.pdf")
        return filename, pdf_bytes
    except Exception:
        return None


def delete_paper_history(paper_id: str, user_email: str) -> bool:
    """
    Deletes a paper history record and deletes its corresponding PDF chunks from GridFS.
    """
    clean_email = user_email.strip().lower()
    db = get_storage_db()
    fs = get_gridfs()

    try:
        oid = ObjectId(paper_id)
    except Exception:
        return False

    doc = db["paper_history"].find_one({"_id": oid, "user_email": clean_email})
    if not doc:
        return False

    # Delete from GridFS if present
    if "gridfs_file_id" in doc:
        try:
            fs.delete(doc["gridfs_file_id"])
        except Exception:
            pass

    # Delete metadata record
    result = db["paper_history"].delete_one({"_id": oid, "user_email": clean_email})
    return result.deleted_count > 0
