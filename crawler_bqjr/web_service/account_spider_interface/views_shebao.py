# coding:utf-8

from django.shortcuts import render
from utils import catch_except


##################################################################
#
#  社保登录接口
#
##################################################################
@catch_except
def show_index(req):
    return render(req, 'show_shebao_crawl_form.html', locals())
