
import asyncio
import aiohttp
import serial
import struct
import time
import socket
import uuid
import logging
from logging.handlers import TimedRotatingFileHandler
from collections import defaultdict

# ====== CONFIG ======
API_URL = "https://your-api.com/rfid"
JWT_TOKEN = "your_jwt_token_here"
DUPLICATE_TIMEOUT = 10  # วินาที

# ====== Logging Setup (แยก log รายวัน และลบเก่า) ======
logger = logging.getLogger("RFIDLogger")
logger.setLevel(logging.INFO)

log_path = "/var/log/rfid/rfid_reader.log"
handler = TimedRotatingFileHandler(log_path, when="midnight", backupCount=7)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ====== Utility ======
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "0.0.0.0"
    finally:
        s.close()
    return ip

def get_mac_address():
    mac = uuid.getnode()
    return '-'.join(f'{(mac >> i) & 0xff:02X}' for i in reversed(range(0, 48, 8)))

DEVICE_IP = get_ip()
DEVICE_MAC = get_mac_address()

# ====== Serial Init ======
ser = serial.Serial(port='/dev/ttyUSB0', baudrate=115200, timeout=1)
ser.flushInput()
ser.write(b'\x04\x00\x01\xDB\x4B')  # Start read command for CF661

# ====== Deduplication Map ======
last_sent_time = defaultdict(float)

# ====== Extract EPC + RSSI ======
def extract_epc_rssi_multi(hex_data):
    results = []
    pos = 0
    while True:
        idx = hex_data.find("E280", pos)
        if idx == -1 or idx + 24 > len(hex_data):
            break
        epc = hex_data[idx:idx + 24]
        rssi_pos = idx + 24
        if rssi_pos + 2 <= len(hex_data):
            rssi_hex = hex_data[rssi_pos:rssi_pos + 2]
            rssi_dbm = struct.unpack('b', bytes.fromhex(rssi_hex))[0]
        else:
            rssi_dbm = None
        results.append((epc, rssi_dbm))
        pos = rssi_pos + 2
    return results

# ====== Async Sender with Retry ======
async def send_to_api(session, epc, rssi, max_retries=3, retry_delay=2):
    now = time.time()
    if now - last_sent_time[epc] < DUPLICATE_TIMEOUT:
        return
    last_sent_time[epc] = now

    payload = {
        "epc": epc,
        "rssi": rssi,
        "ipaddress": DEVICE_IP,
        "macaddress": DEVICE_MAC
    }
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }

    for attempt in range(1, max_retries + 1):
        try:
            async with session.post(API_URL, json=payload, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    logger.info(f"✅ SENT: {epc} | RSSI: {rssi} dBm")
                    return
                else:
                    text = await resp.text()
                    logger.error(f"❌ Attempt {attempt} - {resp.status}: {epc} | {text}")
        except Exception as e:
            logger.error(f"❌ Attempt {attempt} - Exception for {epc}: {e}")

        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    logger.warning(f"⚠️ FAILED to send after {max_retries} attempts: {epc}")

# ====== Main Async Loop ======
async def main():
    logger.info("📡 เริ่มอ่าน RFID + Async + Logging + Deduplication + Retry")
    logger.info(f"IP: {DEVICE_IP} | MAC: {DEVICE_MAC}")

    async with aiohttp.ClientSession() as session:
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                hex_data = data.hex().upper()
                epc_rssi_list = extract_epc_rssi_multi(hex_data)

                tasks = [
                    send_to_api(session, epc, rssi)
                    for epc, rssi in epc_rssi_list
                ]
                if tasks:
                    await asyncio.gather(*tasks)
            await asyncio.sleep(0.1)

# ====== Run ======
try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("📴 หยุดการอ่าน RFID")
finally:
    ser.close()
    logger.info("🔌 ปิดพอร์ต Serial แล้ว")
