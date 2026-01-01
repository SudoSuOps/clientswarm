"""
File Upload API
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel

from api.auth import get_current_client
from services.ipfs import ipfs_service
from services.database import get_uploads_collection

router = APIRouter(prefix="/upload", tags=["upload"])


class UploadResponse(BaseModel):
    cid: str
    filename: str
    size: int
    content_type: str


class MultiUploadResponse(BaseModel):
    uploads: List[UploadResponse]
    combined_cid: str


# Allowed file types for medical imaging
ALLOWED_TYPES = {
    "application/dicom",
    "application/x-nifti",
    "image/png",
    "image/jpeg",
    "application/gzip",  # .nii.gz
    "application/octet-stream",  # Binary files
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    client: dict = Depends(get_current_client)
):
    """
    Upload a single file to IPFS.

    Returns the CID for the uploaded file.
    """
    # Read file
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB")

    # Upload to IPFS
    try:
        cid = await ipfs_service.upload_file(content, file.filename)
    except Exception as e:
        raise HTTPException(500, f"IPFS upload failed: {str(e)}")

    # Record upload
    uploads = get_uploads_collection()
    await uploads.insert_one({
        "cid": cid,
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
        "client_wallet": client["wallet"],
        "uploaded_at": datetime.utcnow()
    })

    return {
        "cid": cid,
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type or "application/octet-stream"
    }


@router.post("/files", response_model=MultiUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    client: dict = Depends(get_current_client)
):
    """
    Upload multiple files to IPFS.

    Returns individual CIDs and a combined directory CID.
    """
    if len(files) > 20:
        raise HTTPException(400, "Max 20 files per upload")

    uploads_list = []
    file_data = []

    for file in files:
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"File {file.filename} too large")

        cid = await ipfs_service.upload_file(content, file.filename)

        uploads_list.append({
            "cid": cid,
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type or "application/octet-stream"
        })

        file_data.append({
            "name": file.filename,
            "cid": cid,
            "size": len(content)
        })

    # Create directory manifest
    manifest = {
        "type": "upload_manifest",
        "files": file_data,
        "total_files": len(files),
        "client": client.get("ens") or client["wallet"],
        "uploaded_at": datetime.utcnow().isoformat()
    }

    combined_cid = await ipfs_service.upload_json(manifest)

    # Record uploads
    uploads_col = get_uploads_collection()
    for upload in uploads_list:
        await uploads_col.insert_one({
            **upload,
            "client_wallet": client["wallet"],
            "manifest_cid": combined_cid,
            "uploaded_at": datetime.utcnow()
        })

    return {
        "uploads": uploads_list,
        "combined_cid": combined_cid
    }
