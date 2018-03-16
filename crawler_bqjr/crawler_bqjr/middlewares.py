# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html

# from scrapy.downloadermiddlewares.robotstxt import RobotsTxtMiddleware
# from scrapy.downloadermiddlewares.httpauth import HttpAuthMiddleware
# from scrapy.downloadermiddlewares.downloadtimeout import DownloadTimeoutMiddleware
# from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
# from scrapy.downloadermiddlewares.retry import RetryMiddleware
# from scrapy.downloadermiddlewares.defaultheaders import DefaultHeadersMiddleware
# from scrapy.downloadermiddlewares.redirect import MetaRefreshMiddleware
# from scrapy.downloadermiddlewares.httpcompression import HttpCompressionMiddleware
# from scrapy.downloadermiddlewares.redirect import RedirectMiddleware
# from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
# from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
# from scrapy.downloadermiddlewares.chunked import ChunkedTransferMiddleware
# from scrapy.downloadermiddlewares.stats import DownloaderStats
# from scrapy.downloadermiddlewares.httpcache import HttpCacheMiddleware

from urllib.parse import urlsplit, urlunsplit

from scrapy import signals

from crawler_bqjr.spider_class import PhantomjsRequestSpider
from crawler_bqjr.utils import get_one_ua


class RandomUserAgentDownloaderMiddleware(object):
    def process_request(self, request, spider):
        request.headers.setdefault('User-Agent', get_one_ua())


class PhantomjsDownloaderMiddleware(object):
    def process_request(self, request, spider):
        if isinstance(spider, PhantomjsRequestSpider):
            url = request.url
            if not url.startswith("js://"):
                new_request = request.replace(url=urlunsplit(("js",) + urlsplit(url)[1:]))

                meta = new_request.meta
                meta["original_url"] = url
                if "phantomjs_finish_xpath" not in meta:
                    meta["phantomjs_finish_xpath"] = spider.phantomjs_finish_xpath

                return new_request


class CrawlerBqjrSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
