# 系统使用kubernets容器管理技术部署
## 它是一个开源的平台，可以实现容器集群的自动化部署、自动扩缩容、维护等功能，能够快速部署应用、快速扩展应用、
无缝对接新的应用功能、节省资源，优化硬件资源的使用。以容器（docker）为中心，满足在生产环境中运行应用的常见需求
只要这个应用可以在容器里运行，那么就能很好的运行在Kubernetes上

## Master组件
1、kube-apiserver：用于暴露Kubernetes API。任何的资源请求/调用操作都是通过kube-apiserver提供的接口进行
2、etcd：为Kubernetes提供默认的存储系统，保存所有集群数据，使用时需要为etcd数据提供备份计划。
3、kube-controller-manager：运行管理控制器，节点控制、pod维护pod副本控制、svc与pod的连接控制、sa与token控制
4、kube-scheduler：调度器，监视新创建没有分配到Node的Pod，为Pod选择一个Node。
5、DNS：是一个DNS服务器，能够为 Kubernetes services提供 DNS记录。
6、docker：运行容器

## Node组件
1、kubelet：是主要的节点代理，它会监视已分配给节点的pod。安装Pod所需的volume、下载Pod的Secrets、Pod中运行的 docker、
定期执行容器健康检查、报告pod、node状态、需要时重启pod
2、kube-proxy：通过在主机上维护网络规则并执行连接转发来实现Kubernetes服务抽象。
3、docker：运行容器

## 集群安装、配置


1、所有机器关闭防火墙
systemctl stop firewalld
systemctl disable firewalld

2、所有机器修改yum源为阿里yum源
yum update -y && yum install -y openssl openssl-devel zlib zlib-devel wget vim unzip curl make gcc bzip2 readline-devel sqlite-devel ebtables ethtool sqlite-devel python-devel mysql-devel libffi-devel libxslt-devel gcc
如果有误vi /etc/sysconfig/network-scripts/ifcfg-? 修改dns （或修改/etc/resovle.conf）
DNS1=8.8.8.8
DNS2=8.8.4.4
service network restart

3、所有机器安装docker
yum install docker  （最好是1.12版本 k8s推荐的版本）
systemctl enable docker && systemctl start docker

4、所有机器安装kubeadm, kubelet and kubectl
setenforce 0

cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF


yum install kubelet kubeadm kubectl  (确定版本一致！)
确保
docker info | grep -i cgroup
cat /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
都是 systemd 或 cgourpfs 如果不是 请先改为cgoupfs 再不行再改systemd （此处有bug！！！）

可journalctl -xue | kubelet 查看安装出错

5、准备镜像
镜像下载好 目前https://hub.docker.com/u/alleyj/ 用户有1.7 k8s的初始化所有镜像
下载好后 给镜像重新打tag gcr.io/google_containers/
node机器只需要kube-proxy-amd64:v1.7.5 和pause-amd64:3.0 如果dns不行，需要运行在node还要下载dns镜像
docker pull alleyj/k8s-dns-dnsmasq-nanny-amd64:1.14.4
docker pull alleyj/k8s-dns-kube-dns-amd64:1.14.4
docker pull alleyj/k8s-dns-sidecar-amd64:1.14.4
docker pull alleyj/controller-manager-amd64:v1.7.5
docker pull alleyj/kube-apiserver-amd64:v1.7.5
docker pull alleyj/kube-scheduler-amd64:v1.7.5
docker pull alleyj/kube-proxy-amd64:v1.7.5
docker pull alleyj/kube-discovery-amd64:1.0
docker pull alleyj/dnsmasq-metrics-amd64:1.0
docker pull alleyj/etcd-amd64:3.0.17
docker pull alleyj/exechealthz-amd64:1.2
docker pull alleyj/pause-amd64:3.0

