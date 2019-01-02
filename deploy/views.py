# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import glob
import json
import uuid

import os
import xlrd
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.http import JsonResponse, StreamingHttpResponse, FileResponse
from django.shortcuts import render

from .ansible_api_v2_4 import ANSRunner
from .assets_query import AssetsSource
from .forms import InventoryForm, GroupForm, MoudelForm, ScriptsForm, PlaybookForm, ServersForm, FileDownForm, \
    FileUpForm, CommonForm
from .log_ansible import AnsibleRecord
from .models import (Ansible_Inventory, Ansible_Group, Ansible_Server, Servers,
                     Ansible_Script, Ansible_Playbook, Log_Ansible_Playbook,
                     Log_Ansible_Model, Projects, Services, Groups, LogFileOps, CommonMethods)
# from delivery.models import Project_Config,Project_Number,BusinessUnit
# from cmdb.models import Server_asset,Service_Assets
# from django.contrib.auth.models import Group
from .redis_ops import Redis_pool


# Create your views here.

@login_required()
def asset_batch_import(request):
    if request.method == "POST":
        fileobj = request.FILES.get("batch_import")
        filename = os.path.join(os.getcwd(), 'upload', fileobj.name)
        # if os.path.isdir(os.path.dirname(filename)) is not True:
        if not os.path.exists(os.path.join(os.getcwd(), 'upload')):
            # print("dir not exists,make it")
            os.makedirs(os.path.join(os.getcwd(), 'upload'))
        try:
            with open(filename, 'wb') as f:
                for chunk in fileobj.chunks():
                    f.write(chunk)
        except Exception as e:
            print(e)

        file = xlrd.open_workbook(filename)
        server = file.sheet_by_name("server")
        try:
            for i in range(1, server.nrows):
                data = server.row_values(i)
                defaults = {
                    'name': data[0],
                    'project': data[1],
                    'service': data[2],
                    'ip': data[3],
                    'cpu_rpm': data[4],
                    'disk_total': data[5],
                    'os_type': data[6],
                    'group': data[7],
                    'username': data[8],
                    'passwd': data[9],
                    'sudo_passwd': data[10],
                    'port': int(data[11]) if data[11] else data[11],
                    'keyfile': data[12],
                    'hostname': data[13],
                    'memo': data[14],
                }
                # print json.dumps(defaults,indent=4)
                Servers.objects.update_or_create(ip=data[3], defaults=defaults)
                project = data[1]
                service = data[2]
                group = data[7]
                pp = None
                if project:
                    pp, _ = Projects.objects.update_or_create(name=project,
                                                              defaults={'name': project})
                if pp and service:
                    Services.objects.update_or_create(project=pp, service_name=service,
                                                      defaults={'project': pp,
                                                                'service_name': service})
                if group:
                    Groups.objects.update_or_create(name=group,
                                                    defaults={'name': group})
        except Exception as e:
            message = "导入失败，%s" % e
            data_list = Servers.objects.all()
            # return JsonResponse({'msg': "资产新增失败,%s" % e, "code": 500, })
            return render(request, "deploy/servers_list.html", locals())
        # return JsonResponse({'msg': "资产批量新增成功", "code": 200, })
        data_list = Servers.objects.all()
        message = "导入成功"
        return render(request, "deploy/servers_list.html", locals())


@login_required
def servers_list(request):
    data_list = Servers.objects.all()

    return render(request, "deploy/servers_list.html", locals())


@login_required
def server_add(request):
    if request.method == "GET":
        form = ServersForm()

        return render(request, "deploy/server_add.html", locals())
    else:
        form = ServersForm(request.POST)

        if form.is_valid():
            form.save()
            project = form.cleaned_data.get("project")
            service = form.cleaned_data.get("service")
            group = form.cleaned_data.get("group")
            try:
                pp = None
                if project:
                    pp, _ = Projects.objects.update_or_create(name=project,
                                                              defaults={'name': project})
                if pp and service:
                    Services.objects.update_or_create(project=pp, service_name=service,
                                                      defaults={'project': pp,
                                                                'service_name': service})
                if group:
                    Groups.objects.update_or_create(name=group,
                                                    defaults={'name': group})
            except Exception as ex:
                message = "新增失败，%s" % ex
                return render(request, "deploy/server_add.html", locals())
            message = "新增成功"
            return render(request, "deploy/server_add.html", locals())

        return render(request, "deploy/server_add.html", locals())


@login_required
def server_edit(request, in_id):
    server = Servers.objects.get(id=in_id)
    if request.method == "GET":

        form = ServersForm(instance=server)

        return render(request, "deploy/server_edit.html", locals())
    else:
        form = ServersForm(request.POST, instance=server)

        if form.is_valid():
            form.save()
            project = form.cleaned_data.get("project")
            service = form.cleaned_data.get("service")
            group = form.cleaned_data.get("group")
            try:
                pp = None
                if project:
                    pp, _ = Projects.objects.update_or_create(name=project,
                                                              defaults={'name': project})
                if pp and service:
                    Services.objects.update_or_create(project=pp, service_name=service,
                                                      defaults={'project': pp,
                                                                'service_name': service})
                if group:
                    Groups.objects.update_or_create(name=group,
                                                    defaults={'name': group})
            except Exception as ex:
                message = "新增失败，%s" % ex
                return render(request, "deploy/server_edit.html", locals())
            message = "新增成功"
            return render(request, "deploy/server_edit.html", locals())
        return render(request, "deploy/server_edit.html", locals())


