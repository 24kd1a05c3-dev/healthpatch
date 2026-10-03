import asyncio
import aiohttp
import argparse
import random
import sys
import threading
from datetime import datetime, timezone
import json

try:
    import msvcrt
    has_msvcrt = True
except ImportError:
    has_msvcrt = False
    import select

class Simulator:
    def __init__(self, device_id, email, password, url, interval):
        self.device_id = device_id
        self.email = email
        self.password = password
        self.url = url
        self.interval = interval
        self.mode = "n"
        self.battery = 100.0
        self.running = True
        self.token = None
        self.user_id = None
        
    async def login(self, session):
        print(f"Logging in as {self.email}...")
        async with session.post(f"{self.url}/auth/login", json={"email": self.email, "password": self.password}) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.token = data["access_token"]
                self.user_id = data["user"]["id"]
                print("Login successful.")
                return True
            else:
                print(f"Login failed: {await resp.text()}")
                return False

    def get_readings(self):
        hr_base = 72
        spo2_base = 98
        temp_base = 36.6
        
        if self.mode == "t" or self.mode == "a":
            hr_base = 135
        if self.mode == "h" or self.mode == "a":
            spo2_base = 88
        if self.mode == "f" or self.mode == "a":
            temp_base = 38.8
            
        hr = hr_base + random.uniform(-3, 3)
        spo2 = min(100, max(0, spo2_base + random.uniform(-1, 1)))
        temp = temp_base + random.uniform(-0.2, 0.2)
        
        self.battery = max(0.0, self.battery - 0.1)
        signal = random.uniform(0.85, 0.99)
        if random.random() < 0.05:
            signal = random.uniform(0.3, 0.7)
            
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": round(hr, 1),
            "spo2": round(spo2, 1),
            "temperature": round(temp, 1),
            "battery": round(self.battery, 1),
            "signal_quality": round(signal, 2),
            "activity": "RESTING"
        }

    async def run(self):
        async with aiohttp.ClientSession() as session:
            if not await self.login(session):
                return
                
            headers = {"Authorization": f"Bearer {self.token}"}
            
            while self.running:
                data = self.get_readings()
                try:
                    async with session.post(f"{self.url}/health-data/", json=data, headers=headers) as resp:
                        if resp.status == 200:
                            print(f"Sent: HR={data['heart_rate']} SpO2={data['spo2']} Temp={data['temperature']} Batt={data['battery']}")
                        else:
                            print(f"Failed to send: {await resp.text()}")
                except Exception as e:
                    print(f"Error sending data: {e}")
                    
                await asyncio.sleep(self.interval)

def keyboard_listener(sim):
    print("Press 't' for tachycardia, 'h' for hypoxemia, 'f' for fever, 'a' for all, 'n' for normal, 'q' to quit")
    while sim.running:
        key = None
        if has_msvcrt:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
        else:
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                key = sys.stdin.read(1).lower()
                
        if key:
            if key == 'q':
                sim.running = False
            elif key in ['t', 'h', 'f', 'a', 'n']:
                sim.mode = key
                print(f"\\nMode changed to: {key}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", default="SHP-ESP32-0001")
    parser.add_argument("--email", default="patient@healthpatch.io")
    parser.add_argument("--password", default="demo123")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    
    sim = Simulator(args.device_id, args.email, args.password, args.url, args.interval)
    
    t = threading.Thread(target=keyboard_listener, args=(sim,))
    t.daemon = True
    t.start()
    
    await sim.run()

if __name__ == "__main__":
    asyncio.run(main())
