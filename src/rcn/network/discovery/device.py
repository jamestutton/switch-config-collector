# Imports
import datetime
import logging
import platform
import random
import subprocess
import socket
import time
import netmiko
import paramiko
from local_settings import credentials
from paramiko import SSHException
from pymongo import ReturnDocument
from pymongo.collection import Collection
from rcn.mongo import mongo_client
from starlette.config import Config
from pysnmp.entity.rfc3413.oneliner import cmdgen
from rcn.network.discovery.utils import CSV2List

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

SnmpCommunityStrings = CSV2List("SNMP.lst")





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
        self.snmp_community = None

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

    @property
    def Succesful(self):
        if self.prompt and self.enable:
            return True
        else:
            return False

    @property
    def Source(self):
        host = socket.gethostname()
        return f"from__{host}"

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

    def SetSNMP(self):
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {
                    "NetDiscovery.SNMP": self.snmp_community,
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

    def Completed(self):
        Queue_data = {
            "locked_by": None,
            "locked_at": None,
            "completed_at": datetime.datetime.now(),
            "next_poll": datetime.datetime.now()
            + datetime.timedelta(hours=3)
            + datetime.timedelta(minutes=random.randint(1, 40)),
        }
        
        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {"Queue": Queue_data},
            },
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
            "succesful": self.Succesful,
            "last_error": self.error,
            "device_type": self.device_type,
        }
        if self.pingable:
            NetDiscovery_data["pingable"] = self.pingable
        elif self.Succesful:
            NetDiscovery_data["pingable"] = "Skipped"
        
        NetDiscovery_data["source"] = self.Source       
        NetDiscovery_data[self.Source] = self.Succesful


        self._data = self.device_collection.find_one_and_update(
            filter={"Management IP": self.current_ip_address},
            update={
                "$set": {"Queue": Queue_data, "NetDiscovery": NetDiscovery_data},
            },
            return_document=ReturnDocument.AFTER,
        )

    def TestComms(self, skipping=False):
        start_time = time.time()
        self.Processing()
        logger.info(f"Testing {self.ip}")
        result = "UNKNOWN"
        if skipping or self.init_ping():
            self.init_connection()
            if self.connected:
                self.close_connection()
                result = "Working"
            else:
                result = "Connection Failed"
        else:
            result = "Ping Failed"
        time_taken = (time.time() - start_time)
        logger.warning(f"Tested {self.ip} in ({time_taken}s) result= {result}")
        self.UpdateDB(result)

    def TrySNMPString(self,snmp_community,OID = '1.3.6.1.2.1.1.5.0'):
        logger.debug(f"Trying {snmp_community} on {self.ip}")
        # Define a PySNMP CommunityData object named auth, by providing the SNMP community string
        auth = cmdgen.CommunityData(snmp_community)

        # Define the CommandGenerator, which will be used to send SNMP queries
        cmdGen = cmdgen.CommandGenerator()

        # Query a network device using the getCmd() function, providing the auth object, a UDP transport
        # our OID for SYSNAME, and don't lookup the OID in PySNMP's MIB's
        errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
                auth,
                cmdgen.UdpTransportTarget((self.ip, 161),timeout=1.0, retries=0),
                cmdgen.MibVariable(OID),
                lookupMib=False,
        )

        # Check if there was an error querying the device
        if errorIndication:
            logger.debug(f"FAILED {snmp_community} on {self.ip} {errorIndication}, {errorStatus}, {errorIndex}")
        else:
            for oid, val in varBinds:
                if val:
                    logger.debug(f"MATCHED {self.ip} {snmp_community} {oid}=={val}")
                    return snmp_community
                else:
                    logger.info(f"KNOWN {self.ip} {snmp_community} {oid}=={val}")


    def FindSNMPCommunity(self):
        start_time = time.time()
        self.Processing()
        my_list = SnmpCommunityStrings
        for item in SnmpCommunityStrings:
          if self.TrySNMPString(item["value"]):
            self.snmp_community = item["code_name"]
            self.SetSNMP()
            break
        self.Completed()
        time_taken = (time.time() - start_time)
        logger.warning(f"FindSNMPCommunity {self.ip} in ({time_taken}s) result= {self.snmp_community}")
        


