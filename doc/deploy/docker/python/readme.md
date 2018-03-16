# 说明
# python:爬虫及web运行的python环境

1.配置docker运行环境：
    # 更换yum源
    sudo mv ./google.repo /etc/yum.repos.d/google.repo
    sudo mv /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.backup
    sudo curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
    # 安装docker
    sudo yum update && yum install -y docker
    # 配置加速器：curl -sSL https://get.daocloud.io/daotools/set_mirror.sh | sh -s http://605d6fda.m.daocloud.io
    systemctl start docker.service

2.获取centos docker镜像:
    docker pull docker.io/centos


3.准备相关文件：
    编译文件Dockerfile
    google源文件google.repo
    python3.6安装包
    chromedriver执行文件
    requirements.txt python第三方包
    目录结构如下：
        -chromedriver
        -Dockerfile
        -google.repo
        -python36
        -requirements.txt


4.编译生成镜像：
    docker build -t driver-python36 .

5.打包镜像文件：
    docker save -o driver-python36-1.tar driver-python36
