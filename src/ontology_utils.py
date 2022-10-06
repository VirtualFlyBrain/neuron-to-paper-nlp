import os
from rdflib import Graph

FBBT_ONT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar-reasoned.owl")


def calculate_node_depths():
    """
    Calculates every neuron's distance to the root neuron class (FBbt:00005106).
    :return: dictionary of entity_curie-distance to root neuron class
    """
    print("Calculating Fbbt class hierarchy depths...")
    depth_dict = dict()

    fbbt_graph = Graph()
    fbbt_graph.parse(FBBT_ONT)
    list_fbbt_entities = """
    PREFIX obo: <http://purl.obolibrary.org/obo/>
    PREFIX FBbt: <http://purl.obolibrary.org/obo/FBbt_>
    PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?fbbtClass (count(?mid) as ?distance)
    WHERE {
        ?mid rdfs:subClassOf* FBbt:00005106 .
        ?fbbtClass rdfs:subClassOf+ ?mid .
        FILTER ( strstarts(str(?fbbtClass), "http://purl.obolibrary.org/obo/FBbt_")) .
    }
    GROUP BY ?fbbtClass 
    """
    qres = fbbt_graph.query(list_fbbt_entities)

    for row in qres:
        if str(row.fbbtClass) not in depth_dict:
            depth_dict[str(row.fbbtClass).replace("http://purl.obolibrary.org/obo/FBbt_", "FBbt:")] = int(row.distance)

    print("Class hierarchy depths calculated.")
    return depth_dict
