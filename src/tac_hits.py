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
import sys
import json
import pandas as pd

from starlette.config import Config
from rcn.network.discovery import Devices,Device,printProgressBar

import logging


# Get an instance of a logger

logger = logging.getLogger(__name__)
config = Config()




# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()
    
    if len(sys.argv) == 2:
        df = pd.read_csv(sys.argv[1])
        for current_index in df.index:
            device = Device(df['ip'][current_index], current_index)
            device.HitsTacacs()
    else:
        raise SyntaxError("Insufficient arguments.")
    
    print(time.time() - start_time)
