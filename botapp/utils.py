import os
from datetime import datetime, timedelta
from PIL import Image
import io
from google.cloud import storage

def validate_wallet_address(address):
    """Validate Ethereum wallet address format"""
    return address.startswith('0x') and len(address) == 42

def validate_image(image_bytes):
    """Validate image submission"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        return width >= 400 and height >= 400
    except:
        return False

def validate_audio(audio_bytes):
    """Validate audio submission"""
    # Add your audio validation logic
    return True

def upload_to_gcs(file_bytes, file_type, user_id):
    """Upload file to Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(os.getenv('GCS_BUCKET_NAME'))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{user_id}_{timestamp}.{file_type}"
    blob = bucket.blob(filename)
    
    blob.upload_from_string(file_bytes)
    return blob.public_url