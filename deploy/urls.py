from django.conf.urls import url

import views

urlpatterns = [
    url(r'^$', views.servers_list),
    url(r'^fileup/$', views.file_up,name="file_up"),
    url(r'^filedown/$', views.file_down,name="file_down"),
    url(r'^filefind/$', views.file_find,name="file_find"),
    url(r'^filelog/$', views.file_log,name="file_log"),
    url(r'^inventory/$', views.inventory,name="inventory"),
    url(r'^inventory_query/(?P<in_id>[0-9]+)/$', views.inventory_query),
    url(r'^servers_list/$', views.servers_list,name="servers_list"),
    url(r'^server/add/$', views.server_add, name='server_add'),
    url(r'^server/edit/(?P<in_id>[0-9]+)/$', views.server_edit, name='server_edit'),
    url(r'^server/del/(?P<in_id>[0-9]+)/$', views.server_del, name='server_del'),
    url(r'^inventory/add/$', views.inventory_add, name='inventory_add'),
    url(r'^inventory/edit/(?P<in_id>[0-9]+)/$', views.inventory_edit, name='inventory_edit'),
    url(r'^inventory/del/(?P<in_id>[0-9]+)/$', views.inventory_del, name='inventory_del'),
    url(r'^project_query/(?P<in_id>[0-9]+)/$', views.project_query, name='project_query'),
    url(r'^asset_server_query/$', views.assets_server_query, name='assets_server_query'),
    url(r'^model/$', views.model_run, name='model_run'),
    url(r'^run_result/$', views.get_ansibel_result, name='get_ansibel_result'),
    url(r'^scripts_list/$', views.scripts_list, name='scripts_list'),
    url(r'^scripts_add/$', views.scripts_add, name='scripts_add'),
    url(r'^scripts_run/(?P<s_id>[0-9]+)/$', views.scripts_run, name='scripts_run'),
    url(r'^scripts_del/(?P<s_id>[0-9]+)/$', views.scripts_del, name='scripts_del'),
    url(r'^playbook_list/$', views.playbook_list, name='playbook_list'),
    url(r'^playbook_add/$', views.playbook_add, name='playbook_add'),
    url(r'^playbook_run/(?P<s_id>[0-9]+)/$', views.playbook_run, name='playbook_run'),
    url(r'^playbook_del/(?P<s_id>[0-9]+)/$', views.playbook_del, name='playbook_del'),
    url(r'^ansible_log/$', views.ansible_log, name='ansible_log'),
    url(r'^ansible_log_view/(?P<s_id>[0-9]+)/$', views.ansible_log_view, name='ansible_log_view'),
    url(r'^ansible_log_del/(?P<s_id>[0-9]+)/$', views.ansible_log_del, name='ansible_log_del'),
    url(r'^asset_batch_import/$', views.asset_batch_import, name='asset_batch_import'),
    url(r'^common_list/$', views.common_list, name='common_list'),
    url(r'^common_add/$', views.common_add, name='common_add'),
    url(r'^common_edit/(?P<in_id>[0-9]+)/$', views.common_edit, name='common_edit'),
    url(r'^common_del/(?P<in_id>[0-9]+)/$', views.common_del, name='common_del'),
    url(r'^common_run/(?P<in_id>[0-9]+)/$', views.common_run, name='common_run'),
    #todo webssh
    url(r'^webssh/(?P<s_id>[0-9]+)/$', views.asset_batch_import, name='webssh'),

]