@login_required
def server_del(request, in_id):
    if request.method == "GET":
        Servers.objects.get(id=in_id).delete()
        data_list = Servers.objects.all()

        return render(request, "deploy/servers_list.html", {"data_list": data_list})


@login_required
def common_list(request):
    data_list = CommonMethods.objects.all()

    return render(request, "deploy/common_list.html", locals())


@login_required
def common_add(request):
    if request.method == "GET":
        form = CommonForm()
        return render(request, "deploy/common_add.html", locals())
    else:
        form = CommonForm(request.POST)

        if form.is_valid():
            form.save()

            message = "新增成功"
            return render(request, "deploy/common_add.html", locals())

        return render(request, "deploy/common_add.html", locals())


@login_required
def common_edit(request, in_id):
    comm = CommonMethods.objects.get(id=in_id)
    if request.method == "GET":

        form = CommonForm(instance=comm)

        return render(request, "deploy/common_edit.html", locals())
    else:
        form = CommonForm(request.POST, instance=comm)

        if form.is_valid():
            form.save()

            message = "修改成功"
            return render(request, "deploy/common_edit.html", locals())
        return render(request, "deploy/common_edit.html", locals())


@login_required
def common_del(request, in_id):
    if request.method == "GET":
        CommonMethods.objects.get(id=in_id).delete()
        data_list = CommonMethods.objects.all()
        return render(request, "deploy/common_list.html", {"data_list": data_list})


@login_required
def common_run(request, in_id):
    if request.method == "GET":
        comm = CommonMethods.objects.get(id=in_id)
        if comm.method == "playbook":
            uuidkey = uuid.uuid4()
            data = {'name': comm.model,
                    'playbook_desc': comm.desc,
                    'playbook_args': comm.vars,
                    '_debug': 'off'}
            with open(os.getcwd() + str(comm.filePath), 'r') as f:
                contents = '\n'.join(i for i in f.readlines())
            form = PlaybookForm(data)
            projectList = Projects.objects.all()
            serverList = AssetsSource().serverList()
            inventoryList = Ansible_Inventory.objects.all()
            groupList = Groups.objects.all()
            if comm.model == "custom":
                roles_list = [os.path.basename(f) for f in glob.glob('upload/playbook/roles/*') if os.path.isdir(f)]
            return render(request, "deploy/playbook_run_online.html", locals())
        elif comm.method == "model":  # 调用模块执行页面
            data = {"moudel": comm.model, "moudel_args": comm.vars}
            form = MoudelForm(data=data)
            rediskey = uuid.uuid4()
            projectList = Projects.objects.all()
            serverList = AssetsSource().serverList()
            inventoryList = Ansible_Inventory.objects.all()
            groupList = Groups.objects.all()
            return render(request, "deploy/moudel.html", locals())
        elif comm.method == "scripts":
            uuidkey = uuid.uuid4()
            data = {'name': comm.model,
                    'scripts_args': comm.vars, }
            with open(os.getcwd() + str(comm.filePath), 'r') as f:
                contents = '\n'.join(i for i in f.readlines())
            form = ScriptsForm(data)

            return render(request, "deploy/scripts_run_online.html", locals())
    data_list = CommonMethods.objects.all()
    message = "运行错误！"
    return render(request, "deploy/common_list.html", locals())


@login_required
def inventory(request):
    if request.method == "GET":
        data_list = Ansible_Inventory.objects.all()
        for d in data_list:
            i, _ = get_json_inentory(d.id)
            d.detail = json.dumps(i, indent=4)

        return render(request, "deploy/inventory.html", {"data_list": data_list})


def get_json_inentory(inventory_id, pw=None):
    try:
        i = Ansible_Inventory.objects.get(id=inventory_id)
        data = {}
        all_host = []
        for x in i.inventory_group.all():
            data[x.group] = {}
            hosts = []
            if pw:
                for y in x.inventory_server.all():
                    y = Servers.objects.get(id=y.server)
                    hosts.append({"ip": y.ip,
                                  "username": y.username,
                                  "password": y.passwd,
                                  "sudo_passwd": y.sudo_passwd, })
                    all_host.append(y.ip)
            else:
                for y in x.inventory_server.all():
                    y = Servers.objects.get(id=y.server)
                    hosts.append({"ip": y.ip, })
                    all_host.append(y.ip)
            data[x.group]["hosts"] = hosts
            if x.ext_vars:
                data[x.group]["vars"] = json.loads(x.ext_vars)
        # print data,all_host
        return data, all_host

    except Exception as e:
        print e
        return e


