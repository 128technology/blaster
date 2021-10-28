#!/usr/bin/env python3

import json
import sys
from io import StringIO
from pexpect import pxssh
from time import sleep
from subprocess import call


ssh_key_filename = '/etc/128technology/ssh/pdc_ssh_key.pub'
authorized_keys_filename = '/etc/128technology/ssh/authorized_keys'


def error(*messages):
    print('ERROR:', *messages)
    disable_systemd_service()
    sys.exit(1)


def info(*messages):
    print('INFO:', *messages)


def read_init(name):
    with open('/etc/128technology/{}.init'.format(name)) as fd:
        return json.load(fd)


def get_nodes(global_init):
    return global_init['init']['control']


def get_this_node(local_init):
    return local_init['init']['id']


def is_ha_node(global_init):
    # HA routers have exactly two nodes
    try:
        return len(get_nodes(global_init)) == 2
    except KeyError:
        return False


def is_first_node(global_init, local_init):
    node_names = sorted(get_nodes(global_init).keys())
    this_node = get_this_node(local_init)
    if this_node == node_names[0]:
        return True
    else:
        return False


def get_remote_node(global_init, local_init):
    nodes = get_nodes(global_init)
    node_names = list(nodes.keys())
    this_node = get_this_node(local_init)
    node_names.remove(this_node)
    remote_name = node_names[0]
    return nodes[remote_name]['host']


def get_num_keys():
    n = 0
    with open(authorized_keys_filename) as fd:
        for line in fd.readlines():
            if line.startswith('ssh-rsa'):
                n += 1
    return n


def read_local_ssh_key():
    info('Reading local ssh key...')
    with open(ssh_key_filename) as fd:
        return fd.read()


def sync_interface_is_up():
    with open('/proc/net/dev') as fd:
        for line in fd.readlines()[2:]:
            interface = line.split(':')[0].strip()
            if interface.startswith('team-'):
                info('Found ha sync interface:', interface)
                return True
    return False


def copy_to_remote_node(local_ssh_key, remote_node, username='t128', password='128tRoutes'):
    remote_ssh_key = ''
    command = 'cat >> {}; cat {}'.format(
        authorized_keys_filename, ssh_key_filename)

    while True:
        try:
            with StringIO() as fd:
                s = pxssh.pxssh(logfile=fd, encoding='utf-8', options={
                            'StrictHostKeyChecking': 'no',
                            'UserKnownHostsFile': '/dev/null'})
                info('Connecting to remote node:', remote_node)
                s.login(remote_node, username, password)
                info('Copy local key to remote...')
                s.sendline('echo 128tRoutes | sudo -S sh -c "echo -n \'{}\' >> {}"'.format(
                    local_ssh_key, authorized_keys_filename))
                s.prompt()   # match the prompt

                print('Get remote key...')
                # reset logfile
                fd.truncate(0)
                s.sendline('cat {}'.format(ssh_key_filename))
                s.prompt()
                fd.seek(0)
                for line in fd.readlines():
                    if line.startswith('ssh-rsa'):
                        remote_ssh_key = line
                s.sendline('history -r')   # clear ssh history
                s.prompt()
                s.logout()
                break
        except pxssh.ExceptionPxssh as e:
            info('Login failed ({}). Trying again in one minute.'.format(e))
            # try again after a minute
            sleep(60)
            continue

    return remote_ssh_key


def append_remote_ssh_key(remote_ssh_key):
    info('Adding remote key to authorized_keys...')
    with open(authorized_keys_filename, 'a') as fd:
        fd.write(remote_ssh_key)


def disable_systemd_service():
    info('Disabling this service...')
    r = call(('systemctl', 'disable', 't128-sync-ha-ssh-keys'))


def main():
    global_init = read_init('global')
    local_init = read_init('local')

    if not is_ha_node(global_init):
        error('This node is not part of an ha router.')

    if is_first_node(global_init, local_init):
        error('This node is the first one in HA cluster.',
             'Synchronization is triggered by the second node.')

    if get_num_keys() > 1:
        error('SSH keys have already been synchronized.')

    local_ssh_key = read_local_ssh_key()
    remote_node = get_remote_node(global_init, local_init)

    while True:
        # wait until sync interface is up
        if not sync_interface_is_up():
            info('Sync interface not yet ready. Sleeping ...')
            sleep(3)
            continue

        # copy local key to remote node and fetch remote key
        remote_ssh_key = copy_to_remote_node(local_ssh_key, remote_node)

        if not remote_ssh_key:
            error('Remote SSH key could not be retrieved.')

        # append remote key to authorized_keys
        append_remote_ssh_key(remote_ssh_key)

        disable_systemd_service()

        info('Done.')
        break


if __name__ == '__main__':
    main()
