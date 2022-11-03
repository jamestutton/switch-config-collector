# Imports
import datetime
import logging
import platform
import random
import subprocess
import socket

import netmiko
import paramiko
from local_settings import credentials
from paramiko import SSHException
from pymongo import ReturnDocument
from pymongo.collection import Collection
from rcn.mongo import mongo_client
from starlette.config import Config

# import time
# import ipaddress
# import threading
# import json
# Imports custom created modules
# from pymongo import DeleteOne
# from pymongo import errors
# from pymongo import UpdateOne
# from pymongo.errors import BulkWriteError

# Get an instance of a logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = Config()


class Device:
    def __init__(self, data, current_index=1):
        self._data = data
        self.current_index = current_index

        _MONGODB_NAME = config("MONGODB_NAME", cast=str)

        self._MONGODB = mongo_client[f"{_MONGODB_NAME}"]
        self._device_collection = getattr(self._MONGODB, "network")

        # netmiko device types to test in order
        self.device_types = ["cisco_ios_ssh", "cisco_ios_telnet", "autodetect"]

        self.device_type = "UNKNOWN"
        self.collect_config_result = "NOT COLLECTED"
        self.version = ["N/A"]
        self.connection = None
        self.pingable = None
        self.prompt = None
        self.enable = None
        self.error = None

    @property
    def current_ip_address(self):
        return self._data["Management IP"]

    @property
    def ip(self):
        return self.current_ip_address

    @property
    def device_collection(self) -> Collection:
        return self._device_collection

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
                    self.connection = netmiko.ConnectHandler(
                        device_type=device_type,
                        ip=self.current_ip_address,
                        username=cred.username,
                        password=cred.password,
                        secret=cred.secret,
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
                except SSHException as e:
                    self.error = f"{e}"
                    continue
                except Exception as e:
                    self.error = f"{e}"
                    # logger.exception(e)

    def init_ping(self):
        try:
            output = subprocess.check_output(
                "ping -{} 1 {}".format("n" if platform.system().lower() == "windows" else "c", self.current_ip_address),
                shell=True,
                universal_newlines=True,
            )
            if "unreachable" in output:
                self.pingable = False
            else:
                self.pingable = True
        except Exception:
            self.pingable = False

        return self.pingable

    def close_connection(self):
        self.connection.disconnect()

    def HitsTacacs(self):
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {
                    "NetDiscovery.HitsTacacs": True,
                },
            },
            return_document=ReturnDocument.AFTER,
        )

    def Processing(self):
        Queue_data = {
            "locked_by": self.current_index,
            "locked_at": datetime.datetime.now(),
            "started_at": datetime.datetime.now(),
            "next_poll": datetime.datetime.now()
            + datetime.timedelta(hours=3)
            + datetime.timedelta(minutes=random.randint(1, 40)),
        }
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={"$set": {"Queue": Queue_data}},
            return_document=ReturnDocument.AFTER,
        )

    def UpdateDB(self, result):
        Queue_data = {
            "locked_by": None,
            "locked_at": None,
            "completed_at": datetime.datetime.now(),
            "next_poll": datetime.datetime.now()
            + datetime.timedelta(hours=3)
            + datetime.timedelta(minutes=random.randint(1, 40)),
        }
        NetDiscovery_data = {
            "result": result,
            "enable": self.enable,
            "prompt": self.prompt,
            "last_error": self.error,
            "device_type": self.device_type,
        }
        if self.pingable:
            NetDiscovery_data["pingable"] = self.pingable
        elif result == "Working":
            NetDiscovery_data["pingable"] = "Skipped"
            NetDiscovery_data["source"] = socket.gethostname()


        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {"Queue": Queue_data, "NetDiscovery": NetDiscovery_data},
                "$inc": {"Queue.attempts": 1, "Queue.polls": 1},
            },
            return_document=ReturnDocument.AFTER,
        )

    def TestComms(self, skipping=False):
        self.Processing()
        logger.info(f"Testing {self.ip}")
        if skipping or self.init_ping():
            self.init_connection()
            if self.connected:
                # device.collect_config_ssh()
                self.close_connection()
                self.UpdateDB("Working")
                return
            else:
                self.UpdateDB("Connection Failed")
                return
        else:
            self.UpdateDB("Ping Failed")
            return
