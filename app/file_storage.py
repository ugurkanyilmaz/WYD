"""
File Storage Management for Profile Pictures
Handles upload, deletion, and URL generation for profile pictures
"""

import os
import uuid
import hashlib
import aiofiles
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
from typing import Optional

# Configuration
UPLOAD_DIR = "static/profile_pictures"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE = (1024, 1024)  # Max dimensions

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileStorageManager:
    """Manages file uploads and deletions for profile pictures"""
    
    @staticmethod
    def generate_filename(user_id: int, original_filename: str) -> str:
        """Generate unique filename for user's profile picture"""
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # Create hash from user_id and timestamp for uniqueness
        unique_id = uuid.uuid4().hex[:12]
        filename = f"user_{user_id}_{unique_id}{file_ext}"
        return filename
    
    @staticmethod
    def get_file_path(filename: str) -> str:
        """Get full file path"""
        return os.path.join(UPLOAD_DIR, filename)
    
    @staticmethod
    def get_public_url(filename: str) -> str:
        """Get public URL for the file"""
        return f"/static/profile_pictures/{filename}"
    
    @staticmethod
    async def validate_image(file: UploadFile) -> None:
        """Validate uploaded image file"""
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(400, "File too large. Max size is 5MB")
        
        # Check file extension
        file_ext = os.path.splitext(file.filename or '')[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check if it's a valid image by trying to open it
        try:
            content = await file.read()
            await file.seek(0)  # Reset file position
            
            with Image.open(io.BytesIO(content)) as img:
                # Basic image validation
                img.verify()
        except Exception:
            raise HTTPException(400, "Invalid image file")
    
    @staticmethod
    async def resize_image(file_content: bytes) -> bytes:
        """Resize image to max dimensions while maintaining aspect ratio"""
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # Convert to RGB if needed (handles RGBA, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                return output.getvalue()
        except Exception as e:
            raise HTTPException(400, f"Error processing image: {str(e)}")
    
    @classmethod
    async def save_profile_picture(cls, user_id: int, file: UploadFile) -> str:
        """Save uploaded profile picture and return public URL"""
        # Validate the image
        await cls.validate_image(file)
        
        # Generate filename
        filename = cls.generate_filename(user_id, file.filename or "profile.jpg")
        file_path = cls.get_file_path(filename)
        
        try:
            # Read and resize image
            content = await file.read()
            resized_content = await cls.resize_image(content)
            
            # Save to disk
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(resized_content)
            
            return cls.get_public_url(filename)
            
        except Exception as e:
            # Clean up file if it was created
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(500, f"Error saving file: {str(e)}")
    
    @classmethod
    async def delete_profile_picture(cls, picture_url: str) -> bool:
        """Delete profile picture from storage"""
        try:
            # Extract filename from URL
            filename = picture_url.split('/')[-1]
            file_path = cls.get_file_path(filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def get_default_avatar_url(user_id: int) -> str:
        """Generate a default avatar URL (could be Gravatar, identicon, etc.)"""
        # Simple implementation - could be enhanced with actual avatar generation
        hash_input = str(user_id).encode('utf-8')
        avatar_hash = hashlib.md5(hash_input).hexdigest()
        return f"https://www.gravatar.com/avatar/{avatar_hash}?d=identicon&s=256"

# Global instance
file_storage = FileStorageManager()