@login_required
def inventory_add(request):
    if request.method == "GET":
        inventory_form = InventoryForm()
        group_form = GroupForm()
        return render(request, "deploy/inventory_add.html", locals())
    else:
        inventory_form = InventoryForm(request.POST)
        group_form = GroupForm(request.POST)
        if inventory_form.is_valid():
            name = inventory_form.cleaned_data["name"]
            desc = inventory_form.cleaned_data["desc"]
            create_user = request.user
            Ansible_Inventory.objects.update_or_create(name=name, desc=desc, create_user=create_user)
            message = "新增成功"
            return render(request, "deploy/inventory_add.html", locals())
        elif group_form.is_valid():
            inventory = group_form.cleaned_data["inventory"]
            group = group_form.cleaned_data["group"]
            ext_vars = group_form.cleaned_data["ext_vars"]
            # g = Ansible_Group(inventory=inventory,group=group,ext_vars=ext_vars)
            # g.save()
            # get_or_create 以及 update_or_create方法都要使用defaults的方式
            default = {"inventory": inventory, "group": group, "ext_vars": ext_vars}
            g, _ = Ansible_Group.objects.update_or_create(defaults=default, group=group)
            server = group_form.cleaned_data["server"]
            for i in server:
                default = {"group": g, "server": i.id}
                Ansible_Server.objects.update_or_create(defaults=default, group=g, server=i.id)
            message = "新增成功"
            return render(request, "deploy/inventory_add.html", locals())


@login_required
def inventory_edit(request, in_id):
    inventory_data = Ansible_Inventory.objects.get(id=in_id)
    group_data = None
    if inventory_data.inventory_group.all():
        group_data = inventory_data.inventory_group.all()[0]

    if request.method == "GET":
        inventory_form = InventoryForm(model_to_dict(inventory_data))
        if group_data:
            group_form = GroupForm(model_to_dict(group_data))
        else:
            group_form = GroupForm()
        return render(request, "deploy/inventory_add.html", locals())
    else:
        inventory_form = InventoryForm(request.POST, model_to_dict(inventory_data))
        if group_data:
            group_form = GroupForm(request.POST, model_to_dict(group_data))
        else:
            group_form = GroupForm()
        if inventory_form.is_valid():
            name = inventory_form.cleaned_data["name"]
            desc = inventory_form.cleaned_data["desc"]
            create_user = request.user
            Ansible_Inventory.objects.update_or_create(name=name, desc=desc, create_user=create_user)
            message = "修改成功"
            return render(request, "deploy/inventory_add.html", locals())
        elif group_form.is_valid():
            inventory = group_form.cleaned_data["inventory"]
            group = group_form.cleaned_data["group"]
            ext_vars = group_form.cleaned_data["ext_vars"]
            # g = Ansible_Group(inventory=inventory,group=group,ext_vars=ext_vars)
            # g.save()
            # get_or_create 以及 update_or_create方法都要使用defaults的方式
            default = {"inventory": inventory, "group": group, "ext_vars": ext_vars}
            g, _ = Ansible_Group.objects.update_or_create(defaults=default, group=group)
            server = group_form.cleaned_data["server"]
            for i in server:
                default = {"group": g, "server": i.id}
                Ansible_Server.objects.update_or_create(defaults=default, group=g, server=i.id)
            message = "新增成功"
            return render(request, "deploy/inventory_add.html", locals())


@login_required
def project_query(request, in_id):
    if request.method == "GET":
        project = Projects.objects.get(id=in_id)
        services = project.services.all()
        service_assets = []
        for service in services:
            service_assets.append(model_to_dict(service))
        return JsonResponse({'service_assets': service_assets})


@login_required
def inventory_query(request, in_id):
    try:
        inventory = Ansible_Inventory.objects.get(id=in_id)
    except Ansible_Inventory.DoesNotExist:
        return JsonResponse({'data': "没有找到数据"})
    if request.method == "GET":
        source = {}
        for ds in inventory.inventory_group.all():
            source[ds.group] = {}
            hosts = []
            for ser in ds.inventory_server.all():
                assets = Servers.objects.get(id=ser.server)

                hosts.append(assets.ip)

            source[ds.group]['hosts'] = hosts
            if ds.ext_vars:
                try:
                    source[ds.group]['vars'] = eval(ds.ext_vars)
                except Exception as ex:
                    source[ds.group]['vars'] = {}
                    # logger.warn(msg="获取资产组变量失败: {ex}".format(ex=ex))
        return JsonResponse({"code": 200, "msg": "success", "data": source})


@login_required
def assets_server_query(request):
    if request.method == "POST":
        if request.POST.get('query') in ['service', 'project', 'group']:
            dataList = []
            if request.POST.get('query') == 'service':
                serv = Services.objects.get(id=request.POST.get('id')).service_name
                for ser in Servers.objects.filter(service=serv):
                    try:
                        project = ser.project
                    except Exception as ex:
                        project = '未知'

                    try:
                        service = ser.service
                    except Exception as ex:
                        service = '未知'

                    dataList.append({"id": ser.id, "ip": ser.ip, "project": project, "service": service})

            elif request.POST.get('query') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('id')).name
                for ser in Servers.objects.filter(group=group_name):
                    try:
                        project = ser.project
                    except Exception as ex:
                        project = '未知'
                    try:
                        service = ser.service
                    except Exception as ex:
                        service = '未知'

                    dataList.append({"id": ser.id, "ip": ser.ip, "project": project, "service": service})

            return JsonResponse({'msg': "主机查询成功", "code": 200, 'data': dataList})
        else:
            JsonResponse({'msg': "不支持的操作", "code": 500, 'data': []})
    else:
        return JsonResponse({'msg': "操作失败", "code": 500, 'data': "不支持的操作"})


@login_required
def inventory_del(request, in_id):
    if request.method == "GET":
        Ansible_Inventory.objects.get(id=in_id).delete()
        data_list = Ansible_Inventory.objects.all()

        for d in data_list:
            i, _ = get_json_inentory(d.id)
            d.detail = json.dumps(i, indent=4)
        return render(request, "deploy/inventory.html", {"data_list": data_list})


