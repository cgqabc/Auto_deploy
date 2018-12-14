# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


# Create your models here.

class Servers(models.Model):

    name = models.CharField(max_length=100, verbose_name='资产名称')
    ip = models.GenericIPAddressField(unique=True, verbose_name='IP')
    hosted_on = models.ForeignKey('self', related_name='hosted_on_server',
                                  blank=True, null=True, verbose_name="宿主机")
    model = models.CharField(max_length=128, null=True, blank=True, verbose_name='服务器型号')
    hostname = models.CharField(max_length=100, blank=True, null=True, verbose_name="主机名")
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="用户名")
    passwd = models.CharField(max_length=100, blank=True, null=True, verbose_name="密码")
    sudo_passwd = models.CharField(max_length=100, blank=True, null=True, verbose_name="sudo密码")
    host_vars = models.CharField(max_length=100, blank=True, null=True, verbose_name="主机变量")
    keyfile = models.CharField(max_length=100, blank=True, null=True,
                               verbose_name="密钥路径")
    port = models.DecimalField(max_digits=6, decimal_places=0, blank=True, null=True, verbose_name="端口")
    line = models.CharField(max_length=100, blank=True, null=True, verbose_name='线路')

    disk_total = models.CharField(max_length=100, blank=True, null=True, verbose_name='磁盘容量')
    cpu_rpm = models.CharField(max_length=100, blank=True, null=True, verbose_name='配置')

    os_type = models.CharField(max_length=64, blank=True, null=True, verbose_name="操作系统")

    project = models.CharField(max_length=100,blank=True, null=True, verbose_name='所属项目')
    service = models.CharField(max_length=100,blank=True, null=True, verbose_name='所属服务')
    group = models.CharField(max_length=100,blank=True, null=True, verbose_name='分组')
    site = models.CharField(blank=True, null=True, max_length=100, verbose_name='位置')
    memo = models.TextField(null=True, blank=True, verbose_name='备注')
    c_time = models.DateTimeField(auto_now_add=True, verbose_name='创建日期')
    m_time = models.DateTimeField(auto_now=True, verbose_name='更新日期')

    def __unicode__(self):
        return "{0}|{1}".format(self.name,self.ip)

    class Meta:
        verbose_name = '服务器表'
        verbose_name_plural = '服务器表'
        ordering = ['-c_time']


class Projects(models.Model):

    parent_unit = models.ForeignKey('self', blank=True, null=True,
                                    related_name='parent_level',verbose_name="上级项目")
    name = models.CharField('项目', max_length=64, unique=True)
    memo = models.CharField('说明', max_length=64, blank=True, null=True)
    manager = models.CharField('负责人', max_length=64, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '总项目表'
        verbose_name_plural = "总项目表"


class Services(models.Model):
    project = models.ForeignKey('Projects', related_name='services',
                                on_delete=models.CASCADE,verbose_name="所属项目")
    service_name = models.CharField(max_length=100,verbose_name="服务名称")
    memo = models.CharField('说明', max_length=64, blank=True, null=True)
    manager = models.CharField('负责人', max_length=64, blank=True, null=True)

    def __unicode__(self):
        return self.service_name

    class Meta:
        unique_together = (("project", "service_name"))
        verbose_name = '服务列表'
        verbose_name_plural = '服务列表'

class Groups(models.Model):
    name = models.CharField('组名', max_length=64, unique=True)
    memo = models.CharField('说明', max_length=64, blank=True, null=True)
    manager = models.CharField('负责人', max_length=64, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '分组表'
        verbose_name_plural = "分组表"

class Ansible_Inventory(models.Model):
    name = models.CharField(unique=True, max_length=100, verbose_name="名称")
    desc = models.CharField(max_length=200, verbose_name="功能描述")
    create_user = models.CharField(max_length=200, verbose_name="创建人")
    create_time = models.DateField(auto_now_add=True, blank=True, null=True, verbose_name="创建时间")

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "动态资产表"
        verbose_name_plural = "动态资产表"


class Ansible_Group(models.Model):
    inventory = models.ForeignKey(Ansible_Inventory, related_name="inventory_group",
                                  on_delete=models.CASCADE, verbose_name="资产名称")
    group = models.CharField(max_length=100, unique=True, verbose_name="组名")
    ext_vars = models.TextField(verbose_name='组外部变量', blank=True, null=True)

    def __unicode__(self):
        return self.group

    class Meta:
        verbose_name = "动态资产分组表"
        verbose_name_plural = "动态资产分组表"


class Ansible_Server(models.Model):
    group = models.ForeignKey(Ansible_Group, related_name="inventory_server",
                              on_delete=models.CASCADE, verbose_name="资产组")
    # server = models.CharField(max_length=100,verbose_name="服务器")
    server = models.SmallIntegerField(verbose_name="服务器", default=None)

    def __unicode__(self):
        # return self.server.manage_ip
        return str(self.id)

    class Meta:
        unique_together = ["group", "server"]
        verbose_name = "动态资产组成员表"
        verbose_name_plural = "动态资产组内成员表"



class Ansible_CallBack_Model_Result(models.Model):
    logId = models.ForeignKey('Log_Ansible_Model', related_name="ansible_model_log")
    content = models.TextField(verbose_name='输出内容', blank=True, null=True)

    def __unicode__(self):
        return str(self.logId)


class Ansible_CallBack_PlayBook_Result(models.Model):
    logId = models.ForeignKey('Log_Ansible_Playbook', related_name="ansible_playbook_log")
    content = models.TextField(verbose_name='输出内容', blank=True, null=True)

    def __unicode__(self):
        return str(self.logId)


class Log_Ansible_Model(models.Model):
    ans_user = models.CharField(max_length=50, verbose_name='使用用户', default=None)
    ans_model = models.CharField(max_length=100, verbose_name='模块名称', default=None)
    ans_args = models.CharField(max_length=500, blank=True, null=True, verbose_name='模块参数', default=None)
    ans_server = models.TextField(verbose_name='服务器', default=None)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='执行时间')

    def __unicode__(self):
        return "{0}|{1}".format(self.ans_model, self.create_time)

    class Meta:
        verbose_name = 'Ansible模块执行记录表'
        verbose_name_plural = 'Ansible模块执行记录表'


class Log_Ansible_Playbook(models.Model):
    ans_id = models.IntegerField(verbose_name='id', blank=True, null=True, default=None)
    ans_user = models.CharField(max_length=50, verbose_name='使用用户', default=None)
    ans_name = models.CharField(max_length=100, verbose_name='模块名称', default=None)
    ans_content = models.CharField(max_length=100, default=None)
    ans_server = models.TextField(verbose_name='服务器', default=None)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='执行时间')

    def __unicode__(self):
        return str(self.create_time)

    class Meta:
        verbose_name = 'Ansible剧本操作记录表'
        verbose_name_plural = 'Ansible剧本操作记录表'


