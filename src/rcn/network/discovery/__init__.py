# Imports
import os
# import time
import datetime
import sys
import re
# import ipaddress
# import threading
# import json
import pandas as pd
import subprocess
import random
# Imports custom created modules
from rcn.mongo import mongo_client
from starlette.config import Config


import logging
# from pymongo import DeleteOne
# from pymongo import errors
from pymongo import ReturnDocument
# from pymongo import UpdateOne
from pymongo.collection import Collection
# from pymongo.errors import BulkWriteError

import platform
import paramiko
import netmiko
import subprocess
import sys

from local_settings import credentials
# from paramiko import SSHException

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
        
        self._batch_size = config("BATCH_SIZE", cast=int,default=32)

        

    @property
    def device_collection(self) -> Collection:
        return self._device_collection

    def next(self):

        aggregate_result = list(
            self.device_collection.aggregate(
                [
                    {
                        "$match": {
                            "Phase": "PHASE 2",
                            "locked_by": None, 
                            "locked_at": None, 
                            "attempts": {"$lt": self.max_attempts},
                            "$or": [{"next_poll": {"$exists": False}}, {"next_poll": {"$lt": datetime.now()}}],
                        },
                    },
                    {"$limit": 1},
                ],
            ),
        )
        if not aggregate_result:
            return None
        return self._wrap_one(
            self.queue_collection.find_one_and_update(
                filter={"_id": aggregate_result[0]["_id"], "locked_by": None, "locked_at": None},
                update={"$set": {"locked_at": datetime.now()}},
                return_document=ReturnDocument.AFTER,
            ),
        )



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
        
        #netmiko device types to test in order
        self.device_types = [
            'cisco_ios_ssh',
            'cisco_ios_telnet',
            'autodetect'
        ]

        self.device_type = "UNKNOWN"
        self.collect_config_result = "NOT COLLECTED"
        self.version = ["N/A"]
        self.connection = None
        self.pingable = None
        self.prompt = None
        self.enable = None
        self.error = None
        

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

    @property
    def connected(self) -> bool:
        if self.connection:
            return True
        else:
            return False

    def init_connection(self):
        for device_type in self.device_types:
            for cred in credentials(self.current_ip_address).list:
                try:
                    self.connection = netmiko.ConnectHandler(device_type=device_type,
                                                        ip=self.current_ip_address,
                                                        username=cred.username,
                                                        password=cred.password,
                                                        secret=cred.secret
                                                        )
                    self.device_type = device_type
                    self.prompt = True
                    self.connection.enable()
                    self.enable = True
                    return 
                except paramiko.AuthenticationException as e:
                    self.error = f"{e}"
                    continue
                except netmiko.exceptions.NetmikoTimeoutException as e:
                    self.error = f"{e}"
                    continue
                except paramiko.ssh_exception.SSHException as e:
                    self.error = f"{e}"
                    continue
                except Exception as e:
                    self.error = f"{e}"
                    logger.exception(e)

   

    def init_ping(self):
        try:
            output = subprocess.check_output("ping -{} 1 {}".format('n' if platform.system().lower(
            ) == "windows" else 'c', self.current_ip_address), shell=True, universal_newlines=True)
            if 'unreachable' in output:
                self.pingable =  False
            else:
                self.pingable =  True
        except Exception as e:
            #logger.exception(e)
            self.pingable =  False

        return self.pingable
        

    def close_connection(self):
        self.connection.disconnect()

    @property
    def connection_type(self):
        if self.connected:
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

    def Processing(self):
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {
                    "locked_by": self.current_index,
                    "locked_at": datetime.datetime.now(),
                    "started_at": datetime.datetime.now(),
                    "next_poll": datetime.datetime.now() +  datetime.timedelta(hours=3) +  datetime.timedelta(minutes=random.randint(1,40))
                },
                "$inc": {"attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    def UpdateDB(self,result):
        device_data = {
                    "locked_by": None,
                    "locked_at": None,
                    "result": result,
                    "device_type": self.device_type,
                    "enable": self.enable,
                    "prompt": self.prompt,
                    "last_error": self.error,
                    "device_type": self.device_type,
                    "completed_at": datetime.datetime.now(),
                    "next_poll": datetime.datetime.now() +  datetime.timedelta(hours=3) +  datetime.timedelta(minutes=random.randint(1,40))
        }
        if self.pingable:
            device_data["pingable"]= self.pingable
        elif result == "Working":
            device_data["pingable"]="Skipped"

        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": device_data,
                "$inc": {"attempts": 1,"polls": 1},
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


