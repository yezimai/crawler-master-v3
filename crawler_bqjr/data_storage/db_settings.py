# -*- coding: utf-8 -*-
import constants_settings

MONGO_ECOMMERCE_DB = "ecommerce"
MONGO_COMMUNICATIONS_DB = "communications"
MONGO_COMPANY_DB = "company"
MONGO_5XIAN1JIN_DB = "5xian1jin"
MONGO_SHIXIN_DB = "shixin"
MONGO_WENSHU_DB = "wenshu"
MONGO_ZHENGXIN_DB = "zhengxin"
MONGO_OTHER_DB = "other"
MONGO_PROXY_DB = "proxy_pool"
MONGO_MOBILEBRAND_DB = "mobile_brand"
MONGO_XUEXIN_DB = "xuexin"
MONGO_BANK_DB = "bank"
MONGO_EMAILBILL_DB = 'email_bill'

MONGO_SETTINGS = {
    MONGO_ECOMMERCE_DB: constants_settings.DATA_STORAGE_MONGO_ECOMMERCE_DB,
    MONGO_COMMUNICATIONS_DB: constants_settings.DATA_STORAGE_MONGO_COMMUNICATIONS_DB,
    MONGO_COMPANY_DB: constants_settings.DATA_STORAGE_MONGO_COMPANY_DB,
    MONGO_5XIAN1JIN_DB: constants_settings.DATA_STORAGE_MONGO_5XIAN1JIN_DB,
    MONGO_SHIXIN_DB: constants_settings.DATA_STORAGE_MONGO_SHIXIN_DB,
    MONGO_WENSHU_DB: constants_settings.DATA_STORAGE_MONGO_WENSHU_DB,
    MONGO_ZHENGXIN_DB: constants_settings.DATA_STORAGE_MONGO_ZHENGXIN_DB,
    MONGO_OTHER_DB: constants_settings.DATA_STORAGE_MONGO_OTHER_DB,
    MONGO_PROXY_DB: constants_settings.DATA_STORAGE_MONGO_PROXY_DB,
    MONGO_MOBILEBRAND_DB: constants_settings.DATA_STORAGE_MONGO_MOBILEBRAND_DB,
    MONGO_XUEXIN_DB: constants_settings.DATA_STORAGE_MONGO_XUEXIN_DB,
    MONGO_BANK_DB: constants_settings.DATA_STORAGE_MONGO_BANK_DB,
    MONGO_EMAILBILL_DB: constants_settings.DATA_STORAGE_MONGO_EMAILBILL_DB,
}

MONGO_PROXY_COLLECTIONS = "proxy_list"  # 代理IP列表
MONGO_GOOD_PROXY_COLLECTIONS = "good_proxy"  # 可用的代理

MONGO_COMMUNICATIONS_COLLECTIONS = "user_communication_info"  # 用户的运营商数据
MONGO_YOURNUMBER_COLLECTIONS = "yournumber_phone_info"  # 查询电话号码标记信息(yournumber.cn)

MONGO_COMPANY_COLLECTIONS = "company"  # 公司名单
MONGO_COMPANY_DETAIL_COLLECTIONS = "company_detail"  # szmqs爬取的工商数据
MONGO_COMPANY_DETAIL2_COLLECTIONS = "company_detail2"  # 58爬取的工商数据
MONGO_COMPANY_DETAIL3_COLLECTIONS = "company_detail3"  # 国家企业信用信息公示系统爬取的工商数据
MONGO_COMPANY_DETAIL4_COLLECTIONS = "company_detail4"  # tianyancha爬取的工商数据

MONGO_SHIXIN_LIST_COLLECTIONS = "shixin_list"  # shixin.court.gov.cn首页的失信名单
MONGO_SHIXIN_DETAIL_COLLECTIONS = "shixin_detail"  # 失信名单（包含详情）
MONGO_ZHIXING_DETAIL_COLLECTIONS = "zhixing_detail"  # 被执行人名单（包含详情）
MONGO_P2P_DEADBEAT_COLLECTIONS = 'p2p_deadbeat'  # p2p老赖信息

MONGO_WENSHU_COLLECTIONS = "wenshu"  # 裁判文书
MONGO_CHINACOURT_COLLECTIONS = "chinacourt"  # 中国法院
MONGO_WENSHU_CONDITION_COLLECTIONS = "wenshu_condition"

MONGO_ZHIFUBAO_COLLECTIONS = "zhifubao"  # 支付宝
MONGO_TAOBAO_COLLECTIONS = "taobao"
MONGO_JD_COLLECTIONS = "jingdong"  # 京东

MONGO_BANK_COLLECTIONS = "bank_trade"  # 银行交易明细

MONGO_EMAILBILL_COLLECTIONS = 'email_bill'  # 邮箱账单

MONGO_ZHENGXIN_PBC_COLLECTIONS = "zhengxin_pbc"  # 人行征信

MONGO_XUEXIN_COLLECTIONS = "xuexin"  # 学历信息

MONGO_SHEBAO_COLLECTIONS = "shebao"  # 社保
MONGO_HOUSEFUND_COLLECTIONS = "housefund"  # 公积金

MONGO_MOBILEBRAND_COLLECTIONS = "mobile_brand"  # 手机型号
MONGO_MOBILEACCESSORY_COLLECTIONS = "mobile_accessory"  # 手机配件

MONGO_SHOP_COLLECTIONS = "shop"  # 商铺

MONGO_ADDRESS_COLLECTIONS = "address"  # 地址

SSDB_SETTINGS = constants_settings.DATA_STORAGE_SSDB_SETTINGS

SSDB_WENSHU_ID_HSET = "wenshu_id_hset"  # 记录已经采集的文书id
SSDB_WENSHU_ID_ERROR_HSET = "wenshu_id_error_hset"  # 记录采集中因为出错的文书id
SSDB_WENSHU_CONDITION_QUEUE = "wenshu_query_condition_queue"

SSDB_ADDRESS_QUEUE = "address_queue"

RABBITMQ_SETTINGS = constants_settings.DATA_STORAGE_RABBITMQ_SETTINGS

# rabbitmq队列名
RABBITMQ_QUEUE = {
    "xuexin": "CRAWL_XUEXIN_QUEUE",

    "zhengxin": "CRAWL_ZHENGXIN_QUEUE",

    "yunyingshang": "CRAWL_YUNYINGSHANG_QUEUE",

    # ecommerce rabbitmq queue
    "jingdong": "CRAWL_JINGDONG_QUEUE",
    "taobao": "CRAWL_TAOBAO_QUEUE",
    "alipay": "CRAWL_ALIPAY_QUEUE",
}

RABBITMQ_EXCHANGE = "CRAWL_EXCHANGE"
