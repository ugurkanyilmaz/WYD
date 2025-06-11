# This file will contain user-related API endpoints.
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import shutil

from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.core.security import decode_access_token

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{username}", response_model=UserResponse)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/me/upload-photo")
def upload_profile_photo(file: UploadFile = File(...), db: Session = Depends(get_db), token: str = Depends(security.oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_ext = file.filename.split(".")[-1]
    if file_ext not in ["jpg", "jpeg", "png"]:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_name = f"{user.id}_profile.{file_ext}"
    file_path = os.path.join("static", "profile_photos", file_name)

    # Save the uploaded profile photo to the static directory
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.profile_photo = file_path
    db.commit()

    return JSONResponse({"msg": "Profile photo uploaded successfully", "path": file_path})

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(security.get_current_user)):
    return current_user