FROM docker.io/centos
RUN mkdir /work/
WORKDIR /work/
ADD ./ ./
# 更换yum源
RUN mv ./google.repo /etc/yum.repos.d/google.repo
RUN mv /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.backup
RUN mv ./CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo
# 安装必要的包
RUN yum update -y && yum install -y openssl openssl-devel zlib zlib-devel wget vim unzip curl make gcc bzip2 readline-devel sqlite-devel
WORKDIR /work/python36
# 编译安装python36
RUN ./configure
RUN make && make install
WORKDIR /work/
ADD ./requirements.txt ./
# 安装scrapy前需要先安装zope和Twisted
RUN wget http://pypi.python.org/packages/source/z/zope.interface/zope.interface-4.0.1.tar.gz
RUN tar -xvf zope.interface-4.0.1.tar.gz
WORKDIR ./zope.interface-4.0.1
RUN python3 setup.py install
WORKDIR /work/
RUN wget https://pypi.python.org/packages/source/T/Twisted/Twisted-15.5.0.tar.bz2
RUN tar -xjvf Twisted-15.5.0.tar.bz2
WORKDIR ./Twisted-15.5.0
RUN python3 setup3.py install
RUN pip3 install scrapy
# 安装python第三方包
RUN pip3 install -r ./requirements.txt -i http://pypi.douban.com/simple --trusted-host pypi.douban.com
# 安装google-chrome,xvfb和webdriver
RUN yum install -y google-chrome-stable Xvfb libXfont xorg-x11-fonts*
RUN pip3 install pyvirtualdisplay
WORKDIR /work/
RUN cp ./chromedriver /usr/bin/chromedriver
# 整理
RUN rm -rf ./Tw* && rm -rf zope*
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8