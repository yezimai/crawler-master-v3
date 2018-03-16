# -*- coding:utf-8 -*-
# 建立在ssh互信配置下
from fabric.api import *
from fabric.colors import *
import time

env.roledefs = {
    #'role': ['weblogic@10.89.1.100:22','weblogic@10.89.1.101:22']
    'role': ['bqadm@172.16.8.31:10022','bqadm@172.16.8.32:10022']
}
if 'weblogic' in env.roledefs['role'][0]:
    environment = '测试'
else:
    environment = '生产'


@roles('role')
def clone_code():
    print(green('克隆代码。'))
    run('cd /data/git_source && rm -rf crawler')
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
    with settings(warn_only=True):
        print(green('%s环境：部署代码文件' % environment))
        run('/bin/cp -rf /data/git_source/* /data/code_source/')
        run('cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/browsers && chmod -R 777 *')
        if environment == '生产':
            print(green('%s环境：constans.py 修改' % environment))
            run('''cd /data/code_source/crawler/crawler_bqjr/ && sed -i "s/10.89.1.99/172.16.8.30/g" constans.py''')
        else:
            print(green('秘钥修改'))
            run('''cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/pipelines && sed -i "s/zhegemiyaobeininadaoyemeiyouyong/zhegemiyaocaishizhenzhengyouyong/g" base.py''')

def restart_web():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/web/web.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/web && kubectl delete -f web.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/web && kubectl create -f web.yaml')

def restart_mysql():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/common/mysql.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl delete -f mysql.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl create -f mysql.yaml')

def restart_mongo():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/common/mongo.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl delete -f mongo.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/web && kubectl create -f mongo.yaml')

def restart_ssdb():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/common/ssdb.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl delete -f ssdb.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl create -f ssdb.yaml')

def restart_ssdbadmin():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/common/ssdb-admin.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl delete -f ssdb-admin.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl create -f ssdb-admin.yaml')

def restart_rabbitmq():
    with settings(warn_only=True):
        if environment == '测试':
            local('''sed -i"s/10.89.1.99/172.16.8.30/g" /data/code_source/crawler/doc/deploy/k8s/common/rabbitmq.yaml''')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl delete -f rabbitmq.yaml')
        local('cd /data/code_source/crawler/doc/deploy/k8s/common && kubectl create -f rabbitmq.yaml')
        print(green('请进入mq容器运行/data/code_source/crawler/doc/deploy/k8s/common/rabbitmq.conf中的命令' ))