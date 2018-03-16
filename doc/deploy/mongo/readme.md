# 说明
## mongodb 做简单的两台机器主从配置，主机只做写入，从机只做查询与自动备份
-
    1  wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-rhel70-3.2.6.tgz 下载
    2  tar –zxvf mongodb-linux-x86_64-2.0.1.tar 解压
    3  创建data，log 目录
    4  创建mongodb.conf 配置
    --
fork=true
port = 27017
dbpath = /root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/data
logpath = /root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/logs/server1.log
logappend = true
master= true { slave= tue source=主机ip}
    5   创建服务 vim /lib/systemd/system/mongodb.service
    --
[Unit]
Description=mongodb
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=forking
ExecStart=/root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/bin/mongod --config /root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/bin/mongodb.conf
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/bin/mongod --shutdown --config /root/mongo/mongodb-linux-x86_64-rhel70-3.2.6/bin/mongodb.conf
PrivateTmp=true

[Install]
WantedBy=multi-user.target

    6   启动服务  systemctl stop firewalld.service & systemctl start mongodb.service
                  systemctl disable firewalld.service & systemctl enable mongodb.service




## ssdb 安装
wget --no-check-certificate https://github.com/ideawu/ssdb/archive/master.zip
unzip master
cd ssdb-master
make && make install
cp ./tools/ssdb.sh /etc/init.d/ssdb
--
>
  configs=/data/ssdb_data/test/ssdb.conf

chkconfig --add ssdb
chkconfig ssdb on

docker exec -it docker_mongo-master_1 /bin/bash
mongo
use admin
db.createUser({user:"bqjr_admin",pwd:"YmFpcWlhbmppbnJvbmc=",roles:[{role:"userAdminAnyDatabase", db: "admin" }]} )
db.auth('bqjr_admin','YmFpcWlhbmppbnJvbmc=')
use ecommerce
db.createUser({user:"user_dianshang_db",pwd:"yigeanquandemima",roles:[{role:"readWrite", db: "ecommerce" }]} )
use communications
db.createUser({user:"operator_db_account",pwd:"woshibuzhidao",roles:[{role:"readWrite", db: "communications" }]} )
use company
db.createUser({user:"company_user",pwd:"123456",roles:[{role:"readWrite", db: "company" }]} )
use 5xian1jin
db.createUser({user:"shebaogongjijin",pwd:"kongpabunengshuoo",roles:[{role:"readWrite", db: "5xian1jin" }]} )
use shixin
db.createUser({user:"shixin_main_user",pwd:"bunenggaosuni",roles:[{role:"readWrite", db: "shixin" }]} )
use wenshu
db.createUser({user:"user_wenshu",pwd:"pawenshu",roles:[{role:"readWrite", db: "wenshu" }]} )
use zhengxin
db.createUser({user:"zx_db_user",pwd:"xiangyixiang",roles:[{role:"readWrite", db: "zhengxin" }]} )
use shop
db.createUser({user:"shop_user",pwd:"123456",roles:[{role:"readWrite", db: "shop" }]} )
use proxy_pool
db.createUser({user:"proxy_user",pwd:"123456",roles:[{role:"readWrite", db: "proxy_pool" }]} )
use mobile_brand
db.createUser({user:"mobile_brand_user",pwd:"123456",roles:[{role:"readWrite", db: "mobile_brand" }]} )
use xuexin
db.createUser({user:"userinfo_xuexin_user",pwd:"mimahaoduoo",roles:[{role:"readWrite", db: "xuexin" }]} )
use bank
db.createUser({user:"mongo_bank_user",pwd:"yaobaohuyonghuyinsi",roles:[{role:"readWrite", db: "bank" }]} )
use email_bill
db.createUser({user:"mongo_user_for_emailbill",pwd:"youyaoxiangyigemima",roles:[{role:"readWrite", db: "email_bill" }]} )

