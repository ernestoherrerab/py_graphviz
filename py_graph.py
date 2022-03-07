#! /usr/bin/env python
"""
Script to graph cdp neighborships.
"""
from getpass import getpass
from pathlib import Path
from nornir import InitNornir
from nornir_scrapli.tasks import send_command
import graph_builder as graph

def get_data_task(task):
    """
    Task to send commands to Devices via Nornir/Scrapli
    """
    cdp_data = task.run(task=send_command, command="show cdp neighbors")
    task.host["facts"] = cdp_data.scrapli_response.genie_parse_output()

def main():
    ### PROGRAM VARIABLES ###
    username = input("Username: ")
    password = getpass(prompt="Password: ", stream=None)
    tmp_dict_output = {}
    diagrams_path = Path("diagrams/")
    cdp_tuples_list = []

    ### INITIALIZE NORNIR ###
    """
    Fetch sent command data, format results, and put them in a dictionary variable
    """
    try:
        print("Initializing connections to devices...")
        nr = InitNornir(config_file="config/config.yml", core={"raise_on_error": True})
        nr.inventory.defaults.username = username
        nr.inventory.defaults.password = password
        results = nr.run(task=get_data_task)
    except KeyError as e:
        print(f"Connection to device failed: {e}")

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

    ### CREATE TUPPLES LIST ###
    for site in tmp_dict_output:
        cdp_tuple_list = []  
        for host in tmp_dict_output[site]:
            neighbor_tuple = ()
            for index in tmp_dict_output[site][host]["facts"]["cdp"]["index"]:
                neighbor = tmp_dict_output[site][host]["facts"]["cdp"]["index"][index]["device_id"].split(".")
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