@login_required()
def get_ansibel_result(request):
    if request.method == "POST":
        redisKey = request.POST.get('uuidkey')
        msg = Redis_pool.rpop(redisKey)
        if msg:
            return JsonResponse({'msg': msg, "code": 200, 'data': []})
        else:
            return JsonResponse({'msg': None, "code": 200, 'data': []})


@login_required
def model_run(request):
    if request.method == "POST":
        redisKey = request.POST.get('uuidkey')
        form = MoudelForm(request.POST)

        if form.is_valid():
            model = form.cleaned_data['moudel']
            args = form.cleaned_data['moudel_args']
            debug = form.cleaned_data['_debug']
            # inventory = form.cleaned_data['inventory']
            # print model,args,debug,inventory
            # resource, sList = get_json_inentory(inventory.id, pw="get")
            resource = []
            sList = []

            if request.POST.get('server_model') == 'custom':
                serverList = request.POST.getlist('ansible_server')
                sList, resource = AssetsSource().custom(serverList)
            elif request.POST.get('server_model') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('script_auth_group')).name
                sList, resource = AssetsSource().group(group=group_name)
            elif request.POST.get('server_model') == 'service':
                serv = Services.objects.get(id=request.POST.get('ansible_service')).service_name
                sList, resource = AssetsSource().service(business=serv)
            elif request.POST.get('server_model') == 'inventory':
                # sList, resource, groups = AssetsSource().inventory(inventory=request.POST.get('ansible_inventory'))
                resource, sList = get_json_inentory(request.POST.get('ansible_inventory'), pw="get")
            if len(sList) > 0:

                logId = Log_Ansible_Model.objects.create(
                    ans_user=str(request.user),
                    ans_server=','.join(sList),
                    ans_args=args,
                    ans_model=model,
                )
                Redis_pool.delete(redisKey)
                Redis_pool.lpush(redisKey,
                                 "[Start] Ansible Model: {0}  ARGS:{1}".format(model, args))

                if debug == 'on':
                    ANS = ANSRunner(hosts=resource, redisKey=redisKey, logId=logId, verbosity=4)
                else:
                    ANS = ANSRunner(hosts=resource, redisKey=redisKey, logId=logId,)

                ANS.run_model(host_list=sList, module_name=model, module_args=args)
                Redis_pool.lpush(redisKey, "[Done] Ansible Done.")
                return JsonResponse({'msg': "操作成功", "code": 200, 'data': []})
            else:
                # print "操作失败，未选择主机或者该分组没有成员"
                return JsonResponse({'msg': "操作失败，未选择主机或者该分组没有成员", "code": 500, 'data': []})

    else:
        form = MoudelForm()
        rediskey = uuid.uuid4()
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        return render(request, "deploy/moudel.html", locals())


@login_required
def scripts_list(request):
    if request.method == "GET":
        data_list = Ansible_Script.objects.all()
        for d in data_list:
            with open(os.getcwd() + str(d.script_file), 'r') as f:
                d.detail = ''.join(i for i in f.readlines())
        return render(request, "deploy/ansible_scripts_list.html", locals())


@login_required
def scripts_add(request):
    if request.method == "GET":
        form = ScriptsForm()
        uuidkey = uuid.uuid4()
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        serviceList = Services.objects.all()
        return render(request, "deploy/scripts_run_online.html", locals())
    elif request.method == "POST":
        scripts_uuid = request.POST.get('uuidkey')
        form = ScriptsForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data['name']
            scripts_args = form.cleaned_data['scripts_args']
            debug = form.cleaned_data['_debug']
            resource = []
            sList = []

            if request.POST.get('server_model') == 'custom':
                serverList = request.POST.getlist('ansible_server')
                sList, resource = AssetsSource().custom(serverList)
            elif request.POST.get('server_model') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('script_auth_group')).name
                sList, resource = AssetsSource().group(group=group_name)
            elif request.POST.get('server_model') == 'service':
                serv = Services.objects.get(id=request.POST.get('ansible_service')).service_name
                sList, resource = AssetsSource().service(business=serv)
            elif request.POST.get('server_model') == 'inventory':
                # sList, resource, groups = AssetsSource().inventory(inventory=request.POST.get('ansible_inventory'))
                resource, sList = get_json_inentory(request.POST.get('ansible_inventory'), pw="get")

            # if len(request.POST.get('custom_model')) > 0:
            #     model_name = request.POST.get('custom_model')
            # else:
            #     model_name = request.POST.get('ansible_model', None)
            # inventory = form.cleaned_data['inventory']
            # # print model,args,debug,inventory
            # resource, sList = get_json_inentory(inventory.id, pw="get")

            def saveScript(content, filePath):
                if os.path.isdir(os.path.dirname(filePath)) is not True:
                    os.makedirs(os.path.dirname(filePath))  # 判断文件存放的目录是否存在，不存在就创建
                with open(filePath, 'w') as f:
                    f.write(content)
                return filePath

            if len(sList) > 0 and request.POST.get('type') == 'run':
                filePath = saveScript(content=request.POST.get('script_file'),
                                      filePath='/tmp/script-{ram}'.format(
                                          ram=uuid.uuid4().hex[0:8]))

                redisKey = scripts_uuid
                logId = AnsibleRecord.Model.insert(user=str(request.user), ans_model='script',
                                                   ans_server=','.join(sList), ans_args=filePath)
                Redis_pool.delete(redisKey)
                Redis_pool.lpush(redisKey,
                                 "[Start] Ansible Model: {model}  Script:{filePath} {args}".format(
                                     model='script', filePath=filePath, args=scripts_args))
                if debug == 'on':
                    ANS = ANSRunner(hosts=resource, redisKey=redisKey, logId=logId, verbosity=4)
                else:
                    ANS = ANSRunner(hosts=resource, redisKey=redisKey, logId=logId,)
                ANS.run_model(host_list=sList, module_name='script',
                              module_args="{filePath} {args}".format(filePath=filePath,
                                                                     args=scripts_args))
                Redis_pool.lpush(redisKey, "[Done] Ansible Done.")
                try:
                    os.remove(filePath)
                except Exception as ex:
                    # logger.warn(msg="删除文件失败: {ex}".format(ex=ex))
                    print("删除文件失败: {ex}".format(ex=ex))
                return JsonResponse({'msg': "操作成功", "code": 200, 'data': []})
            elif request.POST.get('type') == 'save':
                fileName = '/upload/scripts/script-{ram}'.format(ram=uuid.uuid4().hex[0:8])
                filePath = os.getcwd() + fileName

                saveScript(content=request.POST.get('script_file'), filePath=filePath)
                try:
                    Ansible_Script.objects.create(
                        script_name=name,
                        script_uuid=scripts_uuid,
                        script_args=scripts_args,
                        script_server=json.dumps(sList),
                        # script_group=inventory.id,
                        script_file=fileName,
                        # script_service=service,
                        # script_type=request.POST.get('server_model')
                    )
                except Exception as ex:
                    # logger.warn(msg="添加ansible脚本失败: {ex}".format(ex=ex))
                    return JsonResponse({'msg': str(ex), "code": 500, 'data': []})
                return JsonResponse({'msg': "保存成功", "code": 200, 'data': []})

            else:
                # print "操作失败，未选择主机或者该分组没有成员"
                return JsonResponse({'msg': "操作失败，未选择主机或者该分组没有成员",
                                     "code": 500, 'data': []})


