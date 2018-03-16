# crawler_bqjr -> settings.py
CRAWLER_BQJR_LOG_FILE = '/logs/crawler.log'
CRAWLER_BQJR_LOG_LEVEL = "ERROR"
CRAWLER_BQJR_DO_NOTHING_URL = "http://10.83.36.86/_"
CRAWLER_BQJR_WEB_SERVICE_HOST = "http://10.83.36.86/"
CRAWLER_BQJR_IMAGE_HTTP_SUFFIX = 'http://39.108.214.11/images/xuexin/'

# data_storage -> db_settings
DATA_STORAGE_MONGO_ECOMMERCE_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "user_dianshang_db",
    'password': "yigeanquandemima",
    }
DATA_STORAGE_MONGO_COMMUNICATIONS_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "operator_db_account",
    'password': "woshibuzhidao",
    }
DATA_STORAGE_MONGO_COMPANY_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "company_user",
    'password': "123456",
    }
DATA_STORAGE_MONGO_5XIAN1JIN_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "shebaogongjijin",
    'password': "kongpabunengshuoo",
    }
DATA_STORAGE_MONGO_SHIXIN_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "shixin_main_user",
    'password': "bunenggaosuni",
    }
DATA_STORAGE_MONGO_WENSHU_DB = {
    'port': 27017,
    'host': '10.83.36.86',
    'username': "user_wenshu",
    'password': "pawenshu",
    }
DATA_STORAGE_MONGO_ZHENGXIN_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "zx_db_user",
    'password': "xiangyixiang",
    }
DATA_STORAGE_MONGO_OTHER_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "shop_user",
    'password': "123456",
    }
DATA_STORAGE_MONGO_PROXY_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "proxy_user",
    'password': "123456",
}
DATA_STORAGE_MONGO_MOBILEBRAND_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "mobile_brand_user",
    'password': "123456",
    }
DATA_STORAGE_MONGO_XUEXIN_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "userinfo_xuexin_user",
    'password': "mimahaoduoo",
    }
DATA_STORAGE_MONGO_BANK_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "mongo_bank_user",
    'password': "yaobaohuyonghuyinsi",
    }
DATA_STORAGE_MONGO_EMAILBILL_DB = {
    'host': '10.83.36.86',
    'port': 27017,
    'username': "mongo_user_for_emailbill",
    'password': "youyaoxiangyigemima",
    }

DATA_STORAGE_SSDB_SETTINGS = {
    'local': {
        'host': '10.83.36.86',
        'port': 8888,
        'auth_enable': True,
        'auth': 'bqjr1234567890qwertyuiopasdfghjklzxcvbnm',
    },
}

DATA_STORAGE_RABBITMQ_SETTINGS = {
    'local': {
        'host': '10.83.36.86',
        'port': 5672,
        'username': 'bqjr_crawler',
        'password': 'bqjr@2017'
    }
}

# web_service -> settings.py
WEB_SETTINGS_DEBUG = True
WEB_SETTINGS_ALLOWED_HOSTS = ["*"]
#WEB_SETTINGS_ALLOWED_HOSTS = ["10.83.36.86", "127.0.0.1", "localhost", "39.108.214.11"]
WEB_SETTINGS_DOMAIN = "http://10.83.36.86/"
WEB_SETTINGS_ACCESS_DOMAIN = "http://10.89.1.100:12000/"
WEB_SETTINGS_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'captchas',
        'CONN_MAX_AGE': 28000,  # 连接老化时间，mysql自身的连接老化时间是28800
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '10.83.36.86',
        'PORT': ''
    }
}
WEB_SETTINGS_LOG_FILE = '/logs/django.log'