docker tag alleyj/controller-manager-amd64:v1.7.5 grc.io/google_containers/controller-manager-amd64:v1.7.5
docker tag alleyj/kube-apiserver-amd64:v1.7.5 gcr.io/google_containers/kube-apiserver-amd64:v1.7.5
docker tag alleyj/kube-scheduler-amd64:v1.7.5 gcr.io/google_containers/kube-scheduler-amd64:v1.7.5
docker tag alleyj/kube-discovery-amd64:1.0 gcr.io/google_containers/kube-discovery-amd64:1.0
docker tag alleyj/etcd-amd64:3.0.17 gcr.io/google_containers/etcd-amd64:3.0.17
docker tag alleyj/exechealthz-amd64:1.2 gcr.io/google_containers/exechealthz-amd64:1.2
docker tag alleyj/pause-amd64:3.0 gcr.io/google_containers/pause-amd64:3.0
docker tag alleyj/kube-proxy-amd64:v1.7.5 gcr.io/google_containers/kube-proxy-amd64:v1.7.5

6、初始化master
kubeadm init --kubernetes-version=v1.7.5
以下命令执行可为其他用户控制集群
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
从机器以外的机器控制您的集群
scp root@<master ip>:/etc/kubernetes/admin.conf .
kubectl --kubeconfig ./admin.conf get nodes

7、安装网络
本项目选择weavenet 在k8s下common 直接创建之

8、node 加入
kubeadm join --token a1ffee.e9b60d1455019f43 10.89.1.99:6443

9、主机查看node
kubectl get node

10、主机检查所有kube-system pod是否正常  一般有dns不正常 使用k8s下dns配置重新安装即可！


11、ssh互信配置为主机控制其他机器代码等
ssh-keygen -t rsa
ssh-copy-id -i /home/weblogic/.ssh/id_rsa.pub weblogic@10.89.1.100
ssh-copy-id -i /home/weblogic/.ssh/id_rsa.pub weblogic@10.89.1.101
cd /home/weblogic/
chmod 700 .ssh
cd .shh
chmod 600 authorized_keys

12、注意事项
mongo、ssdb、rabbitmq、mysql由于要产生数据将其放在固定的节点机中。
目前学信爬虫会产生图片需要访问，学信deployment与web端deployment放在同一台节点机。

每台节点机器有/data目录
code_source 放运行的代码
git_source 放git源码
pictures 是学信跟web运行的机器上有的
logs 日志下有： crawler爬虫、mongodb（需要提前创建这个目录和log文件）、  ssdb（创建目录）、  web
mongodb 是 mongo所在的机器mongo数据及配置的目录、需要提前创建、放入conf文件
settings 目前用作修改配置文件 之后会弃用
ssdb 是ssdb所在的机器mongo数据及配置的目录、需要提前创建、放入conf文件
rabbitmq 是rabbitmq所在的机器mongo数据及配置的目录、不要提前创建
mysql 是mysql所在的机器mongo数据及配置的目录、不要提前创建


## 使用、控制
kubectl create -f 创建资源
kubectl delete 删除资源
kubectl scale 扩缩资源副本
kubectl describe 查看详情
kubectl logs 日志



认证服务 通过kubelet 以uwsgi服务器的方式 启动在172.16.8.31上， 并在172.16.8.31上启动一个外置的nginx 开放12000 限制ip 通过
/data/tmp/uwsgi_access.sock 通讯。
nginx配置路径/usr/local/nginx/conf/nginx.conf  服务代码路径/data/code_source_oauth/crawler/crawler_bqjr/web_service



项目具体操作说明：
主机172.16.8.30
bqadm    Ob7UsUgzq2lgR6BB
root     A4RAKM8Elb76hewa

节点机172.16.8.31
bqadm    csKBnfa4sSJYQUbj
root     syfznqzLPR9UDTso

节点机172.16.8.32
bqadm    FNuFj29wxXA8CAFv
root     Dtq4tlAoIiyXxKGh


