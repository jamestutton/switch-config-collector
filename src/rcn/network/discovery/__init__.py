# Imports
import os
import time
import datetime
import sys
import re
import ipaddress
import threading
import json
import pandas as pd

# Imports custom created modules
import rcn.network.discovery.connect_to_device as connect_to_device
from rcn.mongo import mongo_client
from starlette.config import Config

import pymongo
import logging
from pymongo import DeleteOne
from pymongo import errors
from pymongo import ReturnDocument
from pymongo import UpdateOne
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

# Get an instance of a logger

logger = logging.getLogger(__name__)
config = Config()

# Module "Global" Variables
directory = '/configs_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
f = open('devices-result.csv', 'a', newline='')
sys.tracebacklimit = 0

# Module Functions and Classes
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Print iterations progress
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s \n' % (prefix, bar, percent, suffix), end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


DEFAULT_INSERT: dict = {
    "attempts": 0,
    "locked_by": None,
    "completed_by": None,
    "completed_at": None,
    "result": None,
    "locked_at": None,
    "last_error": None,
}

class Devices:
    def __init__(self):
        config = Config()
        _MONGODB_NAME = config("MONGODB_NAME", cast=str)
        self._MONGODB = mongo_client[f"{_MONGODB_NAME}"]
        self.collect_config_result = 'UNKOWN'
        self._device_collection = getattr(self._MONGODB, "network")
        self.max_attempts = 1
        
        self._batch_size = config("BATCH_SIZE", cast=int,default=100)

    @property
    def device_collection(self) -> Collection:
        return self._device_collection


    def Pending(self):
        return self.device_collection.find(
            filter={"Phase": "PHASE 2","locked_by": None, "locked_at": None, "attempts": {"$lt": self.max_attempts}},
        ).limit(self._batch_size)

    def Working(self):
        return self.device_collection.find(
            filter={"Phase": "PHASE 2", "result": "Working"} 
        ).limit(self._batch_size)

    def PingFailed(self):
        return self.device_collection.find(
            filter={"Phase": "PHASE 2","result": "Ping Failed"} 
        ).limit(self._batch_size)
        
    def ConnectionFailed(self):
        return self.device_collection.find(
            filter={"Phase": "PHASE 2","result": "Connection Failed"} 
        ).limit(self._batch_size)

class Device:
    """Creating the class with:

        self.current_ip_address - IP address
        self.current_index - index from devices.csv
        self.version - grep version from the 'show version'command
        self.collect_config_result - result of running config_collection.py sctipt

        Methods:
            def collect_config - main method to collect running/startup config and version
            def init_connection - initiate SSH connection to the device
            def close_connection - close SSH connection to the device
            def write_result - put results in to the devices-result.json file
    """

    def __init__(self, current_ip_address, current_index):
        self.current_ip_address = current_ip_address
        self.current_index = current_index
        config = Config()
        _MONGODB_NAME = config("MONGODB_NAME", cast=str)
        
        self._MONGODB = mongo_client[f"{_MONGODB_NAME}"]
        self._device_collection = getattr(self._MONGODB, "network")
        
        

        self.collect_config_result = "NOT COLLECTED"
        self.version = ["N/A"]
        self.connection = None
        self.pingable = None
        
        

    @property
    def device_collection(self) -> Collection:
        return self._device_collection

    def collect_config_ssh(self):
        self.connection.send_command("term len 0")
        startup_config = self.connection.send_command("show startup-config")
        hostname = re.findall('hostname (.*)\n', startup_config)
        show_ver = self.connection.send_command('show version')
        # self.version = re.findall('.* "(.*bin)"\n', show_ver)
        self.version = re.findall('.*"(.*)"\n', show_ver)
        ver_and_config = show_ver + '\n\n\n========== STARTUP CONFIG ==========\n\n\n' + startup_config
        device_path = os.getcwd() + directory + "/" + hostname[0] + '_version_startup-config_' \
                      + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + ".txt"
        with open(device_path, "w+") as f:
            f.write(ver_and_config)

        self.collect_config_result = "OK"
        printProgressBar(2, 3, prefix='Progress: index ' + str(self.current_index), suffix='Complete', length=50)
        return

    def init_connection_ssh(self):
        self.connection = connect_to_device.try_to_connect_ssh(self.current_ip_address)

    def init_connection_telnet(self):
        self.connection = connect_to_device.try_to_connect_telnet(self.current_ip_address)

    def init_connection_auto(self):
        self.connection = connect_to_device.try_to_connect_auto(self.current_ip_address)        

    def init_ping(self):

        self.pingable = connect_to_device.ping_device(self.current_ip_address)
        return self.pingable
        

    def close_connection(self):
        self.connection.disconnect()

    @property
    def connection_type(self):
        if self.connection:
            return f"{self.connection.__class__}"
        else:
            return None

    def HitsTacacs(self):
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {
                    "HitsTacacs": True,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    def UpdateDB(self,result):
        device_data = {
                    "locked_by": None,
                    "locked_at": None,
                    "result": result,
                    "connection": self.connection_type,
                    "completed_at": datetime.datetime.now(),
        }
        if self.pingable:
            device_data["pingable"]= self.pingable
        elif result == "Working":
            device_data["pingable"]="Skipped"

        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": device_data,
                "$inc": {"attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )



    @staticmethod
    def write_result(current_ip_address, version, collect_config_result, current_index, suffix_bar='Complete'):
        dict_result = {
            'ip': current_ip_address,
            'version': version[0],
            'result': collect_config_result,
            'comment': 'Comment OK - ' + str(current_index),
        }
        df_result = pd.DataFrame(dict_result, [current_index])
        df_result.to_csv(f, mode='a', index=False, header=f.tell() == 0)
        printProgressBar(3, 3, prefix='Progress: index ' + str(current_index), suffix=suffix_bar, length=50)
        return


