#!/bin/bash

set -e

echo "📦 อัปเดตแพ็กเกจ..."
sudo apt update

echo "🐍 ติดตั้ง python3-venv หากยังไม่มี..."
sudo apt install -y python3-venv

echo "📁 สร้าง virtual environment หากยังไม่มี..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ สร้าง venv แล้ว"
else
    echo "ℹ️ พบ venv อยู่แล้ว ข้ามการสร้าง"
fi

echo "🔗 เพิ่ม auto activate ใน ~/.bashrc หากยังไม่มี..."
ACTIVATE_LINE="source $(pwd)/venv/bin/activate"
if ! grep -Fxq "$ACTIVATE_LINE" ~/.bashrc; then
    echo "$ACTIVATE_LINE" >> ~/.bashrc
    echo "✅ เพิ่มบรรทัด activate แล้ว"
else
    echo "ℹ️ มีบรรทัด activate อยู่แล้ว"
fi

echo "📁 สร้าง log directory หากยังไม่มี..."
sudo mkdir -p /var/log/rfid
sudo chown "$USER":"$USER" /var/log/rfid

echo "⚙️ ติดตั้ง systemd service หากยังไม่มี..."
SERVICE_FILE="/etc/systemd/system/rfid-reader.service"
if [ ! -f "$SERVICE_FILE" ]; then
    sudo cp rfid-reader.service "$SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl enable rfid-reader.service
    echo "✅ ติดตั้ง service แล้ว"
else
    echo "ℹ️ พบ service อยู่แล้ว ข้ามการติดตั้ง"
fi

echo "✅ ติดตั้งเสร็จสมบูรณ์!"
echo "💡 เริ่มใช้งานด้วย: sudo systemctl start rfid-reader.service"
