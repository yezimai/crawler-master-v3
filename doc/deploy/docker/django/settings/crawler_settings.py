# -*- coding: utf-8 -*-

# Scrapy settings for crawler_bqjr project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

from os import path as os_path, makedirs
from platform import system as get_os

this_dir = os_path.dirname(os_path.abspath(__file__))

BOT_NAME = 'crawler_bqjr'

SPIDER_MODULES = ['crawler_bqjr.spiders']
NEWSPIDER_MODULE = 'crawler_bqjr.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.3  # 下载器在下载同一个网站下一个页面前需要等待的时间(单位:秒)
DOWNLOAD_TIMEOUT = 61  # 下载器超时时间(单位:秒)
DOWNLOAD_MAXSIZE = 67108864  # 64M

# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 1
# CONCURRENT_REQUESTS_PER_IP = 0

# Disable cookies (enabled by default)
COOKIES_DEBUG = False
ALLOWED_HOSTS = ['*']

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'crawler_bqjr.middlewares.CrawlerBqjrSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'crawler_bqjr.middlewares.RandomUserAgentDownloaderMiddleware': 1,
    'crawler_bqjr.middlewares.PhantomjsDownloaderMiddleware': 2,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 3,
}

# DOWNLOADER_MIDDLEWARES_BASE = {
#     'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
#     'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 300,
#     'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
#     'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 400,
#     'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
#     'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 550,
#     'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
#     'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 590,
#     'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
#     'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
#     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
#     'scrapy.downloadermiddlewares.chunked.ChunkedTransferMiddleware': 830,
#     'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
#     'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
# }

DOWNLOAD_HANDLERS = {
    'js': 'crawler_bqjr.downloader_handlers.PhantomJSHandler',  # 需要执行js动态生成页面的情况
}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'crawler_bqjr.pipelines.zhengxin_pipeline.ZhengxinPbcPipeline': 1,
    'crawler_bqjr.pipelines.bank_pipeline.BankPipeline': 2,
    'crawler_bqjr.pipelines.emailbill_pipeline.EmailBillPipeline': 3,
    'crawler_bqjr.pipelines.communications_pipeline.UserCommunicationInfoPipeline': 100,
    'crawler_bqjr.pipelines.xuexin_pipeline.XuexinPipeline': 101,
    'crawler_bqjr.pipelines.ecommerce_pipeline.ZhiFuBaoPipeline': 200,
    'crawler_bqjr.pipelines.ecommerce_pipeline.JDPipeline': 201,
    'crawler_bqjr.pipelines.ecommerce_pipeline.TAOBAOPipeline': 202,
    'crawler_bqjr.pipelines.shixin_pipeline.ShixinListPipeline': 300,
    'crawler_bqjr.pipelines.shixin_pipeline.ShixinDetailPipeline': 301,
    'crawler_bqjr.pipelines.shixin_pipeline.ZhixingDetailPipeline': 302,
    'crawler_bqjr.pipelines.shixin_pipeline.P2PPipeline': 303,
    'crawler_bqjr.pipelines.housefund_pipeline.HousefundPipeline': 400,
    'crawler_bqjr.pipelines.shebao_pipeline.SheBaoPipeline': 401,
    'crawler_bqjr.pipelines.communications_pipeline.YournumberPipeline': 500,
    'crawler_bqjr.pipelines.mobilebrand_pipeline.CnmoPipeline': 600,
    'crawler_bqjr.pipelines.mobilebrand_pipeline.ZolAccessoryPipeline': 601,
    'crawler_bqjr.pipelines.company_pipeline.GSXTDetailPipline': 700,
    'crawler_bqjr.pipelines.company_pipeline.CompanyDetailPipeline': 702,
    'crawler_bqjr.pipelines.company_pipeline.CompanyDetail2Pipeline': 701,
    'crawler_bqjr.pipelines.company_pipeline.CompanyPipeline': 703,
    'crawler_bqjr.pipelines.wenshu_pipeline.WenshuPipeline': 800,
    'crawler_bqjr.pipelines.wenshu_pipeline.ChinacourtPipeline': 801,
    'crawler_bqjr.pipelines.proxy_pipeline.ProxyPipeline': 3000,
    'crawler_bqjr.pipelines.shop_pipeline.YishangPipeline': 3100,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'


