# 10.41.1.168机器说明

目录说明：
git源码存放在/data/git_source
docker容器使用的代码是/data/code_source
部署文件存放在/data/deploy  部署时使用一键部署 fab -f  deploy.py deploy_code 部署代码和部署代码
部署代码的settings 统一在/data/settings 修改后 使用 一键部署自动copy 这里面的到容器使用的代码
！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
！！修改(增加减少配置)了data_storage/db_settings.py 或crawler_bjqr/settings.py或web_service/settings.py 请告知一下！！！
！！修改(增加减少配置)了data_storage/db_settings.py 或crawler_bjqr/settings.py或web_service/settings.py 请告知一下！！！
！！修改(增加减少配置)了data_storage/db_settings.py 或crawler_bjqr/settings.py或web_service/settings.py 请告知一下！！！
！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
日志统一存放在/data/logs
数据库备份及其他备份存放在/data/backup
需要下载的工具存放在/data/tools
uwsgi socket文件存放在/data/tmp
mongo容器挂载目录/data/mongodb
mysql容器挂载目录/data/mysql
ssdb容器挂载目录/data/ssdb
每个爬虫run程序为一个docker容器

端口说明：
mysql 3306       root bqjr2017 / test 123456
mongo 27017
ssdb 8888       bqjr1234567890qwertyuiopasdfghjklzxcvbnm
nginx 80
uwsgi 8000
ssdbadmin 9111   ssdb_user_admin  yigejiandandemima

启动说明：
改了web界面需要重启uwsgi  重启之后/data/tmp 赋权限
改了spider也需要重启相应spider的docker容器
重启文件全在/data/deploy下

重启方式：
部署代码方式: cd /data/ && fab -f  deploy.py deploy_code 部署代码
重启web方式: cd /data/ && fab -f deploy.py restart_web
重启mysql方式: cd /data/ && fab -f deploy.py restart_mysql
重启ssdb方式: cd /data/ && fab -f deploy.py restart_ssdb
重启ssdb-admin方式: cd /data/ && fab -f deploy.py restart_ssdb_admin
重启mongo方式: cd /data/ && fab -f deploy.py restart_mongo
重启 xuexin spider方式：cd /data/ && fab -f deploy.py restart_spider_xuexin
重启 zhengxin spider方式：cd /data/ && fab -f deploy.py restart_spider_zhengxin
重启 ecommerce spider方式：cd /data/ && fab -f deploy.py restart_spider_ecommerce
重启 communications spider方式：cd /data/ && fab -f deploy.py restart_spider_communications
重启 mobiebrand spider方式：cd /data/ && fab -f deploy.py restart_spider_mobiebrand


停止公共服务方式: cd /data/deploy/docker && /usr/local/bin/docker-compose -f docker-common.yml down
启动公共服务方式: cd /data/deploy/docker && /usr/local/bin/docker-compose -f docker-common.yml up -d
启动nginx+uwsgi方式：cd /data/deploy/docker/django && /usr/local/bin/docker-compose -f docker-web.yml up -d
停止nginx+uwsgi方式: cd /data/deploy/docker && /usr/local/bin/docker-compose -f docker-web.yml down
