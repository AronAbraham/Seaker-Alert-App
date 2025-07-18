import psutil
import time
import yaml
import smtplib
from email.mime.text import MIMEText
from prometheus_client import start_http_server, Gauge
import asyncio
import platform

# Prometheus metrics
cpu_usage = Gauge('system_cpu_usage', 'CPU usage percentage')
ram_used = Gauge('system_ram_used', 'Used RAM in GB')
ram_total = Gauge('system_ram_total', 'Total RAM in GB')
disk_used = Gauge('system_disk_used', 'Used disk space in GB')
disk_total = Gauge('system_disk_total', 'Total disk space in GB')
uptime_hours = Gauge('system_uptime_hours', 'System uptime in hours')
temperature_celsius = Gauge('system_temperature_celsius', 'CPU temperature in Celsius')

# Load configuration
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
thresholds = config['thresholds']
email_config = config['email']

def get_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            return temps['coretemp'][0].current
        return None
    except:
        return None

async def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_config['sender_email']
    msg['To'] = email_config['recipient_email']

    try:
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

async def monitor():
    while True:
        # Collect metrics
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime = time.time() - psutil.boot_time()
        
        # Update Prometheus metrics
        cpu_usage.set(cpu)
        ram_used.set(ram.used / 1_000_000_000)
        ram_total.set(ram.total / 1_000_000_000)
        disk_used.set(disk.used / 1_000_000_000)
        disk_total.set(disk.total / 1_000_000_000)
        uptime_hours.set(uptime / 3600)
        
        temp = get_temperature()
        if temp:
            temperature_celsius.set(temp)
        
        # Check thresholds and send alerts
        alerts = []
        if cpu > thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {cpu}%")
        if (ram.used / ram.total * 100) > thresholds['ram_used_percent']:
            alerts.append(f"High RAM usage: {(ram.used / 1_000_000_000):.2f}GB")
        if (disk.used / disk.total * 100) > thresholds['disk_used_percent']:
            alerts.append(f"Low disk space: {(disk.free / 1_000_000_000):.2f}GB free")
        if temp and temp > thresholds['temperature_celsius']:
            alerts.append(f"High temperature: {temp}°C")
        
        # Print and email alerts
        for alert in alerts:
            print(alert)
            await send_email("Seaker-Alert-App Notification", alert)
        
        await asyncio.sleep(10)  # Check every 10 seconds

async def main():
    start_http_server(8000)  # Start Prometheus metrics server
    await monitor()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())