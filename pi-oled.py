#!/usr/bin/env python3

from board import SCL, SDA 
import busio
import adafruit_ssd1306

from PIL import Image, ImageDraw
import socket, psutil, subprocess
import signal, sys, math, time, argparse

from collections import deque

# OLED pixel size
WIDTH  = 128
HEIGHT = 64

# OLED initialize
i2c = busio.I2C(SCL, SDA)
display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3c)
display.fill(0)
display.show()

def oled_cleanup(signal, frame):
    print("Received signal {}, exiting...".format(signal), file=sys.stderr)
    display.fill(0)
    display.show()
    sys.exit(0)

def convert_uptime(t):
    day = math.floor(t / (3600 * 24))
    t -= (day * 3600 * 24)
    hour = math.floor(t / 3600)
    t -= hour * 3600 
    min = math.floor(t / 60) 
    t -= min * 60
    sec = math.floor(t)
    days = 'days' if day > 1 else 'day'
    return day,days, hour,min,sec

def get_uptime():
    with open("/proc/uptime") as f:
        return float(f.read().split()[0])

def get_cpu_freq():
    with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
        return float(f.read()) / 1000000

def get_cpu_usage():
    return psutil.cpu_percent()        

def get_cpu_temp():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return float(f.read()) / 1000.0

def get_ip_address_old():
    ret = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE).stdout
    return  ret.decode().split()

def get_ip_address(dev):
    dev_info = psutil.net_if_addrs()[dev]
    for addr in dev_info:
        if addr.family == socket.AF_INET:
            return addr.address
    return '0.0.0.0'

def cpu_load_meter(n:float, len: int=10):
    fill = int(len * n)
    bar = ('█' * fill) + ('-') * (len - fill)
    return str(bar + '| {}%'.format(n * 100))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--interface',
        type = str,
        default = 'eth0',
        help = 'target network interface to display'
    )
    args = parser.parse_args()
    target_nic = args.interface
    
    image = Image.new('1', (WIDTH, HEIGHT))
    draw  = ImageDraw.Draw(image)
    buf = deque([0]*WIDTH, maxlen=WIDTH)

    signal.signal(signal.SIGTERM, oled_cleanup)
    signal.signal(signal.SIGINT, oled_cleanup)

    try:
        while True:
            cpu_f = get_cpu_freq()
            cpu_t = get_cpu_temp()
            load  = get_cpu_usage()

            draw.rectangle((0, 0, WIDTH, HEIGHT), outline=0, fill=0)

            #draw.text((0, 0), "IPv4: {}".format(get_ip_address(target_nic)), fill=255)
            draw.text((0, 0), "{}: {}".format(target_nic, get_ip_address(target_nic)), fill=255)
            draw.text((0, 14), "Uptime: {} {} {:0>2}:{:0>2}:{:0>2}".format(*convert_uptime(float(get_uptime()))), fill=255)
            draw.text((0, 24), "CPU {:.2f}GHz {:.1f}C".format(cpu_f, cpu_t), fill=255)
            draw.text((0, 34), "CPU Usage {:0>2.1f}%".format(load), fill=255)

            buf.append(load)
            for i in range(WIDTH):
                draw.line((i, 63 - math.ceil(buf[i]/5), i, 63), fill=255, width=1)

            display.image(image)
            display.show()
            time.sleep(0.5)

    except Exception as e:
            oled_cleanup(None, None)

if __name__ == "__main__":
    main()
