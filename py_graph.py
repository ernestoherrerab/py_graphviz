#! /usr/bin/env python
"""
Script to graph cdp neighborships.
"""
from decouple import config
from getpass import getpass
from pathlib import Path
from nornir import InitNornir
from nornir_scrapli.tasks import send_command, send_configs_from_file
from nornir_utils.plugins.functions import print_result
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
    for result in results.keys():
        cdp_tuple_list = []
        neighbor_tuple = ()  
        tmp_dict_output = dict(nr.inventory.hosts[result])
        host = str(nr.inventory.hosts[result])
        for index in tmp_dict_output["facts"]["cdp"]["index"]:
            tmp_neighbor = tmp_dict_output["facts"]["cdp"]["index"][index]["device_id"].split(".")
            neighbor = tmp_neighbor[0]
            neighbor_tuple = (host, neighbor)
            cdp_tuple_list.append(neighbor_tuple)
        cdp_tuples_list.append(cdp_tuple_list)

    
    """    
    Generate Graph
    """
    print("Generating Diagrams...")
    # Generate Graph Edges LLDP Neighbors
    for cdp_tuple in cdp_tuples_list:
        site_id = cdp_tuple[0][0].split("-")
        site_id = site_id[0]
        site_path = diagrams_path / f"{site_id}_site"
        graph.gen_graph(f"{site_id}_site", cdp_tuple, site_path)        
  
            

if __name__ == '__main__':
    main()