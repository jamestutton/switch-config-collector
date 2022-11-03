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
from rcn.network.discovery import Device

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


# from paramiko import SSHException

# Get an instance of a logger

logger = logging.getLogger(__name__)
config = Config()



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
                            "$or": [{"next_poll": {"$exists": False}}, {"next_poll": {"$lt": datetime.datetime.now()}}],
                        },
                    },
                    {"$limit": 1},
                ],
            ),
        )
        if not aggregate_result:
            return None
        return self._wrap_one(
            self.device_collection.find_one_and_update(
                filter={"_id": aggregate_result[0]["_id"], "locked_by": None, "locked_at": None},
                update={"$set": {"locked_at": datetime.datetime.now()}},
                return_document=ReturnDocument.AFTER,
            ),
        )


    def _wrap_one(self, data):
        return Device(data) or None


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

