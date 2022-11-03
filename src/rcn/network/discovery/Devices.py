# Imports
import datetime
from rcn.mongo import mongo_client
from starlette.config import Config
from rcn.network.discovery import Device

import logging
from pymongo import ReturnDocument
from pymongo.collection import Collection
# Get an instance of a logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
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

    def next(self,Working=False):
        filter = {
            "$or": [
                {"Queue": None},
                {
                    "Queue.locked_by": None, 
                    "Queue.locked_at": None, 
                    "$or": [
                        {"Queue.next_poll": {"$exists": False}}, 
                        {"Queue.next_poll": None}, 
                        {"Queue.next_poll": {"$lt": datetime.datetime.now()}}
                    ]
                }
            ]
        }
        if Working:
            filter["NetDiscovery.result"] = "Working"
        else:
            filter["NetDiscovery.result"] = {"$ne": "Working"}
            

        aggregate_result = list(
            self.device_collection.aggregate(
                [
                    {
                        "$match": filter
                    },
                    {"$limit": 1},
                ],
            ),
        )
        if not aggregate_result:
            return None
        return self._wrap_one(
            self.device_collection.find_one_and_update(
                filter={"_id": aggregate_result[0]["_id"], "Queue.locked_by": None, "Queue.locked_at": None},
                update={"$set": {"Queue.locked_at": datetime.datetime.now()}},
                return_document=ReturnDocument.AFTER,
            ),
        )


    def _wrap_one(self, data):
        return Device(data) or None