if 'Windows' == get_os():  # 开发人员调试环境
    LOG_FILE = None
    LOG_LEVEL = "INFO"

    HTML_DIR = r"e:\html_data"
    IMAGE_DIR = r"e:\image_data"  # 亿商公益商户图片保存目录
    WENSHU_DIR = r"e:\wenshu_data"  # 裁判文书保存目录(1刑事案件2民事案件3行政案件4赔偿案件5执行案件)
    IMAGE_HTTP_SUFFIX = 'http://10.41.1.168/images/xuexin/'

    PHANTOMJS_EXECUTABLE_PATH = os_path.join(this_dir, 'browsers', 'phantomJS', 'phantomjs.exe')
    CHROME_EXECUTABLE_PATH = os_path.join(this_dir, 'browsers', 'chrome', 'chromedriver.exe')
    IE_EXECUTABLE_PATH = os_path.join(this_dir, 'browsers', 'IE', 'IEDriverServer.exe')
    IE_EXECUTABLE_233_PATH = os_path.join(this_dir, 'browsers', 'IE', 'IEDriverServer_233.exe')

    HEADLESS_CHROME_PATH = r"C:\Users\Administrator\AppData\Local\Google\Chrome SxS\Application\chrome.exe"

    CHROME_DOWNLOAD_DIR = "C:\\Users\\Daniel\\Downloads\\"
    assert CHROME_DOWNLOAD_DIR.endswith("\\")

    SEND_MAIL_ENABLED = False  # 是否发送邮件
else:  # Linux生产环境
    LOG_FILE = '/logs/crawler.log'
    LOG_LEVEL = "INFO"

    HTML_DIR = "/data/html_data/"
    IMAGE_DIR = "/data/image_data/"  # 亿商公益商户图片保存目录
    WENSHU_DIR = "/data/wenshu_data/"  # 裁判文书保存目录
    IMAGE_HTTP_SUFFIX = 'http://10.41.1.168/images/xuexin/'

    PHANTOMJS_EXECUTABLE_PATH = os_path.join(this_dir, 'browsers', 'phantomJS', 'phantomjs')
    CHROME_EXECUTABLE_PATH = os_path.join(this_dir, 'browsers', 'chrome', 'chromedriver')

    HEADLESS_CHROME_PATH = CHROME_EXECUTABLE_PATH

    CHROME_DOWNLOAD_DIR = "/"
    assert CHROME_DOWNLOAD_DIR.endswith("/")

    SEND_MAIL_ENABLED = True  # 是否发送邮件

if not os_path.exists(HTML_DIR):
    makedirs(HTML_DIR)
if not os_path.exists(IMAGE_DIR):
    makedirs(IMAGE_DIR)
if not os_path.exists(WENSHU_DIR):
    makedirs(WENSHU_DIR)

PHANTOMJS_OPTIONS = ['--load-images=false',
                     '--disk-cache=false'
                     ]
WEBDRIVER_CHECK_WAIT_TIME = 0.1
WEBDRIVER_LOAD_TIMEOUT = 60  # 页面加载超时，单位秒

DO_NOTHING_URL = "https://10.41.1.168/_"

WEB_SERVICE_HOST = "https://10.41.1.168/"
RECOGNIZE_CAPTCHA_API = WEB_SERVICE_HOST + "recognize_captcha/"

NOTICE_MAIL_LIST = ["zhidan.wang@bqjr.cn"]

DEBUG_COMMUNICATIONS_SPIDERS = False

