import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from video_screenshot import capture_screenshots, cleanup_screenshots
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure screenshots directory exists
os.makedirs('static/screenshots', exist_ok=True)

# Clean up screenshots at startup
cleanup_screenshots()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    try:
        video_url = request.form.get('video_url')
        initial_delay = request.form.get('initial_delay', 300)  
        interval = request.form.get('interval', 180)            
        num_screenshots = request.form.get('num_screenshots', 5)
        filename_prefix = request.form.get('filename_prefix', f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        logger.info(f"Processing video URL: {video_url}")
        logger.info(f"Settings: delay={initial_delay}s, interval={interval}s, count={num_screenshots}")
        
        result = capture_screenshots(
            video_url, 
            num_screenshots=num_screenshots,
            initial_delay=initial_delay,
            interval=interval,
            filename_prefix=filename_prefix
        )
        
        screenshot_urls = [f'/static/screenshots/{s}' for s in result['local']]
        return jsonify({
            'status': 'success', 
            'screenshots': screenshot_urls,
            'imgbb': result['imgbb']
        })
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 