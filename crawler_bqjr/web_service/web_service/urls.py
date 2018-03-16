"""web_service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
# from django.contrib import admin

from captchas_upload.views import recognize_captcha
from account_spider_interface.views import do_nothing, access_token
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.views import static


urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    # url(r'^captchas_upload/', include('captchas_upload.urls')),
    url(r'^account_spider/', include('account_spider_interface.urls')),
    url(r'^rest_api/', include('rest_api.urls')),
    # url(r'^recognize_captcha/?$', recognize_captcha),  # 识别验证码
    url(r'^$', do_nothing),  # 用于scrapy没有爬取任务时的空爬
    url(r"^accounts/login/$", auth_views.LoginView.as_view()),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),  # oauth2管理页面
    url(r'^access_token/', access_token),  # access token获取地址
]

if not settings.DEBUG:
    urlpatterns.append(url(r'^static/(?P<path>.*)$', static.serve, {'document_root': settings.STATIC_ROOT, }))
