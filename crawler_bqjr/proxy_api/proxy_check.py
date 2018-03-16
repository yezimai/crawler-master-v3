# -*- coding: utf-8 -*-

from functools import wraps
from multiprocessing import Process, Queue
from queue import Empty
from threading import Thread
from time import sleep, time
from traceback import print_exc

from pymongo import ASCENDING as MONGO_ASCENDING
from requests import get as http_get, post as http_post

from crawler_bqjr.items.proxy_items import SchemeType, SupportMethod
from data_storage.db_settings import MONGO_PROXY_DB, \
    MONGO_PROXY_COLLECTIONS, MONGO_GOOD_PROXY_COLLECTIONS
from data_storage.mongo_db import MongoDB

HTTP_CHECK_URL_LIST = ["http://www.weibo.com/",
                       "http://www.yodao.com/",
                       "http://weixin.qq.com/",
                       "http://www.sohu.com/",
                       "http://www.sina.com.cn/",
                       # "http://www.qq.com/",
                       # "http://mail.163.com/",
                       # "http://www.youku.com/",
                       "http://wenshu.court.gov.cn/",
                       "http://www.189.cn/",
                       ]

HTTPS_CHECK_URL_LIST = ["https://account.chsi.com.cn/passport/login?service=https%3A%2F%2Fmy.chsi.com.cn%2Farchive%2Fj_spring_cas_security_check",
                        # "https://www.toutiao.com/",
                        # "https://www.jd.com/",
                        # "https://www.taobao.com/",
                        # "https://www.baidu.com/",
                        # "https://www.tmall.com/",
                        # "https://www.sogou.com/",
                        # "https://www.so.com/",
                        # "https://www.zhihu.com/",
                        ]

HTTP_CHECK_URL = HTTP_CHECK_URL_LIST[0]
HTTPS_CHECK_URL = HTTPS_CHECK_URL_LIST[0]

ASK_TIMEOUT = 11

REQ_HEADER = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept-Language': 'zh-CN,zh',
              'Connection': 'close',
              }

PROCESS_COUNT = 4
THREAD_COUNT = 64


