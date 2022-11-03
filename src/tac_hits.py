#!/usr/bin/env python3
# Imports
import logging
import sys
import time

import pandas as pd
from rcn.network.discovery import Device
from starlette.config import Config


# Get an instance of a logger

logger = logging.getLogger(__name__)
config = Config()


# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()

    if len(sys.argv) == 2:
        df = pd.read_csv(sys.argv[1])
        for current_index in df.index:
            device = Device(df["ip"][current_index], current_index)
            device.HitsTacacs()
    else:
        raise SyntaxError("Insufficient arguments.")

    print(time.time() - start_time)
