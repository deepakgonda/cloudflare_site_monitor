### To install python and create virtual environment:
```
sudo apt update
sudo apt install python3-venv python3-full -y
```

Then navigate to you directory where you have cloned this Repo (~/cloudflare_site_monitor):
```
python3 -m venv venv
source venv/bin/activate
```

### Now install all requirements
```
pip install -r requirement.txt
```

### Give correct permissions to script file
```
chmod +x /home/pi/cloudflare_site_monitor/script.py
```


### To Create Telegram Bot:
Create a Bot: Talk to @BotFather on Telegram to create a new bot. Follow the instructions to get a token.
Get Your Chat ID: Start a conversation with your new bot or add it to a group. Use a tool like https://api.telegram.org/bot<YourBOTToken>/getUpdates to find your chat ID.

Make Sure you put your BotToken and chat id in env file.
To create env file
```
sudo nano /home/pi/cloudflare_site_monitor/.env
```

And put following text:
```
TELEGRAM_TOKEN='your_bot_token'
TELEGRAM_CHAT_ID='your_chat_id'
```


### After this Create Systemd Service File
Open a new service file in the /etc/systemd/system/ directory. You can name it something like cloudflare_monitor.service. Use sudo and your preferred text editor, for example:
```
sudo nano /etc/systemd/system/cloudflare_monitor.service
```
Add the following contents to the file. 
Ensure you replace /home/pi/cloudflare_site_monitor with the actual path to your script if it's different, and adjust the User= line if necessary (if you're not using the pi user):
```
[Unit]
Description=Cloudflare Tunnel Monitor and Restarter
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/cloudflare_site_monitor
ExecStart=/home/pi/cloudflare_site_monitor/venv/bin/python3 /home/pi/cloudflare_site_monitor/script.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Enable and Start the Service
Reload systemd to make it aware of your new service:
```
sudo systemctl daemon-reload
```

Enable the service so it starts automatically at boot:
```
sudo systemctl enable cloudflare_monitor
```

Start the service now without rebooting:
```
sudo systemctl start cloudflare_monitor
```

Check the status of your service to ensure it's active and running:
```
sudo systemctl status cloudflare_monitor
```


### If serive is dead, or not started:
Check the Service's Journal:
```
sudo journalctl -u cloudflare_monitor.service
```

Ensure Correct File Permissions:
```
chmod +x /home/pi/cloudflare_site_monitor/script.py
```

Validate Script Execution Manually:
/home/pi/cloudflare_site_monitor/venv/bin/python3 /home/pi/cloudflare_site_monitor/script.py

Ensure Docker Command Can Be Run:
Since your script restarts a Docker container, ensure that the pi user can execute Docker commands. Running Docker commands typically requires sudo, or the user needs to be in the docker group. If your script works when manually executed but fails when run as a service, this permissions issue could be the cause.

To add the pi user to the docker group (if not already added):
```
sudo usermod -aG docker pi
```


### Some helpful Commands
To restart service anytime:
```
sudo systemctl restart cloudflare_monitor
```

To check service status:
```
sudo systemctl status cloudflare_monitor
```

To monitor service logs:
```
tail -f /home/pi/cloudflare_site_monitor/cloudflare_monitor.log
```