@login_required
def scripts_run(request, s_id):
    if request.method == "GET":
        scripts = Ansible_Script.objects.get(id=s_id)
        uuidkey = scripts.script_uuid
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        serviceList = Services.objects.all()
        data = {'name': scripts.script_name,
                'inventory': scripts.script_group,
                'scripts_args': scripts.script_args,
                '_debug': 'off'}
        with open(os.getcwd() + str(scripts.script_file), 'r') as f:
            contents = '\n'.join(i for i in f.readlines())
        form = ScriptsForm(data)

        return render(request, "deploy/scripts_run_online.html", locals())


@login_required
def scripts_del(request, s_id):
    if request.method == "GET":
        scripts = Ansible_Script.objects.get(id=s_id)
        scripts.delete()
        data_list = Ansible_Script.objects.all()
        for d in data_list:
            with open(os.getcwd() + str(d.script_file), 'r') as f:
                d.detail = ''.join(i for i in f.readlines())
        return render(request, "deploy/ansible_scripts_list.html", locals())


@login_required
def playbook_del(request, s_id):
    if request.method == "GET":
        playbook = Ansible_Playbook.objects.get(id=s_id)
        playbook.delete()
        data_list = Ansible_Playbook.objects.all()
        for d in data_list:
            with open(os.getcwd() + str(d.playbook_file), 'r') as f:
                d.detail = ''.join(i for i in f.readlines())
        return render(request, "deploy/ansible_playbook_list.html", locals())


@login_required
def playbook_run(request, s_id):
    if request.method == "GET":
        playbook = Ansible_Playbook.objects.get(id=s_id)
        uuidkey = playbook.playbook_uuid
        data = {'name': playbook.playbook_name,
                'playbook_desc': playbook.playbook_desc,
                'inventory': playbook.playbook_auth_group,
                'playbook_args': playbook.playbook_vars,
                '_debug': 'off'}
        with open(os.getcwd() + str(playbook.playbook_file), 'r') as f:
            contents = '\n'.join(i for i in f.readlines())
        form = PlaybookForm(data)
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        return render(request, "deploy/playbook_run_online.html", locals())