查看佰仟爬虫容器运行状态：
kubectl get po -n bqjr-crawler -o wide
status 为running的是正常的  其他状态均有问题
bqjr-crawler-access-deployment 认证入口服务容器
bqjr-crawler-mongo-deployment mongo服务容器
bqjr-crawler-mysql-deployment mysql服务容器
bqjr-crawler-rabbitmq-deployment rabbitmq服务容器
bqjr-crawler-spider-   各种spider容器
bqjr-crawler-ssdb-deployment ssdb服务容器
bqjr-crawler-ssdbadmin-deployment ssdb界面容器
bqjr-crawler-web-deployment 爬虫界面容器（2个 一个nginx 一个uwsgi）

查看佰仟爬虫服务：
kubectl get svc -n bqjr-crawler -o wide
有 EXTERNAL-IP的service 是对外暴露的
bqjr-crawler-access这个服务没有对外暴露、只在集群内部设集群内ip、 节点机01（172.16.8.31）有外置的nginx服务（系统服务）需
要访问。暴露12000端口以供白名单ip获得access_token后访问爬虫web界面。

更新代码：
cd /data/git_source/crawler && git pull
/bin/cp -rf /data/git_source/* /data/code_source/
cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/browsers && chmod -R 777 *
vim /data/code_source/crawler/crawler_bqjr/constants.py  （修改10.89.1.99为172.16.8.30）

重启方式都是先删除资源、再创建资源。 资源（yaml文件)位置存放在/home/bqadm/crawler_k8s
项目的/doc/deploy/k8s也存放着。 如果需要增加或减少资源可以修改yaml文件中的replicas 数量后重启
重启学信爬虫：kubectl delete -f xuexin.yaml && kubectl create -f xuexin.yaml
重启运营商爬虫：kubectl delete -f communication.yaml && kubectl create -f communication.yaml
重启爬虫web服务：kubectl delete -f web.yaml  &&  kubectl create -f web.yaml
重启征信爬虫：kubectl delete -f zhengxin.yaml  &&  kubectl create -f zhengxin.yaml
重启电商爬虫：kubectl delete -f ecommerce.yaml  && kubectl create -f ecommerce.yaml




10.89.1.54 上的爬虫 是以docker的方式启动的
失信爬虫：docker run --name shixin -d -e LANG=Zn_CN.UTF-8 -e LC_ALL=en_US.utf8 -e PYTHONPATH=/work/crawler_bqjr -v /data/code_source/crawler/crawler_bqjr/:/work/ -v /data/logs/crawler/:/logs/ -v /data/html_data/:/data/html_data/ -v /data/image_data/:/data/image_data/ docker.io/421084068/driver-python36 python3 /work/run_shixin_spiders.py
代理爬虫：docker run --name proxy -d -e LANG=Zn_CN.UTF-8 -e LC_ALL=en_US.utf8 -e PYTHONPATH=/work/crawler_bqjr -v /data/code_source/crawler/crawler_bqjr/:/work/ -v /data/logs/crawler/:/logs/ docker.io/421084068/driver-python36 python3 /work/run_proxy_spiders.py
3C产品爬虫：docker run --name mobilebrand -d -e LANG=Zn_CN.UTF-8 -e LC_ALL=en_US.utf8 -e PYTHONPATH=/work/crawler_bqjr -v /data/code_source/crawler/crawler_bqjr/:/work/ -v /data/logs/crawler/:/logs/ docker.io/421084068/driver-python36 python3 /work/run_mobilebrand_spiders.py

更新代码：先切换root权限  su LGlRmGi6HwFdbAnL
cd /data/git_source/crawler && git pull
/bin/cp -rf /data/git_source/* /data/code_source/
cd /data/code_source/crawler/crawler_bqjr/crawler_bqjr/browsers && chmod -R 777 *
vim /data/code_source/crawler/crawler_bqjr/constants.py 修改为10.89.1.54
之后docker stop shixin && docker start shixin 重启容器

