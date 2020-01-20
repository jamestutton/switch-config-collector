import platform
import paramiko
import netmiko
import subprocess

from local_settings import credentials


def ping_device(current_IP_address):
    try:
        output = subprocess.check_output("ping -{} 1 {}".format('n' if platform.system().lower(
        ) == "windows" else 'c', current_IP_address), shell=True, universal_newlines=True)
        if 'unreachable' in output:
            return False
        else:
            return True
    except Exception:
        return False


def try_to_connect_ssh(current_ip_address):
    for count in range(0, len(credentials['username'])):
        try:
            connection = netmiko.ConnectHandler(device_type='cisco_ios_ssh',
                                                ip=current_ip_address,
                                                username=credentials['username'][count],
                                                password=credentials['password'][count],
                                                secret=credentials['secret'][count],
                                                )
            connection.enable()
            return connection
        except paramiko.AuthenticationException:
            continue
        except:
            return 'Telnet'


def try_to_connect_telnet(current_ip_address):
    for count in range(0, len(credentials['username'])):
        try:
            connection = netmiko.ConnectHandler(device_type='cisco_ios_telnet',
                                                ip=current_ip_address,
                                                username=credentials['username'][count],
                                                password=credentials['password'][count],
                                                secret=credentials['secret'][count])
            connection.enable()
            return connection
        except paramiko.AuthenticationException:
            continue
        except:
            return
