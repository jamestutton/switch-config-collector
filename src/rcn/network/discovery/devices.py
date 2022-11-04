# Imports
import datetime
import logging

from pymongo import ReturnDocument
from pymongo.collection import Collection
from rcn.mongo import mongo_client
from rcn.network.discovery import Device
from starlette.config import Config

# Get an instance of a logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = Config()


class Devices:
    def __init__(self):
        config = Config()
        _MONGODB_NAME = config("MONGODB_NAME", cast=str)
        self._MONGODB = mongo_client[f"{_MONGODB_NAME}"]
        self.collect_config_result = "UNKOWN"
        self._device_collection = getattr(self._MONGODB, "network")
        self.max_attempts = 1

        self._batch_size = config("BATCH_SIZE", cast=int, default=32)

    @property
    def device_collection(self) -> Collection:
        return self._device_collection

    def QueueFilter(self, suffix="NetDiscovery"):
        filter = {
            "$or": [
                {f"{suffix}": None},
                {f"{suffix}.Queue": None},
                {
                    f"{suffix}.Queue.locked_by": None,
                    f"{suffix}.Queue.locked_at": None,
                    "$or": [
                        {f"{suffix}.Queue.next_poll": {"$exists": False}},
                        {f"{suffix}.Queue.next_poll": None},
                        {f"{suffix}.Queue.next_poll": {"$lt": datetime.datetime.now()}},
                    ],
                },
            ],
        }
        return filter

    def _next(self, suffix):
        filter = self.QueueFilter(suffix)

        aggregate_result = list(
            self.device_collection.aggregate(
                [
                    {"$match": filter},
                    {"$limit": 1},
                ],
            ),
        )
        if not aggregate_result:
            return None
        return self._wrap_one(
            self.device_collection.find_one_and_update(
                filter={
                    "_id": aggregate_result[0]["_id"],
                    f"{suffix}.Queue.locked_by": None,
                    f"{suffix}.locked_at": None,
                },
                update={"$set": {f"{suffix}.Queue.locked_at": datetime.datetime.now()}},
                return_document=ReturnDocument.AFTER,
            ),
        )

    def nextSNMP(self):
        return self._next("SNMP")

    def nextNetDiscovery(self):
        return self._next(Device.NetworkDiscoveryName())

    def _wrap_one(self, data):
        return Device(data) or None
