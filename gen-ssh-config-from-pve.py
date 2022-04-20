#!/usr/bin/python3

import os
import sys
import asyncio
import aiohttp
import argparse
import json
import time

tasks = set()
config_file = None
config_path = None
base_url = None
token = None
ssh_key = None

def fatal(msg):
    print(msg, file=sys.stderr)
    os._exit(1)

def get_args():
    global config_path, base_url, token, ssh_key

    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--server", type=str, help="Proxmox server url", required=True)
    parser.add_argument("-t", "--token", type=str, help="Path to token file", required=True)
    parser.add_argument(
        "-c", "--config", type=str, help="Location of generated config", required=True
    )
    parser.add_argument("-k", "--key", type=str, help="Path to identity_file for generated config")
    args = parser.parse_args()

    base_url = args.server

    config_path = os.path.expanduser(args.config)

    try:
        with open(os.path.expanduser(args.token), "r") as token_file:
            token = token_file.read().strip()
    except FileNotFoundError:
        fatal("can't open token file")

    ssh_key = args.key

def append_ssh_config(vmid, hostname, ip):
    config_file.write(
        f"\nHost tve-{hostname} tve--{vmid}\n"
        f"\tHostName {ip}\n"
        "\tUser root\n"
        "\tPort 22\n"
        "\tStrictHostKeyChecking no\n" +
        (f"\tIdentityFile {ssh_key}\n" if ssh_key else "")
    )

async def fetch_json(session, url):
    try:
        response = await session.get(url, allow_redirects=False)
        if response.status == 200:
            return json.loads(await response.text())
        elif response.status//100 == 3:
            fatal("redirection is not allowed")
        return dict()
    except json.decoder.JSONDecodeError:
        return dict()
    except aiohttp.ClientError:
        fatal("http connection error")

async def process_ip(session, node, vmid, vmname):
    try:
        resp_json = await fetch_json(
            session,
            '/api2/json/nodes/' + node + '/qemu/' + str(vmid) + '/agent/network-get-interfaces'
        )
    except asyncio.CancelledError:
        tasks.discard(asyncio.current_task())
        return

    data = resp_json.get('data', None)
    if data != None:
        for interface in data.get('result', ()):
            if interface.get('name', '') in ('eth0', 'ens19'):
                for ip in interface.get('ip-addresses', ()):
                    if ip.get('ip-address-type', '') == 'ipv4':
                        append_ssh_config(vmid, vmname, ip['ip-address'])

    tasks.discard(asyncio.current_task())


async def process_vms(session, node):
    try:
        resp_json = await fetch_json(session, '/api2/json/nodes/' + node + '/qemu')
    except asyncio.CancelledError:
        tasks.discard(asyncio.current_task())
        return

    for vm in resp_json.get('data', ()):
        if vm.get('status', '') == 'running':
            tasks.add(asyncio.create_task(process_ip(session, node, vm['vmid'], vm['name'])))

    tasks.discard(asyncio.current_task())

async def process_nodes():
    token_header = {'Authorization' : ('PVEAPIToken=' + token)}

    session = aiohttp.ClientSession(
        base_url = base_url,
        headers=token_header
    )

    try:
        resp_json = await fetch_json(session, '/api2/json/nodes')

        for node in resp_json.get('data', ()):
            tasks.add(asyncio.create_task(process_vms(session, node['node'])))

        while len(tasks):
            await asyncio.wait(tasks)
    except asyncio.CancelledError:
        print("cancelled", file=sys.stderr)
        for task in tasks:
            task.cancel()
        await asyncio.wait(tasks)

    await session.close()

async def async_main():
    global config_file
    try:
        config_file = open(config_path + ".new", "w")
        await asyncio.wait_for(process_nodes(), 30)
    except asyncio.TimeoutError:
        print("timeout", file=sys.stderr)
    except OSError:
        fatal("can't open config file with write permissions")
    finally:
        config_file.close()

    os.replace(config_path + ".new", config_path)

if __name__ == "__main__":
    get_args()

    start = time.perf_counter()

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)

    if os.path.exists(config_path + ".new"):
        os.remove(config_path + ".new")

    elapsed = time.perf_counter() - start
    print(f"done in {elapsed:.2f}s", file=sys.stderr)
