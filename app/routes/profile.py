"""
Profile Management Routes
Handles all profile-related operations including picture upload, bio editing, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import Optional
from ..schemas.users import UserOut, ProfileUpdateIn, ProfilePictureUploadOut, ActionOkOut
from ..crud import (
    update_profile_picture,
    remove_profile_picture, 
    update_user_bio,
    update_user_display_name,
    get_user_profile
)
from ..auth import get_current_user
from ..cache import (
    get_cached_user_data, 
    invalidate_user_cache, 
    check_rate_limit
)
from ..queue_manager import enqueue_user_activity
from ..aws_storage import s3_storage

router = APIRouter()

# ==================== PROFILE PICTURE MANAGEMENT ====================

@router.post('/picture/upload', response_model=ProfilePictureUploadOut)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and set user's profile picture to AWS S3"""
    # Rate limiting - max 5 uploads per hour
    if not await check_rate_limit(
        current_user['id'], 
        "profile_picture_upload", 
        limit=5, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many uploads.")
    
    try:
        # Upload to AWS S3
        picture_url = await s3_storage.upload_profile_picture(current_user['id'], file)
        
        # Update database
        user = await update_profile_picture(current_user['id'], picture_url)
        if not user:
            # If database update fails, try to clean up S3
            await s3_storage.delete_profile_picture(picture_url)
            raise HTTPException(404, "User not found")
        
        # Invalidate cache
        await invalidate_user_cache(current_user['id'])
        
        # Queue profile update activity (for analytics, feed updates etc.)
        await enqueue_user_activity(
            current_user['id'], 
            "profile_picture_updated", 
            {
                "picture_url": picture_url,
                "storage": "aws_s3",
                "file_size": file.size,
                "content_type": file.content_type
            }
        )
        
        return ProfilePictureUploadOut(
            profile_picture_url=picture_url,
            message="Profile picture updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to upload profile picture: {str(e)}")


@router.delete('/picture', response_model=ActionOkOut)
async def delete_profile_picture(current_user: dict = Depends(get_current_user)):
    """Remove user's profile picture from both database and AWS S3"""
    # Rate limiting - max 10 deletions per hour
    if not await check_rate_limit(
        current_user['id'], 
        "profile_picture_delete", 
        limit=10, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many deletions.")
    
    try:
        # Remove from database and get old URL
        result = await remove_profile_picture(current_user['id'])
        if not result:
            raise HTTPException(404, "User not found")
        
        user, old_url = result
        
        # Delete file from S3 if it exists
        s3_deleted = False
        if old_url:
            s3_deleted = await s3_storage.delete_profile_picture(old_url)
        
        # Invalidate cache
        await invalidate_user_cache(current_user['id'])
        
        # Queue profile update activity
        await enqueue_user_activity(
            current_user['id'], 
            "profile_picture_deleted", 
            {
                "old_url": old_url,
                "s3_deleted": s3_deleted
            }
        )
        
        return ActionOkOut(message="Profile picture removed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete profile picture: {str(e)}")


@router.get('/picture/presigned-upload', response_model=dict)
async def get_presigned_upload_url(
    file_extension: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Get presigned URL for direct upload to S3 from frontend"""
    # Rate limiting - max 10 presigned URLs per hour
    if not await check_rate_limit(
        current_user['id'], 
        "presigned_url_request", 
        limit=10, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many requests.")
    
    # Validate file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    if file_extension.lower() not in allowed_extensions:
        raise HTTPException(400, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}")
    
    try:
        presigned_data = await s3_storage.get_presigned_upload_url(
            current_user['id'], 
            file_extension.lower()
        )
        
        # Queue activity for analytics
        await enqueue_user_activity(
            current_user['id'], 
            "presigned_url_requested", 
            {"file_extension": file_extension}
        )
        
        return presigned_data
        
    except Exception as e:
        raise HTTPException(500, f"Failed to generate presigned URL: {str(e)}")


# ==================== PROFILE INFO MANAGEMENT ====================

@router.put('/info', response_model=UserOut)
async def update_profile_info(
    profile_data: ProfileUpdateIn,
    current_user: dict = Depends(get_current_user)
):
    """Update user's bio and display name"""
    # Rate limiting - max 20 profile updates per hour
    if not await check_rate_limit(
        current_user['id'], 
        "profile_update", 
        limit=20, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many profile updates.")
    
    try:
        updated_user = None
        updates = {}
        
        # Update bio if provided
        if profile_data.bio is not None:
            bio_text = profile_data.bio.strip()
            if len(bio_text) > 500:
                raise HTTPException(400, "Bio must be 500 characters or less")
            
            updated_user = await update_user_bio(current_user['id'], bio_text)
            updates["bio"] = bio_text
        
        # Update display name if provided
        if profile_data.display_name is not None:
            display_name = profile_data.display_name.strip()
            if len(display_name) > 100:
                raise HTTPException(400, "Display name must be 100 characters or less")
            if len(display_name) < 1:
                raise HTTPException(400, "Display name cannot be empty")
            
            updated_user = await update_user_display_name(current_user['id'], display_name)
            updates["display_name"] = display_name
        
        if not updated_user:
            # No updates were made, get current user data
            updated_user = await get_user_profile(current_user['id'])
            if not updated_user:
                raise HTTPException(404, "User not found")
        
        # Invalidate cache
        await invalidate_user_cache(current_user['id'])
        
        # Queue profile update activity
        if updates:
            await enqueue_user_activity(
                current_user['id'], 
                "profile_info_updated", 
                updates
            )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update profile: {str(e)}")


@router.put('/bio', response_model=UserOut)
async def update_bio_only(
    bio: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Update only user's bio (separate endpoint for convenience)"""
    # Rate limiting - max 30 bio updates per hour
    if not await check_rate_limit(
        current_user['id'], 
        "bio_update", 
        limit=30, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many bio updates.")
    
    bio_text = bio.strip()
    if len(bio_text) > 500:
        raise HTTPException(400, "Bio must be 500 characters or less")
    
    try:
        updated_user = await update_user_bio(current_user['id'], bio_text)
        if not updated_user:
            raise HTTPException(404, "User not found")
        
        # Invalidate cache
        await invalidate_user_cache(current_user['id'])
        
        # Queue activity
        await enqueue_user_activity(
            current_user['id'], 
            "bio_updated", 
            {"bio": bio_text, "bio_length": len(bio_text)}
        )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update bio: {str(e)}")


@router.put('/display-name', response_model=UserOut) 
async def update_display_name_only(
    display_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Update only user's display name (separate endpoint for convenience)"""
    # Rate limiting - max 15 display name updates per hour
    if not await check_rate_limit(
        current_user['id'], 
        "display_name_update", 
        limit=15, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many display name updates.")
    
    name = display_name.strip()
    if len(name) > 100:
        raise HTTPException(400, "Display name must be 100 characters or less")
    if len(name) < 1:
        raise HTTPException(400, "Display name cannot be empty")
    
    try:
        updated_user = await update_user_display_name(current_user['id'], name)
        if not updated_user:
            raise HTTPException(404, "User not found")
        
        # Invalidate cache
        await invalidate_user_cache(current_user['id'])
        
        # Queue activity
        await enqueue_user_activity(
            current_user['id'], 
            "display_name_updated", 
            {"display_name": name}
        )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update display name: {str(e)}")


# ==================== PROFILE VIEWING ====================

@router.get('/me', response_model=UserOut)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's full profile"""
    # Check cache first
    cached_user = await get_cached_user_data(current_user['id'])
    if cached_user:
        # Queue view activity for analytics
        await enqueue_user_activity(current_user['id'], "profile_viewed_own", {})
        return cached_user
    
    # Get from database
    user = await get_user_profile(current_user['id'])
    if not user:
        raise HTTPException(404, "User not found")
    
    # Cache the user data
    user_dict = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "phone_number": user.phone_number,
        "display_name": user.display_name,
        "profile_picture_url": user.profile_picture_url,
        "bio": user.bio
    }
    await invalidate_user_cache(current_user['id'])  # Refresh cache
    
    # Queue profile view activity (for analytics)
    await enqueue_user_activity(current_user['id'], "profile_viewed_own", {})
    
    return user


@router.get('/{user_id}', response_model=UserOut)
async def view_user_profile(
    user_id: int, 
    current_user: dict = Depends(get_current_user)
):
    """View another user's profile (queue for analytics and recommendations)"""
    # Rate limiting - max 100 profile views per hour
    if not await check_rate_limit(
        current_user['id'], 
        "profile_view", 
        limit=100, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many profile views.")
    
    # Check cache first
    cached_user = await get_cached_user_data(user_id)
    if cached_user:
        # Queue the profile view activity
        await enqueue_user_activity(
            current_user['id'], 
            "profile_viewed_other", 
            {"viewed_user_id": user_id}
        )
        return cached_user
    
    # Get from database
    user = await get_user_profile(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Cache the user data
    user_dict = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "phone_number": user.phone_number,
        "display_name": user.display_name,
        "profile_picture_url": user.profile_picture_url,
        "bio": user.bio
    }
    # Cache for 30 minutes
    await invalidate_user_cache(user_id)
    
    # Queue the profile view activity (for analytics, recommendations, etc.)
    await enqueue_user_activity(
        current_user['id'], 
        "profile_viewed_other", 
        {
            "viewed_user_id": user_id,
            "viewed_username": user.username,
            "timestamp": "queued_for_processing"
        }
    )
    
    return user


# ==================== PROFILE STATS & ANALYTICS ====================

@router.get('/me/stats', response_model=dict)
async def get_profile_stats(current_user: dict = Depends(get_current_user)):
    """Get user's profile statistics"""
    # This could be enhanced to show profile view counts, etc.
    # For now, return basic info
    
    try:
        user = await get_user_profile(current_user['id'])
        if not user:
            raise HTTPException(404, "User not found")
        
        stats = {
            "user_id": user.id,
            "username": user.username,
            "has_profile_picture": bool(user.profile_picture_url),
            "has_bio": bool(user.bio and len(user.bio.strip()) > 0),
            "bio_length": len(user.bio or ""),
            "profile_completion": 0
        }
        
        # Calculate profile completion percentage
        completion_factors = [
            bool(user.profile_picture_url),  # Has profile picture
            bool(user.bio and len(user.bio.strip()) > 0),  # Has bio
            bool(user.display_name),  # Has display name
        ]
        stats["profile_completion"] = (sum(completion_factors) / len(completion_factors)) * 100
        
        # Queue analytics event
        await enqueue_user_activity(
            current_user['id'], 
            "profile_stats_viewed", 
            stats
        )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile stats: {str(e)}")
