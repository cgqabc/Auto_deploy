#!/usr/bin/env python
# -*- coding=utf-8 -*-

from __future__ import absolute_import

import json
import logging
from collections import namedtuple

import re
from ansible import constants
from ansible.errors import AnsibleError
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.host import Host
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars
from ansible.vars.manager import VariableManager

from .log_ansible import AnsibleSaveResult
from .redis_ops import Redis_pool

logger = logging.getLogger('django.ansibleapi')


class HostInventory(Host):
    def __init__(self, host_data):
        self.host_data = host_data
        hostname = host_data.get('hostname') or host_data.get('ip')
        port = host_data.get('port') or 22
        super(HostInventory, self).__init__(hostname, port)
        self.__set_required_variables()
        self.__set_extra_variables()

    def __set_required_variables(self):
        host_data = self.host_data
        self.set_variable('ansible_host', host_data['ip'])
        if host_data.get('port'):
            self.set_variable('ansible_port', host_data['port'])

        if host_data.get('username'):
            self.set_variable('ansible_user', host_data['username'])

        if host_data.get('password'):
            self.set_variable('ansible_ssh_pass', host_data['password'])
        if host_data.get('private_key'):
            self.set_variable('ansible_ssh_private_key_file', host_data['private_key'])

        become = host_data.get("become", False)
        if become:
            self.set_variable("ansible_become", True)
            self.set_variable("ansible_become_method", become.get('method', 'sudo'))
            self.set_variable("ansible_become_user", become.get('user', 'root'))
            self.set_variable("ansible_become_pass", become.get('pass', ''))
        else:
            self.set_variable("ansible_become", False)

    def __set_extra_variables(self):
        for k, v in self.host_data.get('vars', {}).items():
            self.set_variable(k, v)

    def __repr__(self):
        return self.name


class MyInventory(InventoryManager):

    def __init__(self, resource=None):
        self.resource = resource
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        super(MyInventory, self).__init__(self.loader)

    def get_groups(self):
        return self._inventory.groups

    def get_group(self, name):
        return self._inventory.groups.get(name, None)

    def parse_sources(self, cache=False):
        group_all = self.get_group('all')
        ungrouped = self.get_group('ungrouped')

        if isinstance(self.resource, list):
            for host_data in self.resource:
                host = HostInventory(host_data=host_data)
                self.hosts[host_data.get('hostname') or host_data.get('ip')] = host
                groups_data = host_data.get('groups')
                if groups_data:
                    for group_name in groups_data:
                        group = self.get_group(group_name)
                        if group is None:
                            self.add_group(group_name)
                            group = self.get_group(group_name)
                        group.add_host(host)
                else:
                    ungrouped.add_host(host)
                group_all.add_host(host)

        elif isinstance(self.resource, dict):
            for k, v in self.resource.items():
                group = self.get_group(k)
                if group is None:
                    self.add_group(k)
                    group = self.get_group(k)

                if 'hosts' in v:
                    if not isinstance(v['hosts'], list):
                        raise AnsibleError(
                            "You defined a group '%s' with bad data for the host list:\n %s" % (group, v))
                    for host_data in v['hosts']:
                        host = HostInventory(host_data=host_data)
                        self.hosts[host_data.get('hostname') or host_data.get('ip')] = host
                        group.add_host(host)

                if 'vars' in v:
                    if not isinstance(v['vars'], dict):
                        raise AnsibleError("You defined a group '%s' with bad data for variables:\n %s" % (group, v))

                    for x, y in v['vars'].items():
                        self._inventory.groups[k].set_variable(x, y)

    def get_matched_hosts(self, pattern):
        return self.get_hosts(pattern)


