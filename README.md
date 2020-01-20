# Cisco Config and Version Collector
> A simple script to collect starting/running config and versions, put them into the file.
Store results in the file.

Files:
* config_collector.py - main script
* connect_to_device.py - includes functions: ping and connect SSH/Telnet to the device
* devices.csv - list of IP addresses
* devices-result.csv - stores results of running script

## Table of contents
* [Technologies](#technologies)
* [Setup](#setup)
* [Contact](#contact)

## Technologies
* Python3

## Setup
python config_collector.py <IP address>

python config_collector.py device.csv

Examples:
* python config_collector.py devices.csv
* python config_collector.py 10.10.10.10



## Contact
* Created by Dmitry Golovach
* Web: [https://dagolovachgolovach.com](https://dmitrygolovach.com) 
* Twitter: [@dagolovach](https://twitter.com/dagolovach)
* LinkedIn: [@dmitrygolovach](https://www.linkedin.com/in/dmitrygolovach/)

- feel free to contact me!