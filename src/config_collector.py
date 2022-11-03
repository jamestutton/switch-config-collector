#!/usr/bin/env python3
# Imports
import datetime
import logging
import os
import sys
import threading
import time

from rcn.network.discovery import Devices
from rcn.network.discovery import Device
from starlette.config import Config

# Imports custom created modules

# Get an instance of a logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
config = Config()


def TestDevice(device: Device):
    device.TestComms()
    


# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()
    threads = []
    try:
        i = 0
        devs = Devices()

        while dev := devs.next():
            i += 1
            if dev.current_ip_address:
                dev.current_index = i
                thread = threading.Thread(target=TestDevice, args=(dev,))
                threads.append(thread)
                thread.start()
            if i % 10 == 32:
                time.sleep(20)
        
    except Exception as e:
        logger.exception(e)
        # Wait for all to complete
    for thread in threads:
        thread.join()
    print(time.time() - start_time)
