#!/usr/bin/env python3
import matplotlib.cm as cm  # Add this import
import matplotlib.pyplot as plt
import networkx as nx
import rdflib


def calculate_centrality_measures(graph):
    """
    Calculate various centrality measures for the graph.

    Args:
        graph (nx.MultiDiGraph): Input graph

    Returns:
        dict: Dictionary containing different centrality measures
    """
    centrality_measures = {
        'degree_centrality': nx.degree_centrality(graph),
        'in_degree_centrality': nx.in_degree_centrality(graph),
        'out_degree_centrality': nx.out_degree_centrality(graph),
        # 'eigenvector_centrality': nx.eigenvector_centrality(graph, max_iter=300),
        'pagerank': nx.pagerank(graph),
        'betweenness_centrality': nx.betweenness_centrality(graph),
        'closeness_centrality': nx.closeness_centrality(graph)
    }

    return centrality_measures


def extract_subgraph_by_hops(graph, center_node, max_hops):
    """
    Extract a subgraph around a center node within a specified number of hops.

    Args:
        graph (nx.MultiDiGraph): Original graph
        center_node (str): Node to center the subgraph around
        max_hops (int): Maximum number of hops from the center node

    Returns:
        nx.MultiDiGraph: Subgraph within specified hop distance
    """
    # If center node not in graph, return empty graph
    if center_node not in graph:
        print(f"Warning: Center node '{center_node}' not found in the graph.")
        return nx.MultiDiGraph()

    # Use breadth-first search to find nodes within max_hops
    nodes_to_include = {center_node}
    frontier = [(center_node, 0)]

    while frontier:
        current_node, current_hop = frontier.pop(0)

        # If we've reached max hops, skip
        if current_hop >= max_hops:
            continue

        # Find all neighbors (both in and out)
        neighbors_out = list(graph.successors(current_node))
        neighbors_in = list(graph.predecessors(current_node))

        for neighbor in set(neighbors_out + neighbors_in):
            if neighbor not in nodes_to_include:
                nodes_to_include.add(neighbor)
                frontier.append((neighbor, current_hop + 1))

    # Create a subgraph with these nodes
    return graph.subgraph(nodes_to_include)


