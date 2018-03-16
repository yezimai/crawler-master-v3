#!/bin/bash

# 先关闭公共服务(ssdb,mongo等)
# docker-compose -f docker-common.yml down

# 关闭web服务
docker-compose -f docker-web.yml down

# 关闭爬虫
for file in ./spider/*
do
    if [ "${file##*.}"x = "yml"x ]
    then
        echo [+]关闭爬虫${file}中...
        docker-compose -f $file down
        echo [+]关闭成功.
    fi
done
