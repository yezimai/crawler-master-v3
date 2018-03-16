# -*- coding: utf-8 -*-

from os import path as os_path, makedirs, system as os_system, listdir
from platform import system as get_os
from time import time
from traceback import print_exc

MONGO_HOST = "10.89.1.54"
MONGO_PORT = "27017"
MONGO_USER = "shixin_readonly"
MONGO_PASS = "mimayaobaomi"

# 请修改mongoexport的路径
if 'Windows' == get_os():
    MONGOEXPORT_PATH = r"D:\software\MongoDB\Server\3.4\bin\mongoexport.exe"
    DATA_DIR = "F:\\backup\\"  # 必须有个斜杠结尾
    assert DATA_DIR.endswith("\\")
else:  # Linux
    MONGOEXPORT_PATH = "/usr/local/mongodb/bin/mongoexport"
    DATA_DIR = "/opt/backup/"  # 必须有个斜杠结尾
    assert DATA_DIR.endswith("/")

if not os_path.exists(DATA_DIR):
    makedirs(DATA_DIR)

TEST = False

export_db_dict = {
    "shixin":
        [
            "shixin_detail",
            "zhixing_detail",
        ],
}


def cmd_export(db, collection, end_time, query=None):
    cmd_list = [MONGOEXPORT_PATH,
                " -h ", MONGO_HOST, ":", MONGO_PORT,
                " -u ", MONGO_USER, " -p ", MONGO_PASS,
                " -d ", db, " -c ", collection,
                " -o ", DATA_DIR, db, ".", collection, ".", end_time, ".json",
                ]
    if query:
        cmd_list.extend([" -q '", query, "'"])
    if not TEST:
        cmd_list.append(" --quiet")

    cmd = "".join(cmd_list)
    ret = os_system(cmd)
    if ret != 0:
        print("Export %s.%s failed!!!" % (db, collection))


if __name__ == '__main__':
    if not TEST:
        print(u"Start exporting data.")
        start = time()

        time_now = str(int(start * 1E3))
        default_query = "{update_time:{$lte:new Date(%s)}}" % time_now
        query_dict = {}

        file_list = listdir(DATA_DIR)
        file_list.sort()
        for file in file_list:
            try:
                db, collection, last_time, suffix = file.split(".")
                query_dict[db + "." + collection] = '{update_time:{$gt:new Date(%s),$lte:new Date(%s)}}' \
                                                    % (last_time, time_now)
            except Exception:
                print_exc()

        for db, collections in export_db_dict.items():
            for collection in collections:
                try:
                    cmd_export(db, collection, time_now, query_dict.get(db + "." + collection, default_query))
                except Exception:
                    print_exc()

        print(u"Spent %s seconds." % int(time() - start))
    else:
        cmd_export("shixin", "shixin_list", "")
