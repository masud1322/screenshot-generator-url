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

IMGBB_API_KEY = "b9f27299015facaa09f0393078dc644b"

def upload_to_imgbb(image_path, retry_count=3, delay=2):
    try:
        with open(image_path, "rb") as file:
            # Read image file and encode to base64
            image_data = base64.b64encode(file.read()).decode('utf-8')
            
            # Prepare the request
            url = "https://api.imgbb.com/1/upload"
            data = {
                "key": IMGBB_API_KEY,
                "image": image_data,
            }
            
            # Set proper headers
            headers = {
                "Accept": "application/json",
            }
            
            logger.info(f"Uploading {os.path.basename(image_path)} to ImgBB...")
            response = requests.post(url, data=data, headers=headers)
            
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
                    
                    # Upload to ImgBB
                    imgbb_result = upload_to_imgbb(filepath)
                    if imgbb_result:
                        imgbb_links.append(imgbb_result)
                        logger.info(f"Uploaded to ImgBB: {imgbb_result['direct_url']}")
                        
                        # Delete local file after successful upload
                        try:
                            os.remove(filepath)
                            logger.info(f"Deleted local file: {filepath}")
                        except Exception as e:
                            logger.error(f"Failed to delete local file {filepath}: {str(e)}")
                    else:
                        # Keep local file if upload failed
                        screenshots.append(filename)
                        logger.warning(f"Keeping local file due to failed upload: {filepath}")
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