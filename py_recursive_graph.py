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
from yaml import dump,load, SafeDumper
from yaml.loader import FullLoader
import graph_builder as graph
from tqdm import tqdm


class NoAliasDumper(SafeDumper):
    def ignore_aliases(self, data):
        return True
    def increase_indent(self, flow=False, indentless=False):
        return super(NoAliasDumper, self).increase_indent(flow, False)

def build_sites(results, nornir_session):
    dict_output = {} 
    for result in results.keys():
        host = str(nornir_session.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        dict_output[site_id] = {}
    return dict_output

def init_nornir(username, password):
    nr = InitNornir(config_file="config/config.yml")
    nr.inventory.defaults.username = username
    nr.inventory.defaults.password = password
    with tqdm(total=len(nr.inventory.hosts)) as progress_bar:
        results = nr.run(task=get_data_task, progress_bar=progress_bar)
    hosts_failed = list(results.failed_hosts.keys())
    if hosts_failed != []:
        print(f"Authentication Failed: {list(results.failed_hosts.keys())}")
    return nr, results

def get_data_task(task, progress_bar):
    """
    Task to send commands to Devices via Nornir/Scrapli
    """
    commands =["show cdp neighbors detail"]
    data_results = task.run(task=send_commands, commands=commands)
    progress_bar.update()
    for data_result in data_results:
        for data, command in zip(data_result.scrapli_response, commands):
            task.host[command.replace(" ","_")] = data.genie_parse_output()

def rebuild_inventory(results, input_dict, nornir_session):
    """ Rebuild inventory file from CDP output on core switches """
    output_dict = {}
    for result in results.keys():
        host = str(nornir_session.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        input_dict[site_id][host] = {}
        input_dict[site_id][host] = dict(nornir_session.inventory.hosts[result])
        if input_dict[site_id][host] != {}:
            for index in input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"]:
                device_id = input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]["device_id"].lower().replace(config('DOMAIN_NAME_1'), '').replace(config('DOMAIN_NAME_2'), '').split("(")
                device_id = device_id[0]
                if "management_addresses" != {}:
                    device_ip = list(input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]["management_addresses"].keys())
                if "entry_addresses" in input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]:
                    device_ip = list(input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]["entry_addresses"].keys())
                if "interface_addresses" in input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]:
                    device_ip = list(input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]["interface_addresses"].keys())
                if device_ip:
                    device_ip = device_ip[0]
                output_dict[device_id] = {}
                output_dict[device_id]["hostname"] = device_ip
                if "NX-OS" in input_dict[site_id][host]["show_cdp_neighbors_detail"]["index"][index]["software_version"]:
                    output_dict[device_id]["groups"] = ["nxos_devices"]
                else:
                    output_dict[device_id]["groups"] = ["ios_devices"]
    for key, _ in output_dict.copy().items():
        if output_dict[key]["hostname"] != []:
            ip_address = ipaddress.IPv4Address(output_dict[key]["hostname"])
            if ip_address.is_global:
                output_dict.pop(key, None)
        else:
            output_dict.pop(key, None)
    return output_dict

def main():
    ### PROGRAM VARIABLES ###
    username = input("Username: ")
    password = getpass(prompt="Password: ", stream=None)
    tmp_dict_output = {} 
    inv_path_file = Path("inventory/") / "hosts.yml"   
    diagrams_path = Path("diagrams/")
    cdp_tuples_list = []

    ### INITIALIZE NORNIR ###
    """
    Fetch sent command data, format results, and put them in a dictionary variable
    """
    ### FIRST LEVEL ###
    print("Initializing connections to devices...")
    nr, results = init_nornir(username, password)

    print("Parsing generated output...")
    ### CREATE SITE ID DICTIONARIES ###
    tmp_dict_output = build_sites(results, nr)

    ### REBUILD INVENTORY FILE BASED ON THE NEIGHBOR OUTPUT ###    
    host_dict = rebuild_inventory(results, tmp_dict_output, nr)
    host_yaml = dump(host_dict, default_flow_style=False)
    print("Rebuild FIRST Inventory ...")
    with open(inv_path_file, "a") as open_file:
        open_file.write("\n" + host_yaml)

    ### SECOND LEVEL ###
    print("Initializing connections to devices in SECOND inventory file...")
    nr, results = init_nornir(username, password)

    ### CREATE SITE ID DICTIONARIES ###
    print("Parsing generated output...")
    tmp_dict_output = build_sites(results, nr)
    sec_host_dict = rebuild_inventory(results, tmp_dict_output, nr)

    ### MERGE YAML OBJECTS TO UPDATE INVENTORY FILE ###
    print("Rebuild SECOND Inventory ...")
    with open(inv_path_file) as f:
        inv_dict = load(f, Loader=FullLoader )
    inv_tmp = {**sec_host_dict, **inv_dict}
    yaml_inv = dump(inv_tmp, default_flow_style=False)
    with open(inv_path_file, "w+") as open_file:
        open_file.write("\n" + yaml_inv)

    ### THIRD LEVEL ###
    print("Initializing connections to devices in THIRD inventory file...")
    nr, results = init_nornir(username, password)  
    
    ### CREATE SITE ID DICTIONARIES ###
    print("Parsing generated output...")
    tmp_dict_output = build_sites(results, nr)
    third_host_dict = rebuild_inventory(results, tmp_dict_output, nr)
    print("Rebuild THIRD Inventory ...")
    with open(inv_path_file) as f:
        inv_dict = load(f, Loader=FullLoader )
    inv_final = {**third_host_dict, **inv_dict}
    yaml_inv = dump(inv_final, default_flow_style=False)
    with open(inv_path_file, "w+") as open_file:
        open_file.write("\n" + yaml_inv)
    
    print("Initializing connections to devices in FINAL inventory file...")
    nr, results = init_nornir(username, password)      
    ### MERGE YAML OBJECTS TO UPDATE INVENTORY FILE ###
    print("Parse data from FINAL Inventory")
    inv_dict_output = build_sites(results, nr)
    for result in results.keys():
        host = str(nr.inventory.hosts[result])
        site_id = host.split("-")
        site_id = site_id[0]
        inv_dict_output[site_id][host] = {}
        inv_dict_output[site_id][host] = dict(nr.inventory.hosts[result])
    ### CREATE TUPPLES LIST ###
    print("Generating Graph Data...")
    for site in inv_dict_output:
        cdp_tuple_list = []  
        for host in inv_dict_output[site]:
            neighbor_tuple = ()
            if inv_dict_output[site][host] != {}:
                for index in inv_dict_output[site][host]["show_cdp_neighbors_detail"]["index"]:
                    neighbor = inv_dict_output[site][host]["show_cdp_neighbors_detail"]["index"][index]["device_id"].split(".")
                    neighbor = neighbor[0]
                    hostname = host.split("(")
                    hostname = hostname[0]
                    neighbor_tuple = (hostname, neighbor)
                    cdp_tuple_list.append(neighbor_tuple)
        if cdp_tuple_list:
            cdp_tuples_list.append(cdp_tuple_list)
    """    
    Generate Graph
    """
    print(f"Generating Diagrams...{diagrams_path}")
    ### GENERATE GRAPH EDGES CDP NEIGHBORS ###
    for cdp_tuple in cdp_tuples_list:
        site_id = cdp_tuple[0][0].split("-")
        site_id = site_id[0]
        site_path = diagrams_path / f"{site_id}_site"
        graph.gen_graph(f"{site_id}_site", cdp_tuple, site_path)

if __name__ == '__main__':
    main()