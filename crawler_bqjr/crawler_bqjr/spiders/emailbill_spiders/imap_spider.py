# coding : utf-8

from imaplib import IMAP4

from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spiders.emailbill_spiders.base import EmailSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import get_credit_card_bill_by_imap4
from crawler_bqjr.spiders_settings import EMAIL_DICT


class EmailImapSpider(EmailSpider):
    name = EMAIL_DICT["*.com"]
    start_urls = [DO_NOTHING_URL, ]
    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        username = item["username"]
        bill_records = item["bill_records"]
        try:
            imap_gen = get_credit_card_bill_by_imap4(username, item["password"])
            if next(imap_gen):
                self.crawling_login(username)

            for bank_name, subject, content in imap_gen:
                bill_records.append(self.get_bill_record(bank_name, subject, content))
            yield from self.crawling_done(item)
        except IMAP4.error:
            yield from self.except_handle(username, "IMAP出错：", "你的邮箱未开启IMAP或密码错误")
        except Exception:
            yield from self.except_handle(username, "IMAP异常：", "账单获取失败")
