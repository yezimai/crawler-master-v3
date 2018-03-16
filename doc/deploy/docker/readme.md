# 说明
# 利用docker部署基于centos7的爬虫及web项目

1.安装docker:
    # 更换yum源
    mv ./google.repo /etc/yum.repos.d/google.repo
    mv /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.backup
    curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
    # 安装docker
    yum update && yum install -y docker
    ## 如果出现Couldn't resolve host 'mirrors.aliyun.com 修改dns：
    vi /etc/sysconfig/network-scripts/ifcfg-？？？
    文末添加
    DNS1=8.8.8.8
    DNS2=8.8.4.4 即可
    # 配置加速器：curl -sSL https://get.daocloud.io/daotools/set_mirror.sh | sh -s http://605d6fda.m.daocloud.io
    systemctl start docker.service
    
2.安装docker-compose：
    curl -L https://get.daocloud.io/docker/compose/releases/download/1.16.1/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    chmod a+x /usr/local/bin/docker-compose

3.准备：
    mkdir -p /home/work/
    将项目代码及相关文件放置/home/work/目录下
    将打包好的镜像文件放置该目录下
    加载镜像文件：docker load -i driver-python36-1.tar
    $PWD:/home/work/
    目录结构如下：
        -driver-python36-1.tar
        -start.sh
        -stop.sh
        -docker-web.yml
        -docker-common.yml
        -crawler_bqjr/
        -spider/
            -docker-ecommerce-spider.yml
            -docker-xuexin-spider.yml
            
4.运行：
    chmod +x ./start.sh
    ./start.sh

5.检查运行情况：
    docker-compose ps
    docker ps
    docker logs CONTAINER_ID
    docker exec -it IMAGE_ID /bin/bash
    tail -f ./crawler_bqjr/crawler_bqjr/log/crawler.log


注意：
    1.修改./crawler_bqjr/data_storage/db_settings.py中ssdb和mongodb配置
    2.修改./crawler_bqjr/crawler_bqjr/settings.py中常量WEB_SERVICE_HOST,DO_NOTHING_URL的值
    3.为./crawler_bqjr/web_service/nginx/uwsgi.sock ./crawler_bqjr/crawler_bqjr/browsers/phantomJS/phantomjs和
        ./crawler_bqjr/crawler_bqjr/browsers/chrome/chromedirver添加可执行权限
