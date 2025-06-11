# This file will contain profile-related API endpoints.
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from uuid import uuid4
import os

router = APIRouter(prefix="/profile", tags=["Profile"])

UPLOAD_DIR = "static/profile_photos"

@router.post("/upload-photo")
async def upload_profile_photo(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image format")

    file_ext = file.filename.split(".")[-1]
    filename = f"{uuid4().hex}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save the uploaded file to the static directory
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Return the URL for the uploaded profile photo
    return {"filename": filename, "url": f"/static/profile_photos/{filename}"}
