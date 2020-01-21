# Cisco Config and Version Collector
> A simple script to collect starting/running config and versions, put them into the file.
Store results in the file.

Files:
* config_collector.py - main script
* connect_to_device.py - includes functions: ping and connect SSH/Telnet to the device
* devices.csv - list of IP addresses
* devices-result.csv - result of running script

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

## Result
![image-31-552x552](https://user-images.githubusercontent.com/39305133/72814550-d51d9480-3c2a-11ea-991c-5bb23114de5f.png)

## Contact
* Created by Dmitry Golovach
* Web: [https://dagolovachgolovach.com](https://dmitrygolovach.com) 
* Twitter: [@dagolovach](https://twitter.com/dagolovach)
* LinkedIn: [@dmitrygolovach](https://www.linkedin.com/in/dmitrygolovach/)

- feel free to contact me!
