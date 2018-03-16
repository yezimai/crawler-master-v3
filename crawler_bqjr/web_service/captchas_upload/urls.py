# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^upload_file/?$', views.upload_captcha),  # 上传验证码
    url(r'^show_captcha/?$', views.show_captcha),  # 显示验证码
    url(r'^verify_captcha/?$', views.verify_captcha, name="verify_captcha"),  # 提交验证码
]
