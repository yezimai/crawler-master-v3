# -*- coding: UTF-8 -*-

from email.mime.text import MIMEText
from smtplib import SMTP
from traceback import print_exc

from crawler_bqjr.settings import SEND_MAIL_ENABLED, NOTICE_MAIL_LIST

MAIL_HOST = "smtp.exmail.qq.com"  # 设置服务器
MAIL_USER = "crawler_project"  # 用户名
MAIL_PASS = "Spider123456"  # 密码
MAIL_POSTFIX = "bqjr.cn"  # 发件箱的后缀
ME = "".join(("爬虫", "<", MAIL_USER, "@", MAIL_POSTFIX, ">"))
COMMASPACE = ', '


# to_list是收件者的邮箱列表，sub是邮件主题，content是邮件内容
def send_mail(to_list, sub, content):
    if not SEND_MAIL_ENABLED:
        return

    msg = MIMEText(content, 'html', _charset='utf-8')
    msg['Subject'] = sub
    msg['From'] = ME
    msg['To'] = COMMASPACE.join(to_list)
    with SMTP(MAIL_HOST) as server:
        try:
            # server.connect(MAIL_HOST)
            # server.ehlo()
            # server.starttls()
            # server.login(MAIL_USER, MAIL_PASS)
            server.login("@".join((MAIL_USER, MAIL_POSTFIX)), MAIL_PASS)
            server.sendmail(ME, to_list, msg.as_string())
            return True
        except Exception:
            print_exc()
            return False


def send_mail_2_admin(sub, content):
    send_mail(NOTICE_MAIL_LIST, sub, content)


if __name__ == '__main__':
    send_mail_2_admin("测试", '测试邮件')
