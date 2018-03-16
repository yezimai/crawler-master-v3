# -*- coding: utf-8 -*-

from datetime import datetime
from logging import getLogger

from dateutil.relativedelta import relativedelta
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from utils import catch_except

from crawler_bqjr.items.proxy_items import AnonymousLevel, SchemeType, SupportMethod
from data_storage.db_settings import MONGO_MOBILEBRAND_COLLECTIONS, MONGO_MOBILEBRAND_DB
from data_storage.mongo_db import MongoDB
from proxy_api.proxy_utils import ProxyApi

logger = getLogger('rest_api')


@require_http_methods(["GET"])
@catch_except
def get_one_proxy(request):
    proxy_api = ProxyApi()
    try:
        args = request.GET
        proxy = proxy_api.get_proxy_one(location=args.get("location"),
                                        anonymous=int(args.get("anonymous", AnonymousLevel.HIGH)),
                                        scheme=int(args.get("scheme", SchemeType.HTTP)),
                                        method=int(args.get("method", SupportMethod.GET))
                                        )
    except Exception:
        return HttpResponseBadRequest("Bad Request!")
    else:
        return JsonResponse({"proxy": proxy})
    finally:
        proxy_api.close()


@require_http_methods(["GET"])
@catch_except
def get_mobile_phone(request):
    mongo_instance = MongoDB(MONGO_MOBILEBRAND_DB, MONGO_MOBILEBRAND_COLLECTIONS)
    try:
        update_time = request.GET.get("update_time")
        if update_time:
            update_time = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S.%f")
        else:
            update_time = datetime.now() - relativedelta(days=1)
        data_list = []
        for data in mongo_instance.getAll(filter={"update_time": {"$gt": update_time}},
                                          fields={"product_name": 1, "for_sale": 1,
                                                  "brand_name": 1, "product_price": 1,
                                                  "update_time": 1}):
            data["_id"] = "0x" + str(data["_id"])
            data_list.append(data)
    except Exception:
        logger.exception("get_mobile_phone")
        return HttpResponseBadRequest("Bad Request!")
    else:
        return JsonResponse(data_list, safe=False)
    finally:
        mongo_instance.close()
