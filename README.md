This script is used to make a graphical representation of site topologies by using CDP data from the devices located in the inventory file.

There are two versions of the script:

1. py_graph.py - Depends 100% on the inventory file and generates a topology diagram based on the site ID and puts the rendered diagram in the diagrams directory.

2. py_recursive_graph.py - This script requires only a core switch from each site to generate the topology diagram by recreating an inventory file based on the core switches CDP data returned and then running a second CDP data collection on the new inventory file and then creating the topology diagram with the new inventory file. The caveat with this version is that if there are daisy-chained switches, the second level switch will not be queried for CDP.

Ideally, the first script should be used, but it requires a solid inventory SoT.