@login_required
def playbook_add(request):
    if request.method == "GET":
        form = PlaybookForm()
        uuidkey = uuid.uuid4()
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        return render(request, "deploy/playbook_run_online.html", locals())
    elif request.method == "POST":
        playbook_uuid = request.POST.get('uuidkey')
        form = PlaybookForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data['name']
            playbook_args = form.cleaned_data['playbook_args']
            playbook_desc = form.cleaned_data['playbook_desc']
            debug = form.cleaned_data['_debug']
            # inventory = form.cleaned_data['inventory']
            # print name,playbook_args,playbook_desc,debug,inventory
            # resource, sList = get_json_inentory(inventory.id, pw="get")
            resource = []
            sList = []

            if request.POST.get('server_model') == 'custom':
                serverList = request.POST.getlist('ansible_server')
                sList, resource = AssetsSource().custom(serverList)
            elif request.POST.get('server_model') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('script_auth_group')).name
                sList, resource = AssetsSource().group(group=group_name)
            elif request.POST.get('server_model') == 'service':
                serv = Services.objects.get(id=request.POST.get('ansible_service')).service_name
                sList, resource = AssetsSource().service(business=serv)
            elif request.POST.get('server_model') == 'inventory':
                # sList, resource, groups = AssetsSource().inventory(inventory=request.POST.get('ansible_inventory'))
                resource, sList = get_json_inentory(request.POST.get('ansible_inventory'), pw="get")

            def saveScript(content, filePath):
                if os.path.isdir(os.path.dirname(filePath)) is not True:
                    os.makedirs(os.path.dirname(filePath))  # 判断文件存放的目录是否存在，不存在就创建
                with open(filePath, 'w') as f:
                    f.write(content)
                return filePath

            if len(sList) > 0 and request.POST.get('type') == 'run':
                if Redis_pool.get(redisKey=playbook_uuid + '-locked') is None:
                    # 判断剧本是否有人在执行
                    # 加上剧本执行锁
                    Redis_pool.set(redisKey=playbook_uuid + '-locked', value=request.user)
                    # 删除旧的执行消息
                    Redis_pool.delete(playbook_uuid)
                    try:
                        if len(playbook_args) == 0:
                            playbook_args = dict()
                        else:
                            playbook_args = json.loads(playbook_args)
                        playbook_args['host'] = sList
                        filePath = None
                        fileobj = request.FILES.get("playbook_file_upload", None)
                        if fileobj:
                            filePath = os.path.join(os.getcwd(), 'upload/playbook', fileobj.name)
                            # if os.path.isdir(os.path.dirname(filename)) is not True:
                            if not os.path.exists(os.path.join(os.getcwd(), 'upload/playbook')):
                                # print("dir not exists,make it")
                                os.makedirs(os.path.join(os.getcwd(), 'upload/playbook'))
                            try:
                                with open(filePath, 'wb') as f:
                                    for chunk in fileobj.chunks():
                                        f.write(chunk)
                            except Exception as e:
                                print e
                        elif request.POST.get("playbook_file", None):
                            # 临时写入的playbook也放入同一个位置，方便roles调用
                            tempath = os.path.join(os.getcwd(), 'upload/playbook/playbook-{ram}'.format(
                                ram=uuid.uuid4().hex[0:8]))
                            filePath = saveScript(content=request.POST.get('playbook_file'),
                                                  filePath=tempath)

                        logId = AnsibleRecord.PlayBook.insert(user=str(request.user),
                                                              # ans_id=playbook.id,
                                                              ans_name=name,
                                                              ans_content="执行Ansible剧本",
                                                              ans_server=','.join(sList))
                        # 执行ansible playbook
                        if request.POST.get('ansible_debug') == 'on':
                            ANS = ANSRunner(hosts=resource, redisKey=playbook_uuid, logId=logId, verbosity=4)
                        else:
                            ANS = ANSRunner(hosts=resource, redisKey=playbook_uuid, logId=logId)
                        if filePath:
                            ANS.run_playbook(host_list=sList, playbook_path=filePath,
                                             extra_vars=playbook_args)
                        # 获取结果
                        result = ANS.get_playbook_result()
                        dataList = []
                        statPer = {
                            "unreachable": 0,
                            "skipped": 0,
                            "changed": 0,
                            "ok": 0,
                            "failed": 0
                        }
                        for k, v in result.get('status').items():
                            v['host'] = k
                            if v.get('failed') > 0 or v.get('unreachable') > 0:
                                v['result'] = 'Failed'
                            else:
                                v['result'] = 'Succeed'
                            dataList.append(v)
                            statPer['unreachable'] = v['unreachable'] + statPer['unreachable']
                            statPer['skipped'] = v['skipped'] + statPer['skipped']
                            statPer['changed'] = v['changed'] + statPer['changed']
                            statPer['failed'] = v['failed'] + statPer['failed']
                            statPer['ok'] = v['ok'] + statPer['ok']
                        Redis_pool.lpush(playbook_uuid, "[Done] Ansible Done.")
                        return JsonResponse({'msg': "操作成功", "code": 200, 'data': dataList, "statPer": statPer})
                    except Exception as e:
                        return JsonResponse({'msg': "剧本执行失败，{}".format(e), "code": 500,
                                             'data': []})
                    finally:
                        # 切换版本之后取消项目部署锁
                        Redis_pool.delete(redisKey=playbook_uuid + '-locked')



                else:
                    return JsonResponse({'msg': "剧本执行失败，{user}正在执行该剧本".format(
                        user=Redis_pool.get(playbook_uuid + '-locked')), "code": 500,
                        'data': []})





            elif request.POST.get('type') == 'save':
                fileobj = request.FILES.get("playbook_file_upload", None)
                fileName = None
                if fileobj:
                    fileName = os.path.join('/upload/playbook', fileobj.name)
                    filePath = os.path.join(os.getcwd(), 'upload/playbook', fileobj.name)
                    # if os.path.isdir(os.path.dirname(filename)) is not True:
                    if not os.path.exists(os.path.join(os.getcwd(), 'upload/playbook')):
                        # print("dir not exists,make it")
                        os.makedirs(os.path.join(os.getcwd(), 'upload/playbook'))
                    try:
                        with open(filePath, 'wb') as f:
                            for chunk in fileobj.chunks():
                                f.write(chunk)
                    except Exception as e:
                        print e
                elif request.POST.get("playbook_file", None):

                    fileName = '/upload/playbook/playbook-{name}-{ram}'.format(name=name,
                                                                               ram=uuid.uuid4().hex[0:8])
                    filePath = os.getcwd() + fileName

                    saveScript(content=request.POST.get('playbook_file'), filePath=filePath)
                try:
                    defaults = {
                        'playbook_name': name,
                        'playbook_uuid': playbook_uuid,
                        'playbook_vars': playbook_args,
                        'playbook_desc': playbook_desc,
                        # 'playbook_auth_group': inventory.id,
                        'playbook_file': fileName,
                    }
                    Ansible_Playbook.objects.update_or_create(
                        playbook_name=name, defaults=defaults)
                    return JsonResponse({'msg': "保存成功", "code": 200, 'data': []})
                except Exception as ex:
                    # logger.warn(msg="添加ansible脚本失败: {ex}".format(ex=ex))
                    return JsonResponse({'msg': str(ex), "code": 500, 'data': []})


            else:
                # print "操作失败，未选择主机或者该分组没有成员"
                return JsonResponse({'msg': "操作失败，未选择主机或者该分组没有成员",
                                     "code": 500, 'data': []})


