# -*- coding:utf-8 -*-
from fabric.api import *
from fabric.colors import *
import time

env.roledefs = {
    'role': ['bqadm@10.41.1.168:10022',]
}
environment = 'prod'
env.user = 'bqadm'
env.password ='dehiqHPQRXY4'


@roles('role')
def clone_code():
    print(green('克隆代码。'))
    run('cd /data/git_source && rm -rf litb_grab')
    run('cd /data/git_source && git clone git@10.89.0.167:wzd/crawler.git')
    print(green('克隆完成。'))

@roles('role')
def pull_code_from_git():
    print(green('拉取代码。'))
    run('cd /data/git_source/crawler && git pull')
    print(green('拉取完成。'))

# copy 代码
@roles('role')
def deploy_code():
    pull_code_from_git()
    print(green('部署代码文件'))
    run('/bin/cp -rf /data/git_source/* /data/code_source/')
    run('cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/browsers && chmod -R 777 *')
    print(green('部署deploy文件'))
    run('/bin/cp -rf /data/code_source/crawler/doc/deploy/* /data/deploy/')
    print(green('web_service setting 修改'))
    run('''cd /data/code_source/crawler/crawler_bqjr/web_service/web_service && rm -f settings.py''')
    run('''cp -f /data/deploy/docker/django/settings/webservice_settings.py /data/code_source/crawler/crawler_bqjr/web_service/web_service/settings.py''')

    print(green('bqjr_crawler setting 修改'))
    run('''cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr && rm -f settings.py''')
    run('''cp -f /data/deploy/docker/django/settings/crawler_settings.py /data/code_source/crawler/crawler_bqjr/crawler_bqjr/settings.py''')
    print(green('data_storage setting 修改'))
    run('''cd /data/code_source/crawler/crawler_bqjr/data_storage && rm -f db_settings.py''')
    run('''cp -f /data/deploy/docker/django/settings/db_storage_db_settings.py /data/code_source/crawler/crawler_bqjr/data_storage/db_settings.py''')

    print(green('秘钥修改'))
    run('''cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/pipelines && sed -i "s/zhegemiyaobeininadaoyemeiyouyong/zhegemiyaocaishizhenzhengyouyong/g" base.py''')

@roles('role')
def restart_web():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/django/ && /usr/local/bin/docker-compose -f docker-web.yml down''')
        run('''cd /data/deploy/docker/django/ && /usr/local/bin/docker-compose -f docker-web.yml up -d''')
        time.sleep(2)
        run('''cd /data/tmp/ && chmod 777 *''')
        print(green('重启web完成'))

@roles('role')
def restart_mysql():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-mysql.yml down''')
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-mysql.yml up -d''')
        print(green('重启mysql完成'))

@roles('role')
def restart_ssdb():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-ssdb.yml down''')
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-ssdb.yml up -d''')
        print(green('重启ssdb完成'))

@roles('role')
def restart_ssdb_admin():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-ssdb-admin.yml down''')
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-ssdb-admin.yml up -d''')
        print(green('重启ssdb-admin完成'))

@roles('role')
def restart_mongo():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-mongo.yml down''')
        run('''cd /data/deploy/docker/common/ && /usr/local/bin/docker-compose -f docker-mongo.yml up -d''')
        print(green('重启mongo完成'))

@roles('role')
def restart_spider_zhengxin():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-zhengxin-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-zhengxin-spider.yml up -d''')
        print(green('重启zhengxin-spider完成'))

@roles('role')
def restart_spider_communications():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-communications-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-communications-spider.yml up -d''')
        print(green('重启communications-spider完成'))
@roles('role')
def restart_spider_mobilebrand():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-mobilebrand-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-mobilebrand-spider.yml up -d''')
        print(green('重启mobilebrand-spider完成'))
@roles('role')
def restart_spider_ecommerce():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-ecommerce-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-ecommerce-spider.yml up -d''')
        print(green('重启ecommerce-spider完成'))

@roles('role')
def restart_spider_xuexin():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-xuexin-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-xuexin-spider.yml up -d''')
        print(green('重启xuexin-spider完成'))


@roles('role')
def restart_spider_all():
    with settings(warn_only=True):
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-zhengxin-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-zhengxin-spider.yml up -d''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-communications-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-communications-spider.yml up -d''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-mobilebrand-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-mobilebrand-spider.yml up -d''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-ecommerce-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-ecommerce-spider.yml up -d''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-xuexin-spider.yml down''')
        run('''cd /data/deploy/docker/spider/ && /usr/local/bin/docker-compose -f docker-xuexin-spider.yml up -d''')
        print(green('重启所有spiders完成'))

