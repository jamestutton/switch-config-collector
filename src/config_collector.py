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
logger.setLevel(logging.INFO)
logger.info("Starting")



handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)



config = Config()


def TestDevice(device: Device):
    try:
        device.TestComms()
    except Exception as e:
        logger.exception(f"Exception Processing {device.ip}")
        logger.exception(e)
    


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
            if i % 32 == 0:
                time.sleep(20)
        logger.warning("All Devices Processed")
    except Exception as e:
        logger.exception(e)
        # Wait for all to complete
    for thread in threads:
        thread.join()
    print(time.time() - start_time)
