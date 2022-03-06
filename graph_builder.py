#! /usr/bin/env python
"""
Module to add visual description to switches
"""

from graphviz import Digraph, Source

def host_list(hosts):
    host_list = []
    for result_host in hosts.keys():
        host_list.append(result_host)
    return host_list

def gen_graph(name, source_list, filename):
    """ 
    Generate Graph
    """
    dot = Digraph(name, format='png')
    dot.attr("node", shape="box")
    dot.attr("node", image="./images/vEOS_img.png")
    dot.attr("edge", arrowhead="none")
    dot.format = "png"
    dot.graph_attr["splines"] = "ortho"
    # Generate Edge Relationships
    for edges in source_list:
        node1, node2 = edges
        dot.edge(node1, node2)
    # RENDER DOT FILE INTO PNG
    dot.render(filename=filename, format="png")
