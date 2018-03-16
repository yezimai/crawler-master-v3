# 说明 mongo申请NUB热备并在10.89.1.54下/data/lost+found/dump_168 做crontab备份如下：
50 1 * * *  /usr/local/mongodb/bin/mongodump --host 10.41.1.168 --port 27017 --username userinfo_xuexin_user --password mimahaoduoo --db xuexin --out /data/lost+found/dump_168 >> /data/lost+found/cron.log 2>&1
50 1 * * *  /usr/local/mongodb/bin/mongodump --host 10.41.1.168 --port 27017 --username mobile_brand_user --password 123456 --db mobile_brand --out /data/lost+found/dump_168 >> /data/lost+found/cron.log 2>&1
50 1 * * *  /usr/local/mongodb/bin/mongodump --host 10.41.1.168 --port 27017 --username zx_db_user --password xiangyixiang --db zhengxin --out /data/lost+found/dump_168 >> /data/lost+found/cron.log 2>&1
50 1 * * *  /usr/local/mongodb/bin/mongodump --host 10.41.1.168 --port 27017 --username operator_db_account --password woshibuzhidao --db communications --out /data/lost+found/dump_168 >> /data/lost+found/cron.log 2>&1
50 1 * * *  /usr/local/mongodb/bin/mongodump --host 10.41.1.168 --port 27017 --username user_dianshang_db --password yigeanquandemima --db ecommerce --out /data/lost+found/dump_168 >> /data/lost+found/cron.log 2>&1


docker exec -it common_mongo-master_1 /bin/bash
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
