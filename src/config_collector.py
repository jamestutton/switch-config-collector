#!/usr/bin/env python3

"""
A simple script to collect starting/running config and versions, put them into the file.
Store results in the file.

Files:
config_collector.py - main script
connect_to_device.py - includes functions: ping and connect SSH/Telnet to the device
devices.csv - list of IP addresses
devices-result.json - stores results of running script

(C) 2019 Dmitry Golovach
email: dmitry.golovach@outlook.com

"""

# Imports
import os
import time
import datetime
import sys
import ipaddress
import threading
import json
import pandas as pd

# Imports custom created modules
from rcn.network.discovery import Devices,Device
from starlette.config import Config


import logging

# Get an instance of a logger

logger = logging.getLogger(__name__)
config = Config()

# Module "Global" Variables
directory = '/configs_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
f = open('devices-result.csv', 'a', newline='')
sys.tracebacklimit = 0

# Module Functions and Classes

def main(device_data, current_index):
    # Initial call to print 0% progress
    device = Device(device_data, current_index)
    device.TestComms()
    return


# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()
    os.mkdir(os.getcwd() + directory)
    threads = []
    if len(sys.argv) == 2:
        try:
            if sys.argv[1] == "DB":
                i =0
                devs = Devices()
                
                while dev:= devs.next():
                    i += 1
                    if dev["Management IP"]:
                        thread = threading.Thread(target=main, args=(dev, i))
                        threads.append(thread)
                        thread.start()
                    if i % 10 == 32:
                        time.sleep(20)
                    
            else:
                ipaddress.ip_address(sys.ipargv[1])
                # pass only IP address of the device
                current_index = 0
                main(sys.argv[1], current_index)
        except ValueError:
            df = pd.read_csv(sys.argv[1])
            for current_index in df.index:
                thread = threading.Thread(target=main, args=(df['ip'][current_index], current_index))
                threads.append(thread)
                thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()


    else:
        raise SyntaxError("Insufficient arguments.")
    f.write('---'*10 + '\n')
    f.close()
    print(time.time() - start_time)
