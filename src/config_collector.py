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
import re
import ipaddress
import threading
import json
import pandas as pd

# Imports custom created modules
import connect_to_device
from mongo import mongo_client
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

    @property
    def device_collection(self) -> Collection:
        return self._device_collection

    def put(self, device):
        """Place a job into the queue"""
        if channel is None:
            channel = self.channel
        try:
            self.device_collection.insert_one(device)
            return str(job["job_id"])
        except errors.DuplicateKeyError as e:
            logger.warning(e)
            return False

    def next(self):

        aggregate_result = list(
            self.queue_collection.aggregate(
                [
                    {
                        "$match": {
                            "locked_by": None,
                            "locked_at": None,
                            "completed_by": None,
                            "channel": self.channel,
                            "attempts": {"$lt": self.max_attempts},
                            "$or": [{"run_after": {"$exists": False}}, {"run_after": {"$lt": datetime.now()}}],
                        },
                    },
                    {"$sort": {"priority": pymongo.DESCENDING, "queued_at": pymongo.ASCENDING}},
                    {"$limit": 1},
                ],
            ),
        )
        if not aggregate_result:
            return None
        return self._wrap_one(
            self.queue_collection.find_one_and_update(
                filter={"_id": aggregate_result[0]["_id"], "locked_by": None, "locked_at": None},
                update={"$set": {"locked_by": self.consumer_id, "locked_at": datetime.now()}},
                sort=[("priority", pymongo.DESCENDING)],
                return_document=ReturnDocument.AFTER,
            ),
        )

    def Pending(self):
        return self.device_collection.find(
            #filter={"locked_by": None, "locked_at": None, "attempts": {"$lt": self.max_attempts}},
            filter={"Phase": "PHASE 2"}
            #sort=[("priority", pymongo.DESCENDING)],
        )

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
        return connect_to_device.ping_device(self.current_ip_address)

    def close_connection(self):
        self.connection.disconnect()

    @property
    def connection_type(self):
        if self.connection:
            return f"{self.connection.__class__}",
        else:
            return None

    def UpdateDB(self,result):
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {
                    "locked_by": None,
                    "locked_at": None,
                    "result": result,
                    "connection": self.connection_type,
                    "completed_at": datetime.datetime.now(),
                },
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



def main(current_ip_address, current_index):
    # Initial call to print 0% progress
    printProgressBar(0, 3, prefix='Progress: index ' + str(current_index), suffix='Complete', length=50)
    
    device = Device(current_ip_address, current_index)
    ping_result = device.init_ping()
    if not ping_result:
        device.version = ['N/A']
        device.collect_config_result = 'Ping Failed'
        suffix_bar = 'Failed'
        device.write_result(current_ip_address, device.version, device.collect_config_result, current_index, suffix_bar)
        device.UpdateDB("Ping Failed")
        return
    else:
        device.init_connection_ssh()
        if device.connection == 'Telnet':
            device.init_connection_telnet()
        if device.connection == 'autodetect':
            device.init_connection_auto()            
        if device.connection:
           #device.collect_config_ssh()
           device.close_connection()
           device.write_result(device.current_ip_address, device.version, device.collect_config_result,
                             device.current_index)
           device.UpdateDB("Working")
        else:
            Device.write_result(current_ip_address, ['N/A'], "Connection Failed", current_index, "Failed")
            device.UpdateDB("Connection Failed")

        
    return


# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()
    os.mkdir(os.getcwd() + directory)
    threads = []
    if len(sys.argv) == 2:
        try:
            if sys.argv[1] == "DB":
                devs = Devices().Pending()
                i =0
                for dev in devs:
                    i += 1
                    if dev["Management IP"]:
                        thread = threading.Thread(target=main, args=(dev["Management IP"], i))
                        threads.append(thread)
                        thread.start()
                        time.sleep(0.2)
            else:
                ipaddress.ip_address(sys.argv[1])
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
    json.dump(connect_to_device.method, f)
    f.close()
    print(time.time() - start_time)
