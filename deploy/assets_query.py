#! /usr/bin/env python
# -*- coding: utf-8 -*-
# !/usr/bin/env python
# _#_ coding:utf-8 _*_
from .models import Servers
from .models import  Ansible_Inventory
import logging
logger=logging.getLogger('django.assets')


class AssetsSource(object):
    def __init__(self):
        super(AssetsSource, self).__init__()

    def serverList(self):
        serverList = []
        for assets in Servers.objects.all():
            try:
                service = assets.service
            except:
                service = '未知'
            try:
                project = assets.project
            except:
                project = '未知'

            serverList.append(
                {"id": assets.id, "ip": assets.ip, 'project': project, 'service': service})

        return serverList

    def queryAssetsByIp(self, ipList):
        sList = []
        resource = []
        for ip in ipList:
            data = {}
            server = Servers.objects.filter(ip=ip).count()
            if server > 0:
                try:
                    server_assets = Servers.objects.get(ip=ip)
                    sList.append(server_assets.ip)
                    data["ip"] = server_assets.ip
                    if server_assets.port:  data["port"] = int(server_assets.port)
                    data["username"] = server_assets.username
                    data["sudo_passwd"] = server_assets.sudo_passwd
                    if not server_assets.keyfile: data["password"] = server_assets.passwd
                except Exception, ex:
                    logger.warn(msg="server_id:{assets}, error:{ex}".format(assets=server_assets.id, ex=ex))
                if server_assets.host_vars:
                    try:
                        for k, v in eval(server_assets.assets.host_vars).items():
                            if k not in ["ip", "port", "username", "password", "ip"]: data[k] = v
                    except Exception, ex:
                        logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=server_assets.assets.id, ex=ex))

            resource.append(data)
        return sList, resource

    def custom(self, serverList):
        assetsList = []
        for server in serverList:
            try:
                assetsList.append(Servers.objects.select_related().get(id=server))
            except:
                pass
        return self.source(assetsList)

    def group(self, group):
        assetsList = Servers.objects.select_related().filter(group=group)
        return self.source(assetsList)

    def service(self, business):
        assetsList = Servers.objects.select_related().filter(service=business)
        return self.source(assetsList)

    def source(self, assetsList):
        sList = []
        resource = []
        for assets in assetsList:
            data = {}

            try:
                sList.append(assets.ip)
                data["ip"] = assets.ip
                if assets.port: data["port"] = int(assets.port)
                data["username"] = assets.username
                data["sudo_passwd"] = assets.sudo_passwd
                # if assets.server_asset.keyfile == 0: data["password"] = assets.server_asset.passwd
                data["password"] = assets.passwd
            except Exception, ex:
                logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id, ex=ex))

            if assets.host_vars:
                try:
                    for k, v in eval(assets.host_vars).items():
                        if k not in ["ip", "port", "username", "password", "ip"]: data[k] = v
                except Exception, ex:
                    logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id, ex=ex))
            resource.append(data)
        return sList, resource

    def inventory(self, inventory):
        sList = []
        resource = {}
        groups = ''
        try:
            inventory = Ansible_Inventory.objects.get(id=inventory)
        except Exception, ex:
            logger.warn(msg="资产组查询失败：{id}".format(id=inventory, ex=ex))
        for ds in inventory.inventory_group.all():
            resource[ds.group] = {}
            hosts = []
            for ser in ds.inventory_server.all():
                assets = Servers.objects.get(id=ser.server)
                data = {}
                try:
                    serverIp = assets.ip
                    data["ip"] = serverIp
                    if assets.port: data["port"] = int(assets.port)
                    data["username"] = assets.username
                    data["sudo_passwd"] = assets.sudo_passwd
                    data["password"] = assets.passwd
                    if serverIp not in sList: sList.append(serverIp)
                except Exception, ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id, ex=ex))

                if assets.host_vars:
                    try:
                        for k, v in eval(assets.host_vars).items():
                            if k not in ["ip", "port", "username", "password", "ip"]: data[k] = v
                    except Exception, ex:
                        logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id, ex=ex))

                hosts.append(data)
            resource[ds.group_name]['hosts'] = hosts
            groups += ds.group_name + ','
            try:
                if ds.ext_vars: resource[ds.group_name]['vars'] = eval(ds.ext_vars)
            except Exception, ex:
                logger.warn(msg="资产组变量转换失败: {id} {ex}".format(id=inventory, ex=ex))
                resource[ds.group_name]['vars'] = None
        return sList, resource, groups