import requests
import os
import subprocess
import time
import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Load environment variables
load_dotenv()

# Log file path
log_file_path = '/home/pi/cloudflare-tunnel-monitor/cloudflare_monitor.log'

# Set up a specific logger with our desired output level
logger = logging.getLogger('CloudflareMonitor')
logger.setLevel(logging.INFO)

# Add the log message handler to the logger
handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Telegram Settings
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Notification Control
last_notification_time = datetime.min
notification_cooldown = timedelta(hours=1)
site_status = {}



def create_status_image(sites_status, internet_status):
    # Load the background image
    img = Image.open('background.webp')
    # Define dimensions for the image
    width, height = 250, 100 + len(sites_status) * 60
    # Ensure the image is the expected size (400x600); resize or crop if necessary
    #img = ImageOps.fit(img, (width, height), Image.ANTIALIAS)  # Not Working
    img = ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)
    # If you have a custom font, you can load it here. Otherwise, use the default font.
    font = ImageFont.load_default()

    # Define colors
    up_color = (0, 128, 0)  # Green color for UP status
    down_color = (255, 0, 0)  # Red color for DOWN status
    text_color = (0, 0, 0)  # Black color for text

    # Internet status at the top
    internet_text = "Internet: "
    internet_status_text = "UP" if internet_status else "DOWN"
    internet_color = up_color if internet_status else down_color
    # Draw the "Internet: " part
    draw.text((10, 10), internet_text, fill=text_color, font=font)
    # Calculate the size of "Internet: " text and draw the "UP" or "DOWN" part next to it
    internet_text_size = draw.textbbox((0, 0), internet_text, font=font)
    draw.text((10 + internet_text_size[2], 10), internet_status_text, fill=internet_color, font=font)

    # Draw each site status with "Up since" or "Down since" information
    y_offset = 40
    circle_radius = 5
    for site, info in sites_status.items():
        status_color = up_color if info['status'] else down_color

        # Draw status circle
        circle_x = 10
        circle_y = y_offset + 5
        draw.ellipse((circle_x, circle_y, circle_x + circle_radius * 2, circle_y + circle_radius * 2), fill=status_color)

        # Site status text
        y_offset += 5
        status_text_x = circle_x + circle_radius * 2 + 5
        draw.text((status_text_x, y_offset), site, fill=text_color, font=font)

        # "Up since" or "Down since" text
        since_text_y = y_offset + 20
        since_text = "Up since" if info['status'] else "Down since"
        since_time = info.get('last_up') if info['status'] else info.get('last_down')
        since_time_str = since_time.strftime('%Y-%m-%d %H:%M') if since_time else 'N/A'
        draw.text((50, since_text_y), f"{since_text}: {since_time_str}", fill=text_color, font=font)

        # "Last down" text, only if the site is up
        if info['status']:
            last_down_time = info.get('last_down')
            last_down_str = last_down_time.strftime('%Y-%m-%d %H:%M') if last_down_time else 'N/A'
            draw.text((50, since_text_y + 20), f"Last down: {last_down_str}", fill=text_color, font=font)

        y_offset += 60  # Increase the offset for the next site

    # Optionally, you can add a footer or title
    footer_text = "Generated on:   " + datetime.now().strftime('%Y-%m-%d %H:%M')
    draw.text((10, height - 20), footer_text, fill=text_color, font=font)

    # Save the image with texts overlayed on the background
    img_path = '/tmp/site_status_with_background.png'
    img.save(img_path)

    return img_path





def send_telegram_photo(photo_path):
    """Send a photo to a Telegram chat."""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
    data = {'chat_id': TELEGRAM_CHAT_ID}
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        response = requests.post(url, data=data, files=files)
        try:
            response.raise_for_status()  # This will raise an exception for HTTP errors
            logger.info(f"Photo sent successfully. Status code: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            # If you want to retry sending the message or handle the error in a specific way, add the code here



def send_telegram_message(message):
    """Send a text message to a Telegram chat."""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        logger.info(f"Message sent successfully to chat ID {TELEGRAM_CHAT_ID}. Response status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        # If you want to add a retry mechanism or other error handling, you can do so here.




def should_send_notification(site, current_status):
    global last_notification_time, site_status
    """Determine if a notification should be sent based on cooldown and status change."""
    now = datetime.now()
    # Check if the site's status has changed
    status_changed = (site not in site_status) or (site_status[site] != current_status)

    # Check if the cooldown period has passed since the last notification
    cooldown_passed = (now - last_notification_time >= notification_cooldown)

    if status_changed or cooldown_passed:
        site_status[site] = current_status  # Update the current status
        last_notification_time = now  # Update the last notification time
        return True
    return False




def is_site_up(url):
    try:
        response = requests.head(url, timeout=10)  # Added a timeout for safety
        if response.status_code == 200 or  response.status_code == 307:
            logger.info(f"Site up: {url}")
            return True
        else:
            logger.warning(f"Site down or unreachable: {url}. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return False



def is_internet_up():
    response = os.system("ping -c 1 8.8.8.8 > /dev/null 2>&1")
    if response == 0:
        logger.info("Internet is up.")
        return True
    else:
        logger.warning("Internet is down.")
        return False




def restart_docker_container(container_name):
    try:
        subprocess.check_call(['docker', 'restart', container_name])
        logger.info(f"Successfully restarted Docker container: {container_name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart Docker container: {container_name}. Error: {e}")






def check_and_restart(sites, container_name):
    global last_notification_time, site_status
    # Check internet status first
    internet_is_up = is_internet_up()

    if not internet_is_up:
        if should_send_notification('internet', False):
            try:
                img_path = create_status_image({}, False)
                send_telegram_photo(img_path)
            except Exception as e:
                send_telegram_message("Internet is DOWN. All sites are assumed to be DOWN as well.")
        return

    # Check sites status
    statuses_changed = False
    for site in sites:

        # Initialize the site status if it's not already in the dictionary
        if site not in site_status:
            site_status[site] = {'status': False, 'last_up': None, 'last_down': None}

        status = is_site_up(site)

        # Check for a status change
        if site_status[site]['status'] != status:
            statuses_changed = True
            site_status[site]['status'] = status

            # Record the time of the status change
            if status:  # Site is up
                site_status[site]['last_up'] = datetime.now()
            else:  # Site is down
                site_status[site]['last_down'] = datetime.now()

    # Send notification if required
    if statuses_changed or datetime.now() - last_notification_time >= notification_cooldown:
        last_notification_time = datetime.now()
        try:
            img_path = create_status_image(site_status, internet_is_up)
            send_telegram_photo(img_path)
        except Exception as e:
            logger.error(f"Failed to send status image. Error: {e}")
            message = "Status update:\n"
            message += f"Internet: {'UP' if internet_is_up else 'DOWN'}\n"
            for site, info in site_status.items():
                message += f"{site}: {'UP' if info['status'] else 'DOWN'}"
                if info['status']:
                    message += f" - UP since {info['last_up'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                else:
                    message += f" - DOWN since {info['last_down'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            send_telegram_message(message)

    # Restart Docker containers if needed
    for site, info in site_status.items():
        if not info['status']:
            restart_docker_container(container_name)







if __name__ == "__main__":
    SITES = ['http://os.deepakpandey.in', 'http://photos.deepakpandey.in']
    CONTAINER_NAME = 'cloudflared'
    CHECK_INTERVAL = 60  # seconds

    logger.info("Starting Cloudflare tunnel monitor script...")
    while True:
        check_and_restart(SITES, CONTAINER_NAME)
        time.sleep(CHECK_INTERVAL)
