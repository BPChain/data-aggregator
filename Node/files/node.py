"""I read values from my local blockchain node by using the Web3 Library which uses the nodes RPC-API. Make sure the
    required apis are unlocked in geth. I send the values I read to a server in a specified interval via a http post.
    Important variables are SERVER_ADDRESS and SEND_PERIOD. The values I send can currently be seen in gather_data"""

import time
from web3 import Web3, HTTPProvider
import requests
import netifaces as ni
from functools import reduce
import socket


def connect_to_blockchain():
    web3 = Web3(HTTPProvider('http://localhost:8545'))
    while not web3.isConnected():
        time.sleep(1)
    return web3


def start_mining(web3):
    web3.miner.start(1)


def retrieve_new_blocks_since(number_of_last_sent_block, web3):
    """Gets the newly mined blocks since last send cycle"""
    new_blocks = []
    number_of_last_block = web3.eth.getBlock('latest').number
    if number_of_last_block > number_of_last_sent_block:
        number_of_blocks_to_send = number_of_last_block - number_of_last_sent_block
        for i in range(1, number_of_blocks_to_send + 1):
            new_blocks.append(web3.eth.getBlock(number_of_last_sent_block + i))
        return number_of_last_block, new_blocks
    else:
        return number_of_last_sent_block, new_blocks


def calculate_avg_block_difficulty(blocks_to_send):
    if not blocks_to_send:
        return 0
    else:
        return reduce((lambda accum, block: accum + block.timestamp), blocks_to_send, 0) / len(blocks_to_send)


def calculate_avg_block_time(blocks_to_send, last_sent_block):
    blocks_to_send = [last_sent_block] + blocks_to_send
    #first block might be genesis block with timestamp 0. this has to be catched.
    if len(blocks_to_send) == 1:
        return 0
    else:
        if blocks_to_send[0] is None:
            blocks_to_send.remove(None)
        if len(blocks_to_send) == 1:
            return 0
        deltas = [next.timestamp - current.timestamp for current, next in zip(blocks_to_send, blocks_to_send[1:])]
        return sum(deltas) / len(deltas)


def provide_data_every(n_seconds, web3):
    last_block_number = 0
    while True:
        time.sleep(n_seconds)
        last_sent_block = web3.eth.getBlock(last_block_number) if last_block_number > 0 else None
        new_last_block_number, blocks_to_send = retrieve_new_blocks_since(last_block_number, web3)
        last_block_number = new_last_block_number
        node_data = gather_data(blocks_to_send, last_sent_block, web3)
        print(node_data)
        send_data(node_data)


def gather_data(blocks_to_send, last_sent_block, web3):
    avg_block_difficulty = calculate_avg_block_difficulty(blocks_to_send)
    avg_block_time = calculate_avg_block_time(blocks_to_send, last_sent_block)
    host_id = web3.admin.nodeInfo.id
    hash_rate = web3.eth.hashrate
    gas_price = web3.eth.gasPrice
    is_mining = 1 if web3.eth.mining else 0
    node_data = {'hostId': host_id, 'hashrate': hash_rate, 'gasPrice': gas_price,
                 'avgBlockDifficulty': avg_block_difficulty, "avgBlockTime": avg_block_time, "isMining": is_mining}
    return node_data


def get_localhost_of_host():
    """Gets the platform dependent address which will be localhost on the host. So host can listen to localhost
        and container can send to this address."""
    try:
        #test if we are on a mac. This will resolve only there
        socket.gethostbyname('docker.for.mac.localhost')
        hosts_localhost = 'http://docker.for.mac.localhost:3030'
    except socket.gaierror:
        #if on linux this will be the host on the bridge network.
        ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        split = ip.split('.')
        server_ip = split[0] + '.' + split[1] + '.' + split[2] + '.' + '1'
        hosts_localhost = 'http://' + server_ip + ':3030'
    return hosts_localhost


def send_data(node_data):
    try:
        hosts_localhost = get_localhost_of_host()
        requests.post(hosts_localhost, json=node_data, headers={'content-type':'application/json'}, timeout = 1)
    except requests.Timeout as e:
        print("Connection timed out this should happen because requests lib is strange")
        print("Request should have been sent")
    except requests.exceptions.RequestException as e:
        print(e)
        print('Could not establish connection')


if __name__ == "__main__":
    SEND_PERIOD  = 10
    web3_connector = connect_to_blockchain()
    start_mining(web3_connector)
    provide_data_every(SEND_PERIOD, web3_connector)
