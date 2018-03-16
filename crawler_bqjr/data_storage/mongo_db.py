# -*- coding: utf-8 -*-

from re import compile as re_compile

import pymongo
from pymongo.errors import ConnectionFailure

from data_storage import db_settings

ObjectId = pymongo.collection.ObjectId
MONGO_DESCENDING = pymongo.DESCENDING
MONGO_ASCENDING = pymongo.ASCENDING


def catch_mongo_except(func):
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionFailure:
            return func(*args, **kwargs)
        except Exception:
            from traceback import print_exc
            print_exc()

    return decorator


class MongoDB(object):
    def __init__(self, db_name, table):
        db_setting = db_settings.MONGO_SETTINGS[db_name]
        self.mongo_client = pymongo.MongoClient(db_setting["host"], db_setting["port"],
                                                connect=False)
        self.db = self.mongo_client[db_name]

        username = db_setting["username"]
        password = db_setting["password"]
        if username and password:
            self.db.authenticate(username, password)

        self.table = self.db[table]

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.mongo_client.close()
        return False

    @catch_mongo_except
    def getOne(self, **kwargs):
        result = self.table.find_one(kwargs.get("filter"), kwargs.get("fields"))
        return result or None

    @catch_mongo_except
    def getAll(self, **kwargs):
        result = self.table.find(kwargs.get("filter"), kwargs.get("fields"))

        sort = kwargs.get("sort")
        if sort is not None:
            result = result.sort(sort)
        limit = kwargs.get("limit")
        if limit is not None:
            result = result.limit(limit)
        skip = kwargs.get("skip")
        if skip is not None:
            result = result.skip(skip)

        return result

    @catch_mongo_except
    def distinct(self, key):
        return self.table.distinct(key)

    @catch_mongo_except
    def count(self, **kwargs):
        return self.table.count(kwargs.get("filter"))

    @catch_mongo_except
    def insertOne(self, value):
        return self.table.insert_one(value)

    @catch_mongo_except
    def updateOne(self, filter, update, upsert=False):
        return self.table.update_one(filter, update, upsert=upsert)

    @catch_mongo_except
    def deleteOne(self, **kwargs):
        return self.table.delete_one(kwargs.get("filter"))

    @catch_mongo_except
    def deleteMany(self, **kwargs):
        return self.table.delete_many(kwargs.get("filter"))

    @catch_mongo_except
    def aggregate(self, **kwargs):
        return self.table.aggregate(kwargs.get("pipeline"))

    @catch_mongo_except
    def changeTable(self, name):
        self.table = self.db[name]

    @catch_mongo_except
    def close(self):
        self.mongo_client.close()


if __name__ == '__main__':
    with MongoDB(db_settings.MONGO_PROXY_DB, db_settings.MONGO_PROXY_COLLECTIONS) as mongo:
        test = mongo.getOne(filter={"_id": ObjectId("5a1e812305a0ce000ffa0603")}, fields={"_id": 1})
        print(test)
        print(str(test["_id"]))
        filter_dict = {"location": re_compile(r".*贵阳.*")}
        test = mongo.getAll(filter=filter_dict, fields={"ip": 1, "port": 1, "_id": 0},
                            sort=[("_id", MONGO_DESCENDING)])
        test = {(item["ip"], item["port"]) for item in test}
        print(test)
