import os
import aioboto3
from botocore.config import Config

# Support both AWS_S3_BUCKET (preferred) and legacy AWS_S3_BUCKET_NAME
S3_BUCKET = os.getenv('AWS_S3_BUCKET') or os.getenv('AWS_S3_BUCKET_NAME')

async def generate_presigned_upload(key: str, content_type: str, expires_in=3600):
    session = aioboto3.Session()
    # Prefer AWS_S3_REGION if provided; fall back to AWS_REGION, then us-east-1
    region = os.getenv('AWS_S3_REGION') or os.getenv('AWS_REGION', 'us-east-1')
    async with session.client('s3', region_name=region,
                              aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                              aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                              config=Config(signature_version='s3v4')) as client:
        url = await client.generate_presigned_url('put_object',
                                                 Params={'Bucket': S3_BUCKET, 'Key': key, 'ContentType': content_type},
                                                 ExpiresIn=expires_in)
        return url

async def generate_presigned_get(key: str, expires_in: int = 1800):
    """Generate a presigned GET URL for reading an object (default 30 min)."""
    session = aioboto3.Session()
    region = os.getenv('AWS_S3_REGION') or os.getenv('AWS_REGION', 'us-east-1')
    async with session.client('s3', region_name=region,
                              aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                              aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                              config=Config(signature_version='s3v4')) as client:
        url = await client.generate_presigned_url('get_object',
                                                 Params={'Bucket': S3_BUCKET, 'Key': key},
                                                 ExpiresIn=expires_in)
        return url

async def delete_object(key: str) -> bool:
    session = aioboto3.Session()
    region = os.getenv('AWS_S3_REGION') or os.getenv('AWS_REGION', 'us-east-1')
    try:
        async with session.client('s3', region_name=region,
                                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                                  config=Config(signature_version='s3v4')) as client:
            await client.delete_object(Bucket=S3_BUCKET, Key=key)
            return True
    except Exception:
        return False
