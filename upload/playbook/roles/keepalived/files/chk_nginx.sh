#!/bin/bash
A=`ps -C nginx --no-header |wc -l`                 ## 查看是否有 nginx进程 把值赋给变量A   
if [ $A -eq 0 ];then                               ## 如果没有进程值得为 零  
     	 /app/test/nginx-master/sbin/nginx  
      sleep 3  
      if [ `ps -C nginx --no-header |wc -l` -eq 0 ];then  
            killall keepalived                     ## 则结束 keepalived 进程  
      fi  
fi
