#! /usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms

from .models import Ansible_Inventory,Ansible_Group,Ansible_Server,Servers,CommonMethods

class ServersForm(forms.ModelForm):
    class Meta:
        model=Servers
        exclude = ('id',)
        # fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'class': 'form-control'}),
            'hosted_on': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'passwd': forms.PasswordInput(attrs={'class': 'form-control'}),
            'sudo_passwd': forms.PasswordInput(attrs={'class': 'form-control'}),
            'host_vars': forms.TextInput(attrs={'class': 'form-control'}),
            'keyfile': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.TextInput(attrs={'class': 'form-control'}),
            'line': forms.TextInput(attrs={'class': 'form-control'}),
            'disk_total': forms.TextInput(attrs={'class': 'form-control'}),
            'cpu_rpm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '4C16G'}),
            'os_type': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.TextInput(attrs={'class': 'form-control'}),
            'site': forms.TextInput(attrs={'class': 'form-control'}),
            'memo': forms.TextInput(attrs={'class': 'form-control'}),

        }


class CommonForm(forms.ModelForm):
    class Meta:
        model=CommonMethods
        exclude = ('id','last_run_result','last_run_time')
        # fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'desc': forms.TextInput(attrs={'class': 'form-control'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'vars': forms.TextInput(attrs={'class': 'form-control',
                                           'placeholder': '{"role_name":"custom_roule"}',}),
            'filePath': forms.TextInput(attrs={'class': 'form-control',
                                               'placeholder': '/upload/playbook/site.yml',}),
            'user': forms.TextInput(attrs={'class': 'form-control'}),

        }

class InventoryForm(forms.Form):
    name = forms.CharField(required=True, label='名称:',
                           error_messages={'required': u'请输入名称', 'invalid': u'名格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '名称',
                                                         }), )
    desc = forms.CharField(required=True, label='功能描述:',
                          widget=forms.TextInput(attrs={'class': 'form-control',
                                                        'style': 'height:150px;',
                                                        'placeholder': '如：修改用户',
                                                        }), )

class GroupForm(forms.Form):
    inventory =forms.ModelChoiceField(required=False, error_messages={'required': u'选择资产'},
                                       queryset=Ansible_Inventory.objects.all(),
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    group = forms.CharField(required=True, label='组名',
                           error_messages={'required': u'请输入组名称', 'invalid': u'名格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '组名称',
                                                         }), )
    ext_vars = forms.CharField(required=False, label='外部组变量',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '组变量,如{"a":"10","b":"20"}',
                                                         }), )
    server = forms.ModelMultipleChoiceField(required=False, error_messages={'required': u'选择主机'},
                                           queryset=Servers.objects.all(),
                                           widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

#
# class ServerForm(forms.Form):
#     group = forms.ModelChoiceField(required=False, error_messages={'required': u'选择组名'},
#                                        queryset=Ansible_Group.objects.all(),
#                                        widget=forms.Select(attrs={'class': 'form-control'}))
#     server = forms.ModelChoiceField(required=False, error_messages={'required': u'选择主机'},
#                                        queryset=Server_asset.objects.all(),
#                                        widget=forms.Select(attrs={'class': 'form-control'}))

class MoudelForm(forms.Form):
    _moudels = ("shell","ping","copy","yum","user","service","file","cron","sync","wget","custom")
    _moudels = zip(_moudels,_moudels)
    # inventory = forms.ModelChoiceField(queryset=Ansible_Inventory.objects.all(),
    #                                    widget=forms.Select(attrs={'class': 'form-control'}))
    moudel = forms.ChoiceField(required=True, choices=_moudels, label='选择模块',
                               initial='ping',
                               widget=forms.Select(attrs={'class': 'form-control'}))
    moudel_args = forms.CharField(required=False, label='模块参数',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '参数',
                                                         }), )
    _debug = forms.ChoiceField(choices=(('on','开启'),('off','关闭')),label="Debug选项",required=False,
                               initial='off',widget=forms.Select(attrs={'class': 'form-control'}))



class ScriptsForm(forms.Form):
    name = forms.CharField(required=True, label='名称',
                           error_messages={'required': u'请输入名称', 'invalid': u'名格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '如：用户新增',
                                                         }), )
    # inventory = forms.ModelChoiceField(queryset=Ansible_Inventory.objects.all(),
    #                                    widget=forms.Select(attrs={'class': 'form-control'}))

    scripts_args = forms.CharField(required=False, label='参数',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                          'placeholder': '{"role_name":"custom_roule"}',
                                                         }), )
    _debug = forms.ChoiceField(required=False,choices=(('on','开启'),('off','关闭')),label="Debug选项",
                               initial='off',widget=forms.Select(attrs={'class': 'form-control'}))



class PlaybookForm(forms.Form):
    name = forms.CharField(required=True, label='名称',
                           error_messages={'required': u'请输入名称', 'invalid': u'名格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '如：用户新增',
                                                         }), )
    # inventory = forms.ModelChoiceField(queryset=Ansible_Inventory.objects.all(),
    #                                    widget=forms.Select(attrs={'class': 'form-control'}))

    playbook_args = forms.CharField(required=False, label='剧本参数',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '{"role_name":"custom_roule"}',
                                                         }), )
    playbook_desc = forms.CharField(required=False, label='剧本描述',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '作用功能说明',
                                                         }), )
    _debug = forms.ChoiceField(required=False,choices=(('on','开启'),('off','关闭')),label="Debug选项",
                               initial='off',widget=forms.Select(attrs={'class': 'form-control'}))



class FileUpForm(forms.Form):
    # inventory = forms.ChoiceField(choices=(('0','请选择资产类型'),('1','产品线'),('2','组别'),('3','动态资产表'),('4','自定义')),
    #                               required=True,label='资产类型',
    #                                widget=forms.Select(attrs={'class': 'form-control'}))

    inventory = forms.ModelChoiceField(queryset=Ansible_Inventory.objects.all(),
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    filepath = forms.CharField(required=True, label='目标路径',
                           error_messages={'required': u'请输入目标路径', 'invalid': u'格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '/usr/local/src/',
                                                         }), )
    owner = forms.CharField(required=False, label='文件属主',
                           initial='root',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': 'root',
                                                         }), )

    permission = forms.IntegerField(required=False, label='文件权限',
                           initial=755,
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': 755,
                                                         }), )
    content = forms.CharField(required=False, label='备注',
                           # initial='root',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '如：nginx配置修改',
                                                         }), )

class FileDownForm(forms.Form):
    # inventory = forms.ChoiceField(choices=(('1','产品线'),('2','组别'),('3','动态资产表'),('4','自定义')),
    #                               required=True,label='资产类型',
    #                                widget=forms.Select(attrs={'class': 'form-control'}))
    inventory = forms.ModelChoiceField(queryset=Ansible_Inventory.objects.all(),
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    filepath = forms.CharField(required=True, label='目标路径',
                           error_messages={'required': u'请输入目标路径', 'invalid': u'格式错误'},
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': '/usr/local/src/',
                                                         }), )
    content = forms.CharField(required=False, label='备注',
                              # initial='root',
                              widget=forms.TextInput(attrs={'class': 'form-control',
                                                            'placeholder': '如：nginx配置修改',
                                                            }), )
