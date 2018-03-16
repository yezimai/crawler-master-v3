# -*- coding: utf-8 -*-


# 运营商的爬虫名
COMMUNICATIONS_BRAND_DICT = {
    "移动": "ChinaMobile",
    "联通": "ChinaUnicom",
    "电信": "ChinaTelecom",
}

# 用户信息的爬虫名
USERINFO_DICT = {
    "学信": "xuexin",
}

# 征信信息的爬虫名
ZHENANGXIN_DICT = {
    "人行征信": 'zhengxin_pbc',
    "征信接口": 'zhengxin_interface',
}

# 电商信息的爬虫名
JINGDONG_DICT = {
    "京东": "ecommerce_jingdong",
}

TAOBAO_DICT = {
    "淘宝": "ecommerce_taobao",
}

ALIPAY_DICT = {
    "支付宝": "ecommerce_alipay",
}

YHD_DICT = {
    "一号店": "ecommerce_yhd",
}


OTHER_EMAIL_SPIDER_NAME = "imap_email"

# 电子邮件的爬虫名
EMAIL_DICT = {
    "163.com": '163_email',
    "126.com": '163_email',
    "yeah.net": '163_email',
    "qq.com": 'qq_email',
    'sina.com': 'sina_email',
    'sina.cn': 'sina_email',
    'sohu.com': 'sohu_email',
    '*.com': OTHER_EMAIL_SPIDER_NAME,
}

# 银行交易数据爬虫的爬虫名
BANK_DICT = {
    "农业银行": "bank_abc",
    "建设银行": "bank_ccb",
    "工商银行": "bank_icbc",
    "邮政银行": "bank_psbc",
    "中国银行": "bank_boc",
    "招商银行": "bank_cmb",
    "交通银行": "bank_bocom_wap",
    "兴业银行": "bank_cib",
    "民生银行": "bank_cmbc",
    "光大银行": "bank_ceb",
    "平安银行": "bank_pingan",
    "中信银行": "bank_cncb",
    "浦发银行": "bank_spdb",
    "广发银行": "bank_cgb_wap",
    "华夏银行": "bank_hxb",
}

# 公积金爬虫的爬虫名
HOUSEFUND_CITY_DICT = {
    "成都": "housefund_chengdu",
    "广州": "housefund_guangzhou",
}

# 社保爬虫的爬虫名
SHEBAO_CITY_DICT = {
    "成都": "shebao_chengdu",
    "广州": "shebao_guangzhou",
}

AccountType_2_SpiderNamesDict = {
    "communications": COMMUNICATIONS_BRAND_DICT,
    "housefund": HOUSEFUND_CITY_DICT,
    "shebao": SHEBAO_CITY_DICT,
    "xuexin": USERINFO_DICT,
    "bank": BANK_DICT,
    "emailbill": EMAIL_DICT,
    "zhengxin": ZHENANGXIN_DICT,
    "jingdong": JINGDONG_DICT,
    "taobao": TAOBAO_DICT,
    "alipay": ALIPAY_DICT,
    "yhd": YHD_DICT,
}

SpiderName_2_AccountType_DICT = {}
for account_type, spider_name_dict in AccountType_2_SpiderNamesDict.items():
    for spider_name in spider_name_dict.values():
        SpiderName_2_AccountType_DICT[spider_name] = account_type

AccountType_2_SpiderName_DICT = {
    "jingdong": JINGDONG_DICT["京东"],
    "taobao": TAOBAO_DICT["淘宝"],
    "alipay": ALIPAY_DICT["支付宝"],
    "yhd": YHD_DICT["一号店"],
}

ACCOUNT_CRAWLING_QUEUE_SSDB_SUFFIX = "-account_queue"

ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX = "-ask_send_sms_captcha-"

ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX = "-need_img_captcha-"
ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX = "-need_sms_captcha-"
ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX = "-need_img_sms_captcha-"
ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX = "-need_extra_captcha-"
ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX = "-need_qrcode_captcha-"
ACCOUNT_CRAWLING_NEED_NAME_IDCARD_SMS_SSDB_SUFFIX = "-need_name_idcard_sms_captcha-"

ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX = "-img_b64"
ACCOUNT_CRAWLING_IMG_DESCRIBE_SSDB_SUFFIX = "-img_des"
ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX = "-img_headers-"
ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX = "-sms_headers-"
ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX = "-sms"
ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX = "-img_url-"
ACCOUNT_CRAWLING_QRCODE_COOKIES_SSDB_SUFFIX = "-qrcode_cookies-"

ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX = "-crawling_status-"
ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX = "-crawling_msg-"
ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX = "-crawling_data-"
ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX = "-crawling_info-"

DATA_EXPIRE_TIME = 1800  # SSDB里的数据过期时间为1800秒

DIANXIN_APP_ENCRYPT_KEY = "1234567`90koiuyhgtfrdewsaqaqsqde"  # 电信app解密key
DIANXIN_APP_ENCRYPT_IV = b"\x00\x00\x00\x00\x00\x00\x00\x00"  # 电信app解密iv

CHINA_MOBILE_ENCRYPT_PUBLIC_KYE = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsgDq4OqxuEisnk2F0EJF
    mw4xKa5IrcqEYHvqxPs2CHEg2kolhfWA2SjNuGAHxyDDE5MLtOvzuXjBx/5YJtc9
    zj2xR/0moesS+Vi/xtG1tkVaTCba+TV+Y5C61iyr3FGqr+KOD4/XECu0Xky1W9Zm
    maFADmZi7+6gO9wjgVpU9aLcBcw/loHOeJrCqjp7pA98hRJRY+MML8MK15mnC4eb
    ooOva+mJlstW6t/1lghR8WNV8cocxgcHHuXBxgns2MlACQbSdJ8c6Z3RQeRZBzyj
    fey6JCCfbEKouVrWIUuPphBL3OANfgp0B+QG31bapvePTfXU48TYK0M5kE+8Lgbb
    WQIDAQAB
    -----END PUBLIC KEY-----"""