def rdf_to_advanced_graph(turtle_data,
                          output_png='rdf_network.png',
                          node_size_func=None,
                          node_color_func=None,
                          _edge_width_func=None,
                          layout_algorithm='spring',
                          figure_size=(20, 15),
                          dpi=300,
                          filter_predicates=None,
                          max_nodes=500,
                          center_node=None,
                          max_hops=2,
                          centrality_measure='degree'):
    """
    Convert an RDF Turtle file to an advanced network graph PNG.

    Args:
        turtle_data (str): Path to the input RDF Turtle file
        output_png (str, optional): Path for the output PNG file
        node_size_func (callable, optional): Function to determine node size
        node_color_func (callable, optional): Function to determine node color
        _edge_width_func (callable, optional): Function to determine edge width
        layout_algorithm (str, optional): Graph layout algorithm
            Options: 'spring', 'kamada_kawai', 'spectral', 'circular'
        figure_size (tuple, optional): Figure size (width, height) in inches
        dpi (int, optional): Dots per inch for the output image
        filter_predicates (list, optional): List of predicates to include/exclude
        max_nodes (int, optional): Maximum number of nodes to render
        center_node (str, optional): Node to center the graph around
        max_hops (int, optional): Maximum hops from center node
        centrality_measure (str, optional): Centrality measure for sizing/coloring
    """
    # Create a graph
    g = rdflib.Graph()

    # Parse the Turtle file
    g.parse(data=turtle_data, format='turtle')

    # Create a more versatile MultiDiGraph
    nx_graph = nx.MultiDiGraph()

    # Track node frequencies for potential sizing
    node_frequencies = {}

    # Add nodes and edges from RDF graph
    for s, p, o in g:

        # Convert URIs and literals to strings for readability
        subject = str(s).split("#")[-1]
        predicate = str(p).split("#")[-1]
        object = str(o).split("#")[-1]

        # Skip if filtering predicates is specified
        if filter_predicates and predicate not in filter_predicates:
            continue

        # Track node frequencies
        node_frequencies[subject] = node_frequencies.get(subject, 0) + 1
        node_frequencies[object] = node_frequencies.get(object, 0) + 1

        # Add nodes
        nx_graph.add_node(subject)
        nx_graph.add_node(object)

        # Add edge with predicate as label
        nx_graph.add_edge(subject, object, predicate=predicate)

    # Extract subgraph around a specific node
    if center_node is not None:
        # Find all nodes within max_hops distance from center_node
        nx_graph = extract_subgraph_by_hops(nx_graph, center_node, max_hops)
        print(f"Extracted subgraph around {center_node} with {max_hops} hops")

    # Handle max nodes
    if len(nx_graph.nodes) > max_nodes:
        print(f"Warning: Graph has {len(nx_graph.nodes)} nodes. Limiting to {max_nodes}.")
        # Sort nodes by frequency and take top max_nodes
        top_nodes = sorted(node_frequencies, key=node_frequencies.get, reverse=True)[:max_nodes]
        nx_graph = nx_graph.subgraph(top_nodes)

    # Node sizing function
    if node_size_func is None:
        if centrality_measure is None:
            # Default: size based on node frequency
            def node_size_func(node):
                return 100 + (node_frequencies.get(node, 1) * 20)
        else:
            # Choose centrality measure for node sizing
            centrality_measures = calculate_centrality_measures(nx_graph)

            centrality_options = {
                'degree': centrality_measures['degree_centrality'],
                'in_degree': centrality_measures['in_degree_centrality'],
                'out_degree': centrality_measures['out_degree_centrality'],
                # 'eigenvector': centrality_measures['eigenvector_centrality'],
                'pagerank': centrality_measures['pagerank'],
                'betweenness': centrality_measures['betweenness_centrality'],
                'closeness': centrality_measures['closeness_centrality']
            }

            if centrality_measure not in centrality_options:
                raise ValueError(f"Unsupported centrality measure: {centrality_measure}")

            centrality_scores = centrality_options[centrality_measure]

            def node_size_func(node):
                # Scale node size based on centrality
                return 100 + (centrality_scores.get(node, 0) * 5000)

    # Node color function
    if node_color_func is None:
        if centrality_measure is None:
            # Default: color gradient based on node frequency
            def node_color_func(node):
                freq = node_frequencies.get(node, 1)
                return cm.viridis(freq / max(node_frequencies.values()))
        else:
            # Color gradient based on degree centrality
            centrality_measures = calculate_centrality_measures(nx_graph)

            def node_color_func(node):
                # Color gradient based on centrality
                return cm.viridis(centrality_measures['degree_centrality'].get(node, 0))

    # Prepare the plot
    plt.figure(figsize=figure_size, dpi=dpi)

    # Choose layout algorithm
    if layout_algorithm == 'spring':
        pos = nx.spring_layout(nx_graph, k=0.5, iterations=50)
    elif layout_algorithm == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(nx_graph)
    elif layout_algorithm == 'spectral':
        pos = nx.spectral_layout(nx_graph)
    elif layout_algorithm == 'circular':
        pos = nx.circular_layout(nx_graph)
    else:
        raise ValueError(f"Unsupported layout algorithm: {layout_algorithm}")

    # Draw nodes
    nx.draw_networkx_nodes(
        nx_graph,
        pos,
        node_color=[node_color_func(node) for node in nx_graph.nodes()],
        node_size=[node_size_func(node) for node in nx_graph.nodes()],
        alpha=0.7
    )

    # Draw edges
    nx.draw_networkx_edges(
        nx_graph,
        pos,
        edge_color='gray',
        arrows=True,
        arrowsize=10,
        alpha=0.5
    )

    # Draw node labels
    nx.draw_networkx_labels(
        nx_graph,
        pos,
        font_size=8,
        font_weight='bold',
        verticalalignment='center'
    )

    # Remove axis
    plt.axis('off')

    # Save the graph
    plt.tight_layout()
    plt.savefig(output_png, format='png', bbox_inches='tight')
    plt.close()

    print(f"Network graph saved to {output_png}")
    print(f"Total nodes: {nx_graph.number_of_nodes()}")
    print(f"Total edges: {nx_graph.number_of_edges()}")

    return nx_graph
