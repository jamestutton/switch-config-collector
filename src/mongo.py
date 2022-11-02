import logging

from pymongo import MongoClient
from starlette.config import Config

# Get an instance of a logger
logger = logging.getLogger(__name__)

config = Config()
mongo_client = None
if config("OFFLINE", default=False, cast=bool):
    logger.warning("Running in offline mode")
else:
    mongo_client = MongoClient(config("MONGODB_URL"))
