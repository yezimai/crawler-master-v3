# coding:utf-8
from __future__ import unicode_literals

from django.db import models


# Create your models here.


class ZhengXinUserDB(models.Model):
    customerId = models.CharField(verbose_name='ID', blank=False, null=False, max_length=64, db_column='customer_id')
    username = models.CharField(verbose_name='用户名', blank=False, null=False, max_length=64, db_column='username')
    password = models.CharField(verbose_name='用户密码', blank=False, null=False, max_length=32, db_column='password')
    pubDate = models.DateTimeField(verbose_name='创建时间', db_column='pub_date', max_length=0, auto_now=True)

    def __str__(self):
        return str(self.username)

    class Meta:
        ordering = ['-pk']
        db_table = 'zhengxin_user_login_db'
        verbose_name = 'zhengxin_user'
        verbose_name_plural = 'zhengxin_users'
