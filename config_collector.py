#!/usr/bin/env python3

"""
A simple script to collect starting/running config and versions, put them into the file.
Store results in the file.

Files:
config_collector.py - main script
connect_to_device.py - includes functions: ping and connect SSH/Telnet to the device
devices.csv - list of IP addresses
devices-result.json - stores results of running script

(C) 2019 Dmitry Golovach
email: dmitry.golovach@outlook.com

"""

# Imports
import os
import time
import datetime
import sys
import re
import ipaddress
import threading
import json
import pandas as pd

# Imports custom created modules
import connect_to_device

# Module "Global" Variables
directory = '/configs_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
f = open('devices-result.csv', 'a', newline='')
sys.tracebacklimit = 0

# Module Functions and Classes
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Print iterations progress
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s \n' % (prefix, bar, percent, suffix), end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


class Device:
    """Creating the class with:

        self.current_ip_address - IP address
        self.current_index - index from devices.csv
        self.version - grep version from the 'show version'command
        self.collect_config_result - result of running config_collection.py sctipt

        Methods:
            def collect_config - main method to collect running/startup config and version
            def init_connection - initiate SSH connection to the device
            def close_connection - close SSH connection to the device
            def write_result - put results in to the devices-result.json file
    """

    def __init__(self, current_ip_address, current_index):
        self.current_ip_address = current_ip_address
        self.current_index = current_index

    def collect_config_ssh(self):
        self.connection.send_command("term len 0")
        startup_config = self.connection.send_command("show startup-config")
        hostname = re.findall('hostname (.*)\n', startup_config)
        show_ver = self.connection.send_command('show version')
        # self.version = re.findall('.* "(.*bin)"\n', show_ver)
        self.version = re.findall('.*"(.*)"\n', show_ver)
        ver_and_config = show_ver + '\n\n\n========== STARTUP CONFIG ==========\n\n\n' + startup_config
        device_path = os.getcwd() + directory + "/" + hostname[0] + '_version_startup-config_' \
                      + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + ".txt"
        with open(device_path, "w+") as f:
            f.write(ver_and_config)

        self.collect_config_result = "OK"
        printProgressBar(2, 3, prefix='Progress: index ' + str(self.current_index), suffix='Complete', length=50)
        return

    def init_connection_ssh(self):
        self.connection = connect_to_device.try_to_connect_ssh(self.current_ip_address)

    def init_connection_telnet(self):
        self.connection = connect_to_device.try_to_connect_telnet(self.current_ip_address)

    def close_connection(self):
        self.connection.disconnect()

    @staticmethod
    def write_result(current_ip_address, version, collect_config_result, current_index, suffix_bar='Complete'):
        dict_result = {
            'ip': current_ip_address,
            'version': version[0],
            'result': collect_config_result,
            'comment': 'Comment OK - ' + str(current_index),
        }
        df_result = pd.DataFrame(dict_result, [current_index])
        df_result.to_csv(f, mode='a', index=False, header=f.tell() == 0)
        printProgressBar(3, 3, prefix='Progress: index ' + str(current_index), suffix=suffix_bar, length=50)
        return


def main(current_ip_address, current_index):
    # Initial call to print 0% progress
    printProgressBar(0, 3, prefix='Progress: index ' + str(current_index), suffix='Complete', length=50)
    ping_result = connect_to_device.ping_device(current_ip_address)
    if not ping_result:
        version = ['N/A']
        collect_config_result = 'Ping failed'
        suffix_bar = 'Failed'
        Device.write_result(current_ip_address, version, collect_config_result, current_index, suffix_bar)
        return
    else:
        device = Device(current_ip_address, current_index)
        device.init_connection_ssh()
        if device.connection == 'Telnet':
            device.init_connection_telnet()
        device.collect_config_ssh()
        device.close_connection()
        device.write_result(device.current_ip_address, device.version, device.collect_config_result,
                            device.current_index)

    return


# Check to see if this file is the "__main__" script being executed
if __name__ == "__main__":
    start_time = time.time()
    os.mkdir(os.getcwd() + directory)
    threads = []
    if len(sys.argv) == 2:
        try:
            ipaddress.ip_address(sys.argv[1])
            # pass only IP address of the device
            current_index = 0
            main(sys.argv[1], current_index)
        except ValueError:
            df = pd.read_csv(sys.argv[1])
            for current_index in df.index:
                thread = threading.Thread(target=main, args=(df['ip'][current_index], current_index))
                threads.append(thread)
                thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()


    else:
        raise SyntaxError("Insufficient arguments.")
    f.write('---'*10 + '\n')
    json.dump(connect_to_device.method, f)
    f.close()
    print(time.time() - start_time)
