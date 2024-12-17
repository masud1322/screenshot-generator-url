import subprocess
import os
import logging
from datetime import datetime
import requests
import base64
import time

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

IMGBB_API_KEY = os.getenv('IMGBB_API_KEY', 'YOUR_NEW_API_KEY')
FREEIMAGE_API_KEY = "6d207e02198a847aa98d0a2a901485a5"

def upload_to_imgbb(image_path, retry_count=3, delay=2):
    try:
        # Prepare the request
        url = "https://api.imgbb.com/1/upload"
        
        # Prepare multipart form data
        files = {
            'image': ('image.jpg', open(image_path, 'rb'), 'image/jpeg')
        }
        
        data = {
            'key': IMGBB_API_KEY
        }
        
        logger.info(f"Uploading {os.path.basename(image_path)} to ImgBB...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                logger.info(f"Successfully uploaded to ImgBB")
                return {
                    "url": result["data"]["url"],
                    "direct_url": result["data"]["display_url"],
                    "delete_url": result["data"]["delete_url"]
                }
                
        logger.error(f"ImgBB API error: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to upload to ImgBB: {str(e)}")
        return None

def upload_to_freeimage(image_path):
    """Upload to freeimage.host as fallback"""
    try:
        url = "https://freeimage.host/api/1/upload"
        
        # Prepare multipart form data
        files = {
            'source': ('image.jpg', open(image_path, 'rb'), 'image/jpeg')
        }
        
        data = {
            'key': FREEIMAGE_API_KEY,
            'action': 'upload',
            'format': 'json'
        }
        
        logger.info(f"Uploading {os.path.basename(image_path)} to freeimage.host...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status_code") == 200:
                logger.info(f"Successfully uploaded to freeimage.host")
                return {
                    "url": result["image"]["url"],
                    "direct_url": result["image"]["display_url"],
                    "delete_url": None  # freeimage doesn't provide delete URL
                }
                
        logger.error(f"Freeimage API error: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to upload to freeimage.host: {str(e)}")
        return None

def upload_to_imgbox(image_path):
    """Upload to imgbox.com as another fallback"""
    try:
        url = "https://imgbox.com/upload/process"
        
        # Prepare form data
        files = {
            'files[]': ('image.jpg', open(image_path, 'rb'), 'image/jpeg')
        }
        
        data = {
            'gallery_id': '',  # Empty for no gallery
            'gallery_title': '',
            'comments_enabled': '0',
            'adult_content': '0',
            'thumb_size': '350r'  # Regular thumbnail
        }
        
        # First make an init request
        init_response = requests.get("https://imgbox.com/upload/init")
        if init_response.status_code != 200:
            logger.error("Failed to initialize imgbox upload")
            return None
            
        # Get token from init response
        try:
            token = init_response.json().get('token')
            if not token:
                logger.error("No token in imgbox init response")
                return None
            data['token'] = token
        except:
            logger.error("Failed to parse imgbox init response")
            return None
            
        logger.info(f"Uploading {os.path.basename(image_path)} to imgbox.com...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                files = result.get('files', [])
                if files and len(files) > 0:
                    file_info = files[0]
                    return {
                        "url": file_info.get('original_url'),
                        "direct_url": file_info.get('original_url'),
                        "delete_url": None  # imgbox doesn't provide delete URL
                    }
                    
        logger.error(f"Imgbox API error: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to upload to imgbox: {str(e)}")
        return None

def capture_screenshots(video_url, num_screenshots=5, initial_delay=300, interval=180, filename_prefix="screenshot"):
    try:
        logger.info(f"Starting screenshot capture for video: {video_url}")
        logger.info(f"Settings: {num_screenshots} screenshots, {initial_delay}s delay, {interval}s interval")
        
        # Create screenshots directory
        os.makedirs('static/screenshots', exist_ok=True)
        logger.info("Created/verified screenshots directory")
        
        screenshots = []
        imgbb_links = []
        
        for i in range(int(num_screenshots)):
            try:
                # Calculate timestamp
                timestamp = int(initial_delay) + (i * int(interval))
                time_str = f"{int(timestamp/3600):02d}:{int((timestamp%3600)/60):02d}:{timestamp%60:02d}"
                logger.info(f"Processing screenshot {i+1}/{num_screenshots} at timestamp {time_str}")
                
                # Generate output filename
                filename = f'{filename_prefix}_{i}.jpg'
                filepath = os.path.join('static/screenshots', filename)
                
                # FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-ss', time_str,
                    '-i', video_url,
                    '-frames:v', '1',
                    '-q:v', '2',  # High quality
                    '-y',         # Overwrite output
                    filepath
                ]
                
                logger.info(f"Running FFmpeg for timestamp {time_str}")
                logger.debug(f"FFmpeg command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(filepath):
                    filesize = os.path.getsize(filepath)
                    logger.info(f"Screenshot saved: {filepath} ({filesize} bytes)")
                    
                    # Try ImgBB first
                    imgbb_result = upload_to_imgbb(filepath)
                    
                    # If ImgBB fails, try freeimage.host
                    if not imgbb_result:
                        logger.info("ImgBB upload failed, trying freeimage.host...")
                        imgbb_result = upload_to_freeimage(filepath)
                    
                    # If both fail, try imgbox
                    if not imgbb_result:
                        logger.info("Freeimage upload failed, trying imgbox.com...")
                        imgbb_result = upload_to_imgbox(filepath)
                    
                    if imgbb_result:
                        imgbb_links.append(imgbb_result)
                        logger.info(f"Uploaded to image host: {imgbb_result['direct_url']}")
                        
                        # Delete local file after successful upload
                        try:
                            os.remove(filepath)
                            logger.info(f"Deleted local file: {filepath}")
                        except Exception as e:
                            logger.error(f"Failed to delete local file {filepath}: {str(e)}")
                    else:
                        # Keep local file if all uploads failed
                        screenshots.append(filename)
                        logger.warning(f"Keeping local file due to failed uploads: {filepath}")
                else:
                    logger.error(f"FFmpeg failed for timestamp {time_str}")
                    logger.error(f"Error output: {result.stderr}")
                
            except Exception as e:
                logger.error(f"Error capturing screenshot {i+1}: {str(e)}")
                continue
        
        logger.info(f"Process completed. Captured {len(screenshots)} screenshots, Uploaded {len(imgbb_links)} to ImgBB")
        return {
            'local': screenshots,
            'imgbb': imgbb_links
        }
        
    except Exception as e:
        logger.error(f"Screenshot capture failed: {str(e)}")
        raise

# Clean up old screenshots on startup
def cleanup_screenshots():
    try:
        screenshot_dir = 'static/screenshots'
        if os.path.exists(screenshot_dir):
            for file in os.listdir(screenshot_dir):
                if file.endswith('.jpg'):
                    filepath = os.path.join(screenshot_dir, file)
                    try:
                        os.remove(filepath)
                        logger.info(f"Cleaned up old screenshot: {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {filepath}: {str(e)}")
    except Exception as e:
        logger.error(f"Screenshot cleanup failed: {str(e)}")