#!/bin/bash

echo "🔧 เริ่มติดตั้งระบบ RFID Reader..."

# === Step 1: อัปเดตและติดตั้ง Python venv ===
sudo apt update
sudo apt install python3-venv -y

# === Step 2: เตรียม path project ===
PROJECT_DIR=~/python/RFID
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# === Step 3: สร้าง virtual environment ===
python3 -m venv venv
source venv/bin/activate

# === Step 4: ติดตั้ง dependencies ใน virtualenv ===
pip install --upgrade pip
pip install pyserial aiohttp

# === Step 5: เตรียม log directory ===
sudo mkdir -p /var/log/rfid
sudo chown $USER:$USER /var/log/rfid

# === Step 6: สร้างไฟล์ Systemd Service ===
SERVICE_FILE=/etc/systemd/system/rfid-reader.service

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=RFID Reader Async Service
After=network.target

[Service]
ExecStart=~/python/RFID/venv/bin/python ~/python/RFID/rfid_reader_asyncio_log_dedup.py
WorkingDirectory=~/python/RFID
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# === Step 7: Reload systemd และ enable service ===
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable rfid-reader.service

echo "✅ ติดตั้งเสร็จสมบูรณ์! รันด้วย: sudo systemctl start rfid-reader.service"
