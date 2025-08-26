"""
AWS S3 File Storage Manager for Profile Pictures
Handles upload, deletion, and URL generation using AWS S3
"""

import os
import uuid
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
from typing import Optional
import asyncio
from functools import wraps

# AWS Configuration from environment
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") 
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION")

# File Configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE = (1024, 1024)  # Max dimensions

def async_wrapper(func):
    """Wrapper to make sync boto3 calls async"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return wrapper

class AWSS3FileStorage:
    """Manages file uploads and deletions using AWS S3"""
    
    def __init__(self):
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME, AWS_S3_REGION]):
            raise ValueError("Missing AWS credentials or configuration in environment variables")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_S3_REGION
        )
        self.bucket_name = AWS_S3_BUCKET_NAME
        self.region = AWS_S3_REGION
    
    def generate_s3_key(self, user_id: int, file_extension: str) -> str:
        """Generate unique S3 key for user's profile picture"""
        unique_id = uuid.uuid4().hex[:12]
        timestamp = uuid.uuid1().time
        return f"profile-pictures/user_{user_id}/{timestamp}_{unique_id}{file_extension}"
    
    def get_public_url(self, s3_key: str) -> str:
        """Get public URL for the S3 object"""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    async def validate_image(self, file: UploadFile) -> None:
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
    
    async def resize_image(self, file_content: bytes) -> bytes:
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
    
    @async_wrapper
    def _upload_to_s3(self, file_content: bytes, s3_key: str, content_type: str) -> None:
        """Upload file content to S3 (sync method wrapped as async)"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                CacheControl='max-age=31536000',  # Cache for 1 year
                Metadata={
                    'uploaded-by': 'wyd-backend',
                    'file-type': 'profile-picture'
                }
            )
        except NoCredentialsError:
            raise HTTPException(500, "AWS credentials not found")
        except ClientError as e:
            raise HTTPException(500, f"Failed to upload to S3: {str(e)}")
    
    @async_wrapper  
    def _delete_from_s3(self, s3_key: str) -> bool:
        """Delete file from S3 (sync method wrapped as async)"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    @async_wrapper
    def _check_s3_object_exists(self, s3_key: str) -> bool:
        """Check if S3 object exists"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def extract_s3_key_from_url(self, url: str) -> Optional[str]:
        """Extract S3 key from public URL"""
        if not url or not url.startswith(f"https://{self.bucket_name}.s3."):
            return None
        
        try:
            # Extract key from URL: https://bucket.s3.region.amazonaws.com/key
            key = url.split(f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/", 1)[1]
            return key
        except (IndexError, ValueError):
            return None
    
    async def upload_profile_picture(self, user_id: int, file: UploadFile) -> str:
        """Upload profile picture to S3 and return public URL"""
        # Validate the image
        await self.validate_image(file)
        
        # Generate S3 key
        file_ext = os.path.splitext(file.filename or '.jpg')[1].lower()
        s3_key = self.generate_s3_key(user_id, file_ext)
        
        try:
            # Read and resize image
            content = await file.read()
            resized_content = await self.resize_image(content)
            
            # Upload to S3
            await self._upload_to_s3(resized_content, s3_key, 'image/jpeg')
            
            # Return public URL
            return self.get_public_url(s3_key)
            
        except Exception as e:
            raise HTTPException(500, f"Error uploading file: {str(e)}")
    
    async def delete_profile_picture(self, picture_url: str) -> bool:
        """Delete profile picture from S3"""
        s3_key = self.extract_s3_key_from_url(picture_url)
        if not s3_key:
            return False
        
        try:
            return await self._delete_from_s3(s3_key)
        except Exception:
            return False
    
    async def get_presigned_upload_url(self, user_id: int, file_extension: str, expires_in: int = 3600) -> dict:
        """Generate presigned URL for direct upload from frontend"""
        s3_key = self.generate_s3_key(user_id, file_extension)
        
        try:
            @async_wrapper
            def generate_presigned_post():
                return self.s3_client.generate_presigned_post(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Fields={
                        'Content-Type': 'image/jpeg',
                        'Cache-Control': 'max-age=31536000'
                    },
                    Conditions=[
                        ['content-length-range', 1024, MAX_FILE_SIZE],  # 1KB to 5MB
                        {'Content-Type': 'image/jpeg'}
                    ],
                    ExpiresIn=expires_in
                )
            
            presigned_post = await generate_presigned_post()
            
            return {
                'upload_url': presigned_post['url'],
                'fields': presigned_post['fields'],
                'public_url': self.get_public_url(s3_key),
                's3_key': s3_key,
                'expires_in': expires_in
            }
            
        except Exception as e:
            raise HTTPException(500, f"Error generating presigned URL: {str(e)}")
    
    @staticmethod
    def get_default_avatar_url(user_id: int) -> str:
        """Generate a default avatar URL"""
        import hashlib
        hash_input = str(user_id).encode('utf-8')
        avatar_hash = hashlib.md5(hash_input).hexdigest()
        return f"https://www.gravatar.com/avatar/{avatar_hash}?d=identicon&s=256"

# Global instance
s3_storage = AWSS3FileStorage()
