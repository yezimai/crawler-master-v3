# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^get_proxy/?$', views.get_one_proxy, name="get_proxy"),  # 获取代理
    url(r'^get_mobile_phone/?$', views.get_mobile_phone, name="get_mobile_phone"),  # 获取
]
