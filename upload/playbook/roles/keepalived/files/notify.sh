#!/bin/bash
# Author: MageEdu<linuxedu@foxmail.com>
# description: An exampleof notify script
# 
vip=123.6.32.191
contact='caogq@19pay.com.cn xiangzw@19pay.com.cn wutb@19e.com.cn xiejun@19pay.com.cn'
notify() {
mailsubject="虚商系统告警--`date '+%F %H:%M:%S'`"
mailbody="`date '+%F %H:%M:%S'`: 警告，$vip 负载均衡主备发生变化,请注意检查系统 `hostname` changed to be $1 "
echo $mailbody | mail -s "$mailsubject"  $contact
}
case "$1" in
master)
notify master
#/etc/rc.d/init.d/nginx restart （当运行脚本时参数为master时重启nginx服务）
exit 0
;;
backup)
notify backup
#/etc/rc.d/init.d/nginx restop （当运行脚本时参数为backup时重启nginx服务）
exit 0
;;
fault)
notify fault
#/etc/rc.d/init.d/nginx stop
exit 0
;;
*)
echo 'Usage: `basename $0`{master|backup|fault}'
exit 1
;;
esac