def pass_except(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # from traceback import print_exc
            # print_exc()
            # pass
            return None

    return inner


@pass_except
def get_web_html_by_requests(url, proxies):
    start = time()
    resp = http_get(url, headers=REQ_HEADER, proxies=proxies, timeout=ASK_TIMEOUT)
    response_time = time() - start
    resp.close()
    return response_time if 200 == resp.status_code else None


@pass_except
def post_web_html_by_requests(url, data, proxies):
    start = time()
    resp = http_post(url, data=data, headers=REQ_HEADER, proxies=proxies, timeout=ASK_TIMEOUT)
    response_time = time() - start
    resp.close()
    return response_time if 200 == resp.status_code else None


def _run_thread_check_proxy(thread_count, target, args=()):
    thread_list = []
    for i in range(thread_count):
        t = Thread(target=target, args=args)
        t.setDaemon(False)
        t.start()
        thread_list.append(t)
        sleep(1)

    for t in thread_list:
        t.join()


# 返回平均响应时间和检查通过次数
def check_one_proxy(proxy_info_dict):
    http_scheme = SchemeType.HTTP
    post_method = SupportMethod.POST

    if proxy_info_dict.get("support_method", SupportMethod.GET) == post_method:  # TODO: 处理post的代理
        return -1, 0

    proxy_str = proxy_info_dict["ip"] + ":" + str(proxy_info_dict["port"])
    total_response_time = 0.0
    quality = 0
    if proxy_info_dict.get("scheme_type", http_scheme) == http_scheme:
        for url in HTTP_CHECK_URL_LIST:
            response_time = get_web_html_by_requests(url, proxies={'http': 'http://' + proxy_str})
            if response_time:
                total_response_time += response_time
                quality += 1
    else:
        for url in HTTPS_CHECK_URL_LIST:
            response_time = get_web_html_by_requests(url, proxies={'https': 'https://' + proxy_str})
            if response_time:
                total_response_time += response_time
                quality += 1

    return (total_response_time / quality, quality) if quality else (-1, 0)


def _run_check_proxy(proxy_infos_queue, ret_infos_queue):
    while True:
        try:
            proxy_info_dict = proxy_infos_queue.get(timeout=3)
            response_time, quality = check_one_proxy(proxy_info_dict)
            ret_infos_queue.put((response_time, quality, proxy_info_dict["_id"]))
        except Exception as e:
            if type(e) is not Empty:  # Queue.get没有数据的异常不打印
                print_exc()
            return


def del_duplicate_proxy(collection):
    proxy_unique_set = set()
    duplicate_ids = []
    with MongoDB(MONGO_PROXY_DB, collection) as mongo_instance:
        for item in mongo_instance.getAll(fields={"ip": 1, "port": 1}):
            try:
                proxy_unique = item["ip"] + ":" + str(item["port"])
                if proxy_unique not in proxy_unique_set:
                    proxy_unique_set.add(proxy_unique)
                else:
                    duplicate_ids.append(item["_id"])
            except Exception:
                print_exc()

        for the_id in duplicate_ids:
            mongo_instance.deleteOne(filter={"_id": the_id})

    print("Del %d of duplicated item in collection[%s]" % (len(duplicate_ids), collection))
    del duplicate_ids

    return proxy_unique_set


def get_proxy_from_kuaidaili():
    try:
        url = "http://dps.kuaidaili.com/api/getdps/" \
              "?orderid=959308673589451&num=50&sep=1&f_loc=1&dedup=1"
        resp = http_get(url)
        text = resp.text
        if resp.status_code == 200 and not text.startswith("ERROR"):
            return text.split()
    except Exception:
        from traceback import print_exc
        print_exc()

    return []


def _check_proxy_usable(mongo_instance):
    g_proxy_infos_queue = Queue()
    g_ret_infos_queue = Queue()  # 输出信息

    start = time()

    # 删除很多次尝试都无效的代理
    mongo_instance.deleteMany(filter={"ok_times": 0,
                                      "fail_times": {"$gt": 21}
                                      })
    mongo_instance.deleteMany(filter={"response_time": -1,
                                      "fail_times": {"$gt": 100}
                                      })

    # 所有可用的代理都要不断检查
    for proxy_info_dict in mongo_instance.getAll(filter={"quality": {"$gt": 0}}):
        g_proxy_infos_queue.put(proxy_info_dict)

    # 抽2000个失效的代理再检查一遍
    # 因为每次检查完会把fail_times加1,所以按fail_times升序排序的前2000个总是离上次检查最久的.
    for proxy_info_dict in mongo_instance.getAll(filter={"quality": 0},
                                                 sort=[("fail_times", MONGO_ASCENDING)],
                                                 limit=2000):
        g_proxy_infos_queue.put(proxy_info_dict)

    process_list = []
    for i in range(PROCESS_COUNT):
        process = Process(target=_run_thread_check_proxy, args=(THREAD_COUNT,
                                                                _run_check_proxy,
                                                                (g_proxy_infos_queue,
                                                                 g_ret_infos_queue,
                                                                 ))
                          )
        process.start()
        process_list.append(process)

    # 因为子进程也会向队列中加入元素，如果用process.join()等待子进程结束会造成死锁
    # 详情见https://docs.python.org/2/library/multiprocessing.html
    # 所以用轮询process.is_alive()的方法判断处理是否结束
    while True:
        all_down = 1
        for p in process_list:
            if p.is_alive():
                all_down = 0
                break

        try:
            while not g_ret_infos_queue.empty():
                response_time, quality, _id = g_ret_infos_queue.get()
                updater = {"$set": {"response_time": response_time,
                                    "quality": quality,
                                    }
                           }
                updater["$inc"] = {"ok_times": 1} if quality else {"fail_times": 1}
                mongo_instance.updateOne({"_id": _id}, updater)
        except Exception as e:
            if type(e) is not Empty:  # Queue.get没有数据的异常不打印
                print_exc()
        finally:
            if all_down:
                # print("All Down", time() - start)
                break
            else:
                sleep(31)

    g_proxy_infos_queue.close()
    g_ret_infos_queue.close()


def check_proxy_usable():
    del_duplicate_proxy(MONGO_PROXY_COLLECTIONS)
    # proxy_set = del_duplicate_proxy(MONGO_GOOD_PROXY_COLLECTIONS)

    mongo_instance_spider = MongoDB(MONGO_PROXY_DB, MONGO_PROXY_COLLECTIONS)
    # mongo_instance_kuaidaili = MongoDB(MONGO_PROXY_DB, MONGO_GOOD_PROXY_COLLECTIONS)

    while True:
        try:
            _check_proxy_usable(mongo_instance_spider)

            # _check_proxy_usable(mongo_instance_kuaidaili)
            # for proxy in get_proxy_from_kuaidaili():
            #     if proxy in proxy_set:
            #         continue
            #
            #     ip, other = proxy.split(":", 1)
            #     port, location = other.split(",", 1)
            #     item = {"ip": ip,
            #             "port": int(port),
            #             "location": location,
            #             "response_time": -1,
            #             "fail_times": 0,
            #             "ok_times": 0,
            #             "quality": 0,
            #             }
            #     proxy_set.add(proxy)
            #     mongo_instance_kuaidaili.insertOne(item)
        except Exception:
            print_exc()


if __name__ == '__main__':
    check_proxy_usable()
