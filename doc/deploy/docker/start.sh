#!/bin/bash

# 先开启公共服务(ssdb,mongo等)
# docker-compose -f docker-common.yml up -d

# 开启web服务
docker-compose -f docker-web.yml up -d

# 开启爬虫
for file in ./spider/*
do
    if [ "${file##*.}"x = "yml"x ]
    then
        echo [+]开启爬虫${file}中...
        docker-compose -f $file up -d
        echo [+]开启成功.
    fi
done

docker-compose -f docker-ecommerce-spider.yml up -d

# 为phantomjs,chromedriver,uwsgi.sock添加可执行权限
chmod 777 ./crawler_bqjr/crawler_bqjr/browsers/phantomJS/phantomjs
chmod 777 ./crawler_bqjr/crawler_bqjr/browsers/chrome/chromedriver
chmod 777 ./crawler_bqjr/web_service/nginx/uwsgi.sock