class ModelResultsCollector(CallbackBase):

    def __init__(self, *args, **kwargs):
        super(ModelResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.host_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result


class ModelResultsCollectorToSave(CallbackBase):

    def __init__(self, redisKey, logId, *args, **kwargs):
        super(ModelResultsCollectorToSave, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
        self.redisKey = redisKey
        self.logId = logId

    def v2_runner_on_unreachable(self, result):
        for remove_key in ('changed', 'invocation'):
            if remove_key in result._result:
                del result._result[remove_key]
        data = "<font color='#FA8072'>{host} | UNREACHABLE! => {stdout}</font>".format(host=result._host.get_name(),
                                                                                       stdout=json.dumps(result._result,
                                                                                                         indent=4))
        Redis_pool.lpush(self.redisKey, data)
        if self.logId: AnsibleSaveResult.Model.insert(self.logId, data)
        # print data

    def v2_runner_on_ok(self, result, *args, **kwargs):
        for remove_key in ('changed', 'invocation', '_ansible_parsed', '_ansible_no_log'):
            if remove_key in result._result:
                del result._result[remove_key]
        if result._result.has_key('rc') and result._result.has_key('stdout'):
            data = "<font color='green'>{host} | SUCCESS | rc={rc} >> \n{stdout}".format(host=result._host.get_name(),
                                                                                         rc=result._result.get('rc'),
                                                                                         stdout=result._result.get(
                                                                                             'stdout'))
        else:
            data = "<font color='green'>{host} | SUCCESS >> {stdout}</font>".format(host=result._host.get_name(),
                                                                                    stdout=json.dumps(result._result,
                                                                                                      indent=4))
        Redis_pool.lpush(self.redisKey, data)
        if self.logId: AnsibleSaveResult.Model.insert(self.logId, data)
        # print data

    def v2_runner_on_failed(self, result, *args, **kwargs):
        for remove_key in ('changed', 'invocation'):
            if remove_key in result._result:
                del result._result[remove_key]
        if result._result.has_key('rc') and result._result.has_key('stdout'):
            data = "<font color='#DC143C'>{host} | FAILED | rc={rc} >> \n{stdout}</font>".format(
                host=result._host.get_name(), rc=result._result.get('rc'), stdout=result._result.get('stdout'))
        else:
            data = "<font color='#DC143C'>{host} | FAILED! => {stdout}</font>".format(host=result._host.get_name(),
                                                                                      stdout=json.dumps(result._result,
                                                                                                        indent=4))
        Redis_pool.lpush(self.redisKey, data)
        if self.logId: AnsibleSaveResult.Model.insert(self.logId, data)
        # print data


class PlayBookResultsCollectorToSave(CallbackBase):
    CALLBACK_VERSION = 2.0

    def __init__(self, redisKey, logId, *args, **kwargs):
        super(PlayBookResultsCollectorToSave, self).__init__(*args, **kwargs)
        self.task_ok = {}
        self.task_skipped = {}
        self.task_failed = {}
        self.task_status = {}
        self.task_unreachable = {}
        self.task_changed = {}
        self.redisKey = redisKey
        self.logId = logId
        self.taks_check = {}

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self._clean_results(result._result, result._task.action)
        self.task_ok[result._host.get_name()] = result._result
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        for remove_key in ('changed', 'invocation', '_ansible_parsed', '_ansible_no_log', '_ansible_verbose_always'):
            if remove_key in result._result:
                del result._result[remove_key]
        if result._task.action in ('include', 'include_role', '_ansible_parsed', '_ansible_no_log'):
            return
        elif result._result.get('changed', False):
            if delegated_vars:
                msg = "<font color='yellow'>changed: [%s -> %s]</font>" % (
                    result._host.get_name(), delegated_vars['ansible_host'])
            else:
                msg = "<font color='yellow'>changed: [%s]</font>" % result._host.get_name()
        else:
            if delegated_vars:
                msg = "<font color='green'>ok: [%s -> %s]</font>" % (
                    result._host.get_name(), delegated_vars['ansible_host'])
            elif result._result.has_key('msg') and result._result.get('msg'):
                msg = "<font color='green'>ok: [{host}] => {stdout}</font>".format(host=result._host.get_name(),
                                                                                   stdout=json.dumps(result._result,
                                                                                                     indent=4))
            else:
                msg = "<font color='green'>ok: [%s]</font>" % result._host.get_name()
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            Redis_pool.lpush(self.redisKey, msg)
            if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
            # print msg

    def v2_runner_on_failed(self, result, *args, **kwargs):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self.task_failed[result._host.get_name()] = result._result
        if 'exception' in result._result:
            msg = result._result['exception'].strip().split('\n')[-1]
            logger.error(msg=msg)
            # print(msg)
            del result._result['exception']
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if delegated_vars:
                msg = "<font color='#DC143C'>fatal: [{host} -> {delegated_vars}]: FAILED! => {msg}</font>".format(
                    host=result._host.get_name(), delegated_vars=delegated_vars['ansible_host'],
                    msg=json.dumps(result._result))
            else:
                msg = "<font color='#DC143C'>fatal: [{host}]: FAILED! => {msg}</font>".format(
                    host=result._host.get_name(), msg=json.dumps(result._result))
            Redis_pool.lpush(self.redisKey, msg)
            if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
            # print msg

    def v2_runner_on_unreachable(self, result):
        self.task_unreachable[result._host.get_name()] = result._result
        msg = "<font color='#DC143C'>fatal: [{host}]: UNREACHABLE! => {msg}</font>\n".format(
            host=result._host.get_name(), msg=json.dumps(result._result))
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_runner_on_changed(self, result):
        self.task_changed[result._host.get_name()] = result._result
        msg = "<font color='yellow'>changed: [{host}]</font>\n".format(host=result._host.get_name())
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_runner_on_skipped(self, result):
        self.task_skipped[result._host.get_name()] = result._result
        msg = "<font color='yellow'>skipped: [{host}]</font>\n".format(host=result._host.get_name())
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            Redis_pool.lpush(self.redisKey, msg)
            if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
            # print msg

    def v2_runner_on_no_hosts(self, task):
        msg = "<font color='#DC143C'>skipping: no hosts matched</font>"
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_playbook_item_on_skipped(self, result):
        msg = "<font color='yellow'>skipping: [%s] => (item=%s)</font>" % (
            result._host.get_name(), result._result['item'])
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        if not name:
            msg = u"<font color='#FFFFFF'>PLAY"
        else:
            msg = u"<font color='#FFFFFF'>PLAY [%s]" % name
        if len(msg) < 80: msg = msg + '*' * (79 - len(msg)) + '</font>'
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def _print_task_banner(self, task):
        msg = "<font color='#FFFFFF'>\nTASK [%s]" % (task.get_name().strip())
        if len(msg) < 80: msg = msg + '*' * (80 - len(msg)) + '</font>'
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._print_task_banner(task)

    def v2_playbook_on_cleanup_task_start(self, task):
        msg = "<font color='#FFFFFF'>CLEANUP TASK [%s]</font>" % task.get_name().strip()
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_playbook_on_handler_task_start(self, task):
        msg = "<font color='#FFFFFF'>RUNNING HANDLER [%s]</font>" % task.get_name().strip()
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_playbook_on_stats(self, stats):
        msg = "<font color='#FFFFFF'>\nPLAY RECAP *********************************************************************</font>"
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            self.task_status[h] = {
                "ok": t['ok'],
                "changed": t['changed'],
                "unreachable": t['unreachable'],
                "skipped": t['skipped'],
                "failed": t['failures']
            }
            f_color, u_color, c_color, s_color, o_color, h_color = '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', 'green', 'green'
            if t['failures'] > 0:
                f_color, h_color = '#DC143C', '#DC143C'
            elif t['unreachable'] > 0:
                u_color, h_color = '#DC143C', '#DC143C'
            elif t['changed'] > 0:
                c_color, h_color = 'yellow', 'yellow'
            elif t['ok'] > 0:
                o_color = 'green'
            elif t["skipped"] > 0:
                s_color = 'yellow'
            msg = """<font color='{h_color}'>{host}</font>\t\t: <font color='{o_color}'>ok={ok}</font>\t<font color='{c_color}'>changed={changed}</font>\t<font color='{u_color}'>unreachable={unreachable}</font>\t<font color='{s_color}'>skipped={skipped}</font>\t<font color='{f_color}'>failed={failed}</font>""".format(
                host=h, ok=t['ok'], changed=t['changed'],
                unreachable=t['unreachable'],
                skipped=t["skipped"], failed=t['failures'],
                f_color=f_color, h_color=h_color,
                u_color=u_color, c_color=c_color,
                o_color=o_color, s_color=s_color
            )
            Redis_pool.lpush(self.redisKey, msg)
            if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
            # print msg

    def v2_runner_item_on_ok(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if result._task.action in ('include', 'include_role'):
            return
        elif result._result.get('changed', False):
            msg = "<font color='yellow'>changed"
        else:
            msg = "<font color='green'>ok"
        if delegated_vars:
            msg += ": [%s -> %s]" % (result._host.get_name(), delegated_vars['ansible_host'])
        else:
            msg += ": [%s]" % result._host.get_name()
        msg += " => (item=%s)</font>" % (json.dumps(self._get_item(result._result)))
        if (
                self._display.verbosity > 0 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
            msg += " => %s</font>" % json.dumps(result._result)
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_runner_item_on_failed(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if 'exception' in result._result:
            msg = result._result['exception'].strip().split('\n')[-1]
            logger.error(msg=msg)
            del result._result['exception']
        msg = "<font color='#DC143C'>failed: "
        if delegated_vars:
            msg += "[%s -> %s]</font>" % (result._host.get_name(), delegated_vars['ansible_host'])
        else:
            msg += "[%s] => (item=%s) => %s</font>" % (
                result._host.get_name(), result._result['item'], self._dump_results(result._result))
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_runner_item_on_skipped(self, result):
        msg = "<font color='yellow'>skipping: [%s] => (item=%s)</font>" % (
            result._host.get_name(), self._get_item(result._result))
        if (
                self._display.verbosity > 0 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
            msg += " => %s</font>" % json.dumps(result._result)
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg

    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        msg = "<font color='#DC143C'>FAILED - RETRYING: %s (%d retries left).</font>" % (
            task_name, result._result['retries'] - result._result['attempts'])
        if (
                self._display.verbosity > 2 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
            msg += "Result was: %s</font>" % json.dumps(result._result, indent=4)
        Redis_pool.lpush(self.redisKey, msg)
        if self.logId: AnsibleSaveResult.PlayBook.insert(self.logId, msg)
        # print msg


class PlayBookResultsCollector(CallbackBase):
    CALLBACK_VERSION = 2.0

    def __init__(self, *args, **kwargs):
        super(PlayBookResultsCollector, self).__init__(*args, **kwargs)
        self.task_ok = {}
        self.task_skipped = {}
        self.task_failed = {}
        self.task_status = {}
        self.task_unreachable = {}
        self.task_changed = {}

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.task_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.task_failed[result._host.get_name()] = result

    def v2_runner_on_unreachable(self, result):
        self.task_unreachable[result._host.get_name()] = result

    def v2_runner_on_skipped(self, result):
        self.task_skipped[result._host.get_name()] = result

    def v2_runner_on_changed(self, result):
        self.task_changed[result._host.get_name()] = result

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            self.task_status[h] = {
                "ok": t['ok'],
                "changed": t['changed'],
                "unreachable": t['unreachable'],
                "skipped": t['skipped'],
                "failed": t['failures']
            }


class ANSRunner(object):

    def __init__(
            self,
            hosts=constants.DEFAULT_HOST_LIST,
            module_name=constants.DEFAULT_MODULE_NAME,
            module_args=constants.DEFAULT_MODULE_ARGS,
            forks=constants.DEFAULT_FORKS,
            timeout=constants.DEFAULT_TIMEOUT,
            pattern="all",
            remote_user=constants.DEFAULT_REMOTE_USER,
            module_path=None,
            connection_type="smart",
            become=None,
            become_method=None,
            become_user=None,
            check=False,
            passwords=None,
            extra_vars=None,
            private_key_file=None,
            listtags=False,
            listtasks=False,
            listhosts=False,
            ssh_common_args=None,
            ssh_extra_args=None,
            sftp_extra_args=None,
            scp_extra_args=None,
            verbosity=None,
            syntax=False,
            redisKey=None,
            logId=None
    ):
        self.Options = namedtuple("Options", [
            'listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
            'module_path', 'forks', 'remote_user', 'private_key_file', 'timeout',
            'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args',
            'become', 'become_method', 'become_user', 'verbosity', 'check',
            'extra_vars', 'diff'
        ]
                                  )
        self.results_raw = {}
        self.pattern = pattern
        self.module_name = module_name
        self.module_args = module_args
        self.gather_facts = 'no'
        self.options = self.Options(
            listtags=listtags,
            listtasks=listtasks,
            listhosts=listhosts,
            syntax=syntax,
            timeout=timeout,
            connection=connection_type,
            module_path=module_path,
            forks=forks,
            remote_user=remote_user,
            private_key_file=private_key_file,
            ssh_common_args=ssh_common_args or "",
            ssh_extra_args=ssh_extra_args or "",
            sftp_extra_args=sftp_extra_args,
            scp_extra_args=scp_extra_args,
            become=become,
            become_method=become_method,
            become_user=become_user,
            verbosity=verbosity,
            extra_vars=extra_vars or [],
            check=check,
            diff=False
        )
        self.redisKey = redisKey
        self.logId = logId
        self.loader = DataLoader()
        self.inventory = MyInventory(resource=hosts)
        self.variable_manager = VariableManager(self.loader, self.inventory)
        self.variable_manager.extra_vars = load_extra_vars(loader=self.loader, options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options, "")
        self.passwords = passwords or {}
    def run_model(self, host_list, module_name, module_args):
        if self.redisKey or self.logId:
            self.callback = ModelResultsCollectorToSave(self.redisKey, self.logId)
        else:
            self.callback = ModelResultsCollector()

        play_source = dict(
            name="Ansible Ad-hoc",
            hosts=host_list,
            gather_facts=self.gather_facts,
            tasks=[dict(action=dict(module=module_name, args=module_args))]
        )
        play = Play().load(play_source, loader=self.loader, variable_manager=self.variable_manager)
        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
                stdout_callback=self.callback
            )
            tqm._stdout_callback = self.callback
            constants.HOST_KEY_CHECKING = False  # 关闭第一次使用ansible连接客户端是输入命令
            tqm.run(play)
        except Exception as err:
            logger.error(msg=err)
        finally:
            if tqm is not None:
                tqm.cleanup()
            if self.loader:
                self.loader.cleanup_all_tmp_files()

    def run_playbook(self, host_list, playbook_path, extra_vars=dict()):
        """
        run ansible palybook
        """
        try:
            if self.redisKey or self.logId:
                self.callback = PlayBookResultsCollectorToSave(self.redisKey, self.logId)
            else:
                self.callback = PlayBookResultsCollector()
            if isinstance(host_list, list):
                extra_vars['host'] = ','.join(host_list)
            else:
                extra_vars['host'] = host_list
            self.variable_manager.extra_vars = extra_vars
            executor = PlaybookExecutor(
                playbooks=[playbook_path], inventory=self.inventory, variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options, passwords=self.passwords,
            )
            executor._tqm._stdout_callback = self.callback
            constants.HOST_KEY_CHECKING = False  # 关闭第一次使用ansible连接客户端是输入命令
            constants.DEPRECATION_WARNINGS = False
            constants.RETRY_FILES_ENABLED = False
            executor.run()
        except Exception as err:
            logger.error(msg=err)
            return False

    def get_model_result(self):
        self.results_raw = {'success': {}, 'failed': {}, 'unreachable': {}}
        for host, result in self.callback.host_ok.items():
            self.results_raw['success'][host] = result._result

        for host, result in self.callback.host_failed.items():
            self.results_raw['failed'][host] = result._result

        for host, result in self.callback.host_unreachable.items():
            self.results_raw['unreachable'][host] = result._result

        return json.dumps(self.results_raw)

    def get_playbook_result(self):
        self.results_raw = {'skipped': {}, 'failed': {}, 'ok': {}, "status": {}, 'unreachable': {}, "changed": {}}

        for host, result in self.callback.task_ok.items():
            self.results_raw['ok'][host] = result

        for host, result in self.callback.task_failed.items():
            self.results_raw['failed'][host] = result

        for host, result in self.callback.task_status.items():
            self.results_raw['status'][host] = result

        for host, result in self.callback.task_changed.items():
            self.results_raw['changed'][host] = result

        for host, result in self.callback.task_skipped.items():
            self.results_raw['skipped'][host] = result

        for host, result in self.callback.task_unreachable.items():
            self.results_raw['unreachable'][host] = result
        return self.results_raw

    def handle_cmdb_data(self, data):
        '''处理setup返回结果方法'''
        data_list = []
        for k, v in json.loads(data).items():
            if k == "success":
                for x, y in v.items():
                    cmdb_data = {}
                    data = y.get('ansible_facts')
                    disk_size = 0
                    cpu = data['ansible_processor'][-1]
                    for k, v in data['ansible_devices'].items():
                        if k[0:2] in ['sd', 'hd', 'ss', 'vd']:
                            disk = int((int(v.get('sectors')) * int(v.get('sectorsize'))) / 1024 / 1024)
                            disk_size = disk_size + disk
                    cmdb_data['serial'] = data['ansible_product_serial'].split()[0]
                    cmdb_data['ip'] = x
                    cmdb_data['cpu'] = cpu.replace('@', '')
                    cmdb_data['ram_total'] = int(data['ansible_memtotal_mb'])
                    cmdb_data['disk_total'] = int(disk_size)
                    cmdb_data['system'] = data['ansible_distribution'] + ' ' + data[
                        'ansible_distribution_version'] + ' ' + data['ansible_userspace_bits']
                    cmdb_data['model'] = data['ansible_product_name'].split(':')[0]
                    cmdb_data['cpu_number'] = data['ansible_processor_count']
                    cmdb_data['vcpu_number'] = data['ansible_processor_vcpus']
                    cmdb_data['cpu_core'] = data['ansible_processor_cores']
                    cmdb_data['hostname'] = data['ansible_hostname']
                    cmdb_data['kernel'] = str(data['ansible_kernel'])
                    cmdb_data['manufacturer'] = data['ansible_system_vendor']
                    if data['ansible_selinux']:
                        cmdb_data['selinux'] = data['ansible_selinux'].get('status')
                    else:
                        cmdb_data['selinux'] = 'disabled'
                    cmdb_data['swap'] = int(data['ansible_swaptotal_mb'])
                    # 获取网卡资源
                    nks = []
                    for nk in data.keys():
                        if re.match(r"^ansible_(eth|bind|eno|ens|em)\d+?", nk):
                            device = data.get(nk).get('device')
                            try:
                                address = data.get(nk).get('ipv4').get('address')
                            except:
                                address = 'unkown'
                            macaddress = data.get(nk).get('macaddress')
                            module = data.get(nk).get('module')
                            mtu = data.get(nk).get('mtu')
                            if data.get(nk).get('active'):
                                active = 1
                            else:
                                active = 0
                            nks.append(
                                {"device": device, "address": address, "macaddress": macaddress, "module": module,
                                 "mtu": mtu, "active": active})
                    cmdb_data['status'] = 0
                    cmdb_data['nks'] = nks
                    data_list.append(cmdb_data)
            elif k == "unreachable":
                for x, y in v.items():
                    cmdb_data = {}
                    cmdb_data['status'] = 1
                    cmdb_data['ip'] = x
                    data_list.append(cmdb_data)
        if data_list:
            return data_list
        else:
            return False

    def handle_cmdb_crawHw_data(self, data):
        data_list = []
        for k, v in json.loads(data).items():
            if k == "success":
                for x, y in v.items():
                    cmdb_data = {}
                    cmdb_data['ip'] = x
                    data = y.get('ansible_facts')
                    cmdb_data['mem_info'] = data.get('ansible_mem_detailed_info')
                    cmdb_data['disk_info'] = data.get('ansible_disk_detailed_info')
                    data_list.append(cmdb_data)
        if data_list:
            return data_list
        else:
            return False

    def handle_model_data(self, data, module_name, module_args=None):
        '''处理ANSIBLE 模块输出内容'''
        module_data = json.loads(data)
        failed = module_data.get('failed')
        success = module_data.get('success')
        unreachable = module_data.get('unreachable')
        data_list = []
        if module_name == "raw":
            if failed:
                for x, y in failed.items():
                    data = {}
                    data['ip'] = x
                    try:
                        data['msg'] = y.get('stdout').replace('\t\t', '<br>').replace('\r\n', '<br>').replace('\t',
                                                                                                              '<br>')
                    except:
                        data['msg'] = None
                    if y.get('rc') == 0:
                        data['status'] = 'succeed'
                    else:
                        data['status'] = 'failed'
                    data_list.append(data)
            elif success:
                for x, y in success.items():
                    data = {}
                    data['ip'] = x
                    try:
                        data['msg'] = y.get('stdout').replace('\t\t', '<br>').replace('\r\n', '<br>').replace('\t',
                                                                                                              '<br>')
                    except:
                        data['msg'] = None
                    if y.get('rc') == 0:
                        data['status'] = 'succeed'
                    else:
                        data['status'] = 'failed'
                    data_list.append(data)

        elif module_name == "ping":
            if success:
                for x, y in success.items():
                    data = {}
                    data['ip'] = x
                    if y.get('ping'):
                        data['msg'] = y.get('ping')
                        data['status'] = 'succeed'
                    data_list.append(data)
        else:
            if success:
                for x, y in success.items():
                    data = {}
                    data['ip'] = x
                    if y.get('invocation'):
                        data['msg'] = "Ansible %s with %s execute success." % (module_name, module_args)
                        data['status'] = 'succeed'
                    data_list.append(data)

            elif failed:
                for x, y in failed.items():
                    data = {}
                    data['ip'] = x
                    data['msg'] = y.get('msg')
                    data['status'] = 'failed'
                    data_list.append(data)

        if unreachable:
            for x, y in unreachable.items():
                data = {}
                data['ip'] = x
                data['msg'] = y.get('msg')
                data['status'] = 'failed'
                data_list.append(data)
        if data_list:
            return data_list
        else:
            return False


if __name__ == '__main__':
    import django, os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SimpleOps.settings")
    django.setup()
    resource = [
        {"ip": "192.168.0.110", "username": u"root", "password": u"123456"},
        # {"ip": "192.168.0.111"},
        # {"ip": "192.168.0.113"},
    ]
    # 要输入ip而不是hostname
    # resource =  {
    #         "dynamic_host": {
    #                     "hosts": [
    #                                 {"ip": "192.168.0.110", "port": "22", "username": "root", "password": "123456"},
    #                                 {"ip": "192.168.0.111", "port": "22", "username": "root", "password": "123456"}
    #                               ],
    #                     "vars": {
    #                              "var1":"ansible",
    #                              "var2":"saltstack"
    #                              }
    #                 }
    #             }
    # rbt = ANSRunner(hosts=resource, redisKey='1',logId="")  # 如果带rediskey参数则是直接保存结果和推送redis
    rbt = ANSRunner(resource)
    rbt.run_model(host_list=["192.168.0.110"], module_name='shell', module_args="who")
    data = rbt.get_model_result()
    print data
#     print data
#     print rbt.handle_model_data(data, 'synchronize', module_args='src=/data/webserver/VManagePlatform/ dest=/data/webserver/VManagePlatform/ compress=yes delete=yes recursive=yes')
# rbt.run_model(host_list=["192.168.1.34","192.168.1.130","192.168.1.1"],module_name='ping',module_args="")
#     rbt.run_playbook(["192.168.1.34","192.168.1.130"],playbook_path='/etc/ansible/api/init/system_init.yml')
#     data = rbt.get_model_result()
#     data = rbt.get_playbook_result()
#     print data
#     print rbt.handle_playbook_data_to_html(data)
# print rbt.handle_model_data(module_name='copy',module_args="src=/root/git.log dest=/tmp/test.txt",data=data)