class Ansible_Script(models.Model):
    script_name = models.CharField(max_length=50, verbose_name='脚本名称', unique=True)
    script_uuid = models.CharField(max_length=50, verbose_name='唯一id', blank=True, null=True)
    script_server = models.TextField(verbose_name='目标机器', blank=True, null=True)
    script_file = models.FileField(upload_to='./script/', verbose_name='脚本路径')
    script_args = models.TextField(blank=True, null=True, verbose_name='脚本参数')
    script_service = models.SmallIntegerField(verbose_name='授权业务', blank=True, null=True)
    script_group = models.SmallIntegerField(verbose_name='授权组', blank=True, null=True)
    script_type = models.CharField(max_length=50, verbose_name='脚本类型', blank=True, null=True)

    def __unicode__(self):
        return self.script_name

    class Meta:
        verbose_name = 'Ansible脚本配置表'
        verbose_name_plural = 'Ansible脚本配置表'


class Ansible_Playbook(models.Model):
    type = (
        ('service', u'service'),
        ('group', u'group'),
        ('custom', u'custom'),
    )
    playbook_name = models.CharField(max_length=50, verbose_name='剧本名称', unique=True)
    playbook_desc = models.CharField(max_length=200, verbose_name='功能描述', blank=True, null=True)
    playbook_vars = models.TextField(verbose_name='模块参数', blank=True, null=True)
    playbook_uuid = models.CharField(max_length=50, verbose_name='唯一id')
    playbook_server_model = models.CharField(choices=type, verbose_name='服务器选择类型', max_length=10, blank=True, null=True)
    playbook_server_value = models.SmallIntegerField(verbose_name='服务器选择类型值', blank=True, null=True)
    playbook_file = models.FileField(upload_to='./playbook/', verbose_name='剧本路径')
    playbook_auth_group = models.SmallIntegerField(verbose_name='授权组', blank=True, null=True)
    playbook_auth_user = models.SmallIntegerField(verbose_name='授权用户', blank=True, null=True, )
    playbook_type = models.SmallIntegerField(verbose_name='剧本类型', blank=True, null=True, default=0)

    def __unicode__(self):
        return self.playbook_name

    class Meta:
        verbose_name = 'Ansible剧本配置表'
        verbose_name_plural = 'Ansible剧本配置表'


class LogFileOps(models.Model):
    opstype = models.CharField(max_length=20,choices=(('up','分发'),('down','下载')),
                               verbose_name="操作类型",default='up')
    srcfile = models.CharField(max_length=100,verbose_name="源文件路径",blank=True,null=True,default=None)
    filepath = models.CharField(max_length=100,verbose_name="目标文件路径",blank=True,null=True,default=None)
    server = models.CharField(max_length=100,verbose_name="目标服务器")
    content = models.CharField(max_length=100,blank=True,null=True,verbose_name="备注")
    user = models.CharField(max_length=50, verbose_name='执行者', blank=True,null=True,default=None)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='执行时间')

    def __unicode__(self):
        return "{}:{}".format(self.opstype,self.create_time)

    class Meta:
        verbose_name = "文件操作记录表"


class CommonMethods(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称",unique=True,)
    desc = models.CharField(max_length=100, verbose_name="功能描述", blank=True, null=True, default=None)
    method = models.CharField(max_length=20,choices=(('model','模块'),(('scripts','脚本')),
                                                     ('playbook','剧本')),
                               verbose_name="使用方法",default='playbook')
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name="模块或角色")
    vars = models.CharField(max_length=100, blank=True, null=True, verbose_name="参数")
    filePath = models.CharField(max_length=100, blank=True, null=True, verbose_name="文件路径")
    user = models.CharField(max_length=50, verbose_name='添加人员', blank=True, null=True, default=None)
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='添加时间')
    last_run_time = models.DateTimeField(blank=True, null=True, verbose_name='上次执行时间')
    last_run_result = models.CharField(max_length=100, blank=True, null=True, verbose_name="上次执行结果")
    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "常用方法表"