@login_required
def playbook_list(request):
    if request.method == "GET":
        data_list = Ansible_Playbook.objects.all()
        for d in data_list:
            with open(os.getcwd() + str(d.playbook_file), 'r') as f:
                d.detail = ''.join(i for i in f.readlines())
        return render(request, "deploy/ansible_playbook_list.html", locals())


@login_required
def ansible_log(request):
    if request.method == "GET":
        modelList = Log_Ansible_Model.objects.all().order_by('-id')[0:500]
        playbookList = Log_Ansible_Playbook.objects.all().order_by('-id')[0:500]
        fileList = LogFileOps.objects.all().order_by('-id')[0:500]
        return render(request, "deploy/ansible_log.html", locals())


@login_required
def ansible_log_view(request, s_id):
    if request.method == "GET":
        data = "未找到相关信息！"
        if request.GET.get("m_p") == "moudel" or request.GET.get("m_p") == "model":
            data_list = Log_Ansible_Model.objects.get(id=s_id).ansible_model_log.all()
            data = []
            for i in data_list:
                data.append(i.content)
        elif request.GET.get("m_p") == "playbook":
            data_list = Log_Ansible_Playbook.objects.get(id=s_id).ansible_playbook_log.all()
            data = []
            for i in data_list:
                data.append(i.content)
        return JsonResponse({'data': data})


@login_required
def ansible_log_del(request, s_id):
    if request.method == "GET":
        if request.GET.get("m_p") == "moudel" or request.GET.get("m_p") == "model":
            Log_Ansible_Model.objects.get(id=s_id).delete()
        elif request.GET.get("m_p") == "playbook":
            Log_Ansible_Playbook.objects.get(id=s_id).delete()
        return JsonResponse({'messages': '删除成功！'})


@login_required()
def file_up(request):
    if request.method == "GET":
        form = FileUpForm()
        uuidkey = uuid.uuid4()
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        serviceList = Services.objects.all()
        return render(request, "deploy/file_up.html", locals())
    elif request.method == "POST":
        scripts_uuid = request.POST.get('uuidkey')
        form = FileUpForm(request.POST)

        if form.is_valid():
            descpath = form.cleaned_data['filepath']
            permission = form.cleaned_data['permission']
            owner = form.cleaned_data['owner']
            # inventory = form.cleaned_data['inventory']
            content = form.cleaned_data['content']
            # print model,args,debug,inventory
            # resource, sList = get_json_inentory(inventory.id, pw="get")
            resource = []
            sList = []

            if request.POST.get('server_model') == 'custom':
                serverList = request.POST.getlist('ansible_server')
                sList, resource = AssetsSource().custom(serverList)
            elif request.POST.get('server_model') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('script_auth_group')).name
                sList, resource = AssetsSource().group(group=group_name)
            elif request.POST.get('server_model') == 'service':
                serv = Services.objects.get(id=request.POST.get('ansible_service')).service_name
                sList, resource = AssetsSource().service(business=serv)
            elif request.POST.get('server_model') == 'inventory':
                # sList, resource, groups = AssetsSource().inventory(inventory=request.POST.get('ansible_inventory'))
                resource, sList = get_json_inentory(request.POST.get('ansible_inventory'), pw="get")
            fileobj = request.FILES.get("file_upload", None)
            # fileName = None
            filePath = None
            if fileobj:
                # fileName = os.path.join('/upload/myfile/upload', fileobj.name)
                filePath = os.path.join(os.getcwd(), 'upload/myfile/upload', fileobj.name)
                # if os.path.isdir(os.path.dirname(filename)) is not True:
                if not os.path.exists(os.path.join(os.getcwd(), 'upload/myfile/upload')):
                    # print("dir not exists,make it")
                    os.makedirs(os.path.join(os.getcwd(), 'upload/myfile/upload'))
                try:
                    with open(filePath, 'wb') as f:
                        for chunk in fileobj.chunks():
                            f.write(chunk)
                except Exception as e:
                    print(e)

                scripts_args = "src={} dest={} owner={} mode={} backup=yes".format(filePath,
                                                                                   descpath,
                                                                                   owner, permission)
                redisKey = scripts_uuid
                # logId = AnsibleRecord.Model.insert(user=str(request.user), ans_model='copy',
                #                                    ans_server=','.join(sList), ans_args=filePath)
                Redis_pool.delete(redisKey)
                Redis_pool.lpush(redisKey,
                                 "[Start] Ansible Model: {model}  Script:{filePath} {args}".format(
                                     model='copy', filePath=filePath, args=scripts_args))

                ANS = ANSRunner(hosts=resource, redisKey=redisKey)

                ANS.run_model(host_list=sList, module_name='copy',
                              module_args=scripts_args)
                Redis_pool.lpush(redisKey, "[Done] Ansible Done.")
                try:
                    LogFileOps.objects.create(opstype="up", filepath=descpath, server=str(sList),
                                              content=content,
                                              user=str(request.user.username), srcfile=fileobj.name)
                except Exception as e:
                    print(e)
                return JsonResponse({'msg': "操作成功", "code": 200, 'data': []})

            else:
                # print "操作失败，未选择主机或者该分组没有成员"
                return JsonResponse({'msg': "操作失败，未选择主机或者该分组没有成员",
                                     "code": 500, 'data': []})


