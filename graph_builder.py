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

def gen_graph(name, source_list):
    """ 
    Generate Graph
    """
    graph = Digraph(name)
    graph.attr("node", shape="box")
    graph.attr("node", image="./images/vEOS_img.png")
    graph.attr("edge", arrowhead="none")
    graph.format = "png"
    graph.graph_attr["splines"] = "ortho"
    # Generate Edge Relationships
    for edges in source_list:
        node1, node2 = edges
        graph.edge(node1, node2)
    rendered = Source(graph)
    rendered.render(filename="site")
    return rendered
