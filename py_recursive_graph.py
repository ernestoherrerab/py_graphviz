#! /usr/bin/env python
"""
Script to graph cdp neighborships.
"""
from decouple import config
from getpass import getpass
from pathlib import Path
import ipaddress
from nornir import InitNornir
from nornir_scrapli.tasks import send_commands
from yaml import dump
import graph_builder as graph

def get_data_task(task):
    """
    Task to send commands to Devices via Nornir/Scrapli
    """
    commands =["show cdp neighbors detail"]
    data_results = task.run(task=send_commands, commands=commands)
    for data_result in data_results:
        for data, command in zip(data_result.scrapli_response, commands):
            task.host[command.replace(" ","_")] = data.genie_parse_output()

def neighbor_to_input(output_dict, input_dict):
    """ Generate graph data from devices output """
    for index in input_dict["show_cdp_neighbors_detail"]["index"]:
        device_id = input_dict["show_cdp_neighbors_detail"]["index"][index]["device_id"].lower().replace(config('DOMAIN_NAME_1'), '').replace(config('DOMAIN_NAME_2'), '')
        if "management_addresses" != {}:
            device_ip = list(input_dict["show_cdp_neighbors_detail"]["index"][index]["management_addresses"].keys())
        if "entry_addresses" in input_dict["show_cdp_neighbors_detail"]["index"][index]:
            device_ip = list(input_dict["show_cdp_neighbors_detail"]["index"][index]["entry_addresses"].keys())
        if "interface_addresses" in input_dict["show_cdp_neighbors_detail"]["index"][index]:
            device_ip = list(input_dict["show_cdp_neighbors_detail"]["index"][index]["interface_addresses"].keys())
        device_ip = device_ip[0]
        output_dict[device_id] = {}
        output_dict[device_id]["hostname"] = device_ip
        if "NX-OS" in input_dict["show_cdp_neighbors_detail"]["index"][index]["software_version"]:
            output_dict[device_id]["groups"] = ["nxos_devices"]
        else:
            output_dict[device_id]["groups"] = ["ios_devices"]
    return output_dict

def main():
    ### PROGRAM VARIABLES ###
    username = input("Username: ")
    password = getpass(prompt="Password: ", stream=None)
    tmp_dict_output = {}
    hostfile_dict = {}
    inv_path_file = Path("inventory/") / "hosts.yml"
    diagrams_path = Path("diagrams/")
    cdp_tuples_list = []

    ### INITIALIZE NORNIR ###
    """
    Fetch sent command data, format results, and put them in a dictionary variable
    """
    print("Initializing connections to devices...")
    nr = InitNornir(config_file="config/config.yml")
    nr.inventory.defaults.username = username
    nr.inventory.defaults.password = password
    results = nr.run(task=get_data_task)
    hosts_failed = list(results.failed_hosts.keys())
    if hosts_failed != []:
        print(f"Authentication Failed: {list(results.failed_hosts.keys())}")

    print("Parsing generated output...")
    ### CREATE SITE ID DICTIONARIES ###
    for result in results.keys():
        host = str(nr.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        tmp_dict_output[site_id] = {}    

    ### FILL HOST DATA IN DICTIONARIES ###
    for result in results.keys():
        host = str(nr.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        tmp_dict_output[site_id][host] = {}
        tmp_dict_output[site_id][host] = dict(nr.inventory.hosts[result])
        if tmp_dict_output[site_id][host] != {}:
            graph_input_dict = neighbor_to_input(hostfile_dict, tmp_dict_output[site_id][host])


    ### UPDATE INVENTORY FILE WITH NEIGHBORS DATA 
    print("Updating Inventory Files")
    for key, _ in graph_input_dict.copy().items():
        ip_address = ipaddress.IPv4Address(graph_input_dict[key]["hostname"])
        if ip_address.is_global:
            graph_input_dict.pop(key, None)
    host_yaml = dump(graph_input_dict, default_flow_style=False)
    with open(inv_path_file, "a") as open_file:
        open_file.write("\n" + host_yaml)

    print("Initializing connections to new devices...")
    nr = InitNornir(config_file="config/config.yml")
    nr.inventory.defaults.username = username
    nr.inventory.defaults.password = password
    results = nr.run(task=get_data_task)
    hosts_failed = list(results.failed_hosts.keys())
    if hosts_failed != []:
        print(f"Authentication Failed: {list(results.failed_hosts.keys())}")

    ### CREATE SITE ID DICTIONARIES ###
    for result in results.keys():
        host = str(nr.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        tmp_dict_output[site_id][host] = {}
        tmp_dict_output[site_id][host] = dict(nr.inventory.hosts[result])

    ### CREATE TUPPLES LIST ###
    for site in tmp_dict_output:
        cdp_tuple_list = []  
        for host in tmp_dict_output[site]:
            neighbor_tuple = ()
            if tmp_dict_output[site][host] != {}:
                for index in tmp_dict_output[site][host]["show_cdp_neighbors_detail"]["index"]:
                    neighbor = tmp_dict_output[site][host]["show_cdp_neighbors_detail"]["index"][index]["device_id"].split(".")
                    neighbor = neighbor[0]
                    neighbor_tuple = (host, neighbor)
                    cdp_tuple_list.append(neighbor_tuple)
        cdp_tuples_list.append(cdp_tuple_list)
       
    """    
    Generate Graph
    """
    print("Generating Diagrams...")
    ### GENERATE GRAPH EDGES CDP NEIGHBORS ###
    for cdp_tuple in cdp_tuples_list:
        site_id = cdp_tuple[0][0].split("-")
        site_id = site_id[0]
        site_path = diagrams_path / f"{site_id}_site"
        graph.gen_graph(f"{site_id}_site", cdp_tuple, site_path)

if __name__ == '__main__':
    main()