@login_required()
def file_find(request):
    if request.method == "POST":
        form = FileDownForm(request.POST)

        if form.is_valid():
            descpath = form.cleaned_data['filepath']
            # inventory = form.cleaned_data['inventory']
            dataList = []
            # resource, sList = get_json_inentory(inventory.id, pw="get")
            resource = []
            sList = []

            if request.POST.get('server_model') == 'custom':
                serverList = request.POST.getlist('ansible_server')
                sList, resource = AssetsSource().custom(serverList)
            elif request.POST.get('server_model') == 'group':
                group_name = Groups.objects.get(id=request.POST.get('script_auth_group')).name
                sList, resource = AssetsSource().group(group=group_name)
            elif request.POST.get('server_model') == 'service':
                serv = Services.objects.get(id=request.POST.get('ansible_service')).service_name
                sList, resource = AssetsSource().service(business=serv)
            elif request.POST.get('server_model') == 'inventory':
                # sList, resource, groups = AssetsSource().inventory(inventory=request.POST.get('ansible_inventory'))
                resource, sList = get_json_inentory(request.POST.get('ansible_inventory'), pw="get")
            scripts_args = "path={}".format(descpath)
            ANS = ANSRunner(hosts=resource)
            ANS.run_model(host_list=sList, module_name='find',
                          module_args=scripts_args)
            filesData = json.loads(ANS.get_model_result())
            for k, v in filesData.get('success').items():
                for ds in v.get('files'):
                    data = {}
                    # data["id"] = order.id
                    data['host'] = k
                    data['path'] = ds.get('path')
                    data['size'] = round(float(ds.get('size')) / 1024, 2)
                    data['islnk'] = ds.get('islnk')
                    dataList.append(data)
            return JsonResponse({'msg': "操作成功", "code": 200, 'data': dataList})
        else:
            return JsonResponse({'msg': "操作失败", "code": 500, 'data': []})


@login_required()
def file_down(request):
    if request.method == "GET":
        form = FileDownForm()
        uuidkey = uuid.uuid4()
        projectList = Projects.objects.all()
        serverList = AssetsSource().serverList()
        inventoryList = Ansible_Inventory.objects.all()
        groupList = Groups.objects.all()
        serviceList = Services.objects.all()
        return render(request, "deploy/file_down.html", locals())


    elif request.method == "POST":

        descpath = request.POST.get('path')
        # inventory = request.POST.get('inventory')
        content = request.POST.get('content')
        # print model,args,debug,inventory
        # resource, sList = get_json_inentory(inventory, pw="get")
        resource = []
        sList = []

        sList, resource = AssetsSource().queryAssetsByIp(ipList=request.POST.getlist('dest_server'))
        filePath = os.path.join(os.getcwd(), 'upload/myfile/download')
        if not os.path.exists(filePath):
            # print("dir not exists,make it")
            os.makedirs(filePath)

        scripts_args = "src={} dest={} fail_on_missing=yes".format(descpath, filePath, )
        ANS = ANSRunner(hosts=resource)
        ANS.run_model(host_list=sList, module_name='fetch',
                      module_args=scripts_args)
        # 日志记录
        try:
            LogFileOps.objects.create(opstype="down", filepath='/upload/myfile/download',
                                      server=str(sList), content=content,
                                      user=str(request.user.username), srcfile=descpath)
        except Exception as e:
            print(e)

        # 文件读取迭代
        def file_iterator(filepath, chunk_size=512):
            with open(filepath, 'rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

        result = json.loads(ANS.get_model_result())
        filePath = result.get('success').get(request.POST.get('dest_server')).get('dest')
        if filePath:
            response = StreamingHttpResponse(file_iterator(filePath))
            response = FileResponse(response)
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment; filename="{file_name}'.format(
                file_name=os.path.basename(filePath))
            return response

        # return JsonResponse({'msg': "操作成功", "code": 200, 'data': []})

        else:
            # print "操作失败，未选择主机或者该分组没有成员"
            return JsonResponse({'msg': "操作失败，未选择主机或者该分组没有成员",
                                 "code": 500, 'data': []})


@login_required()
def file_log(request):
    if request.method == "GET":
        data_list = LogFileOps.objects.all()
        uuidkey = uuid.uuid4()
        return render(request, "deploy/file_log.html", locals())
