import os
import json
from rdflib import Graph

FBBT_ONT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar-reasoned.owl")
FBBT_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar.jsonl")

OBO_NAMESPACE = "http://purl.obolibrary.org/obo/"


def parse_fbbt_ontology(ontology_path):
    fbbt_graph = Graph()
    fbbt_graph.parse(ontology_path)
    list_fbbt_entities = """
    PREFIX obo: <http://purl.obolibrary.org/obo/>
    PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
    SELECT DISTINCT ?fbbtClass ?id ?label ?aliases ?parent ?definition
    WHERE {
        ?fbbtClass a owl:Class .
        ?fbbtClass rdfs:label ?label .
        ?fbbtClass oboInOwl:id ?id . 
        ?fbbtClass oboInOwl:hasRelatedSynonym ?aliases .
        ?fbbtClass rdfs:subClassOf* ?parent .
        ?fbbtClass obo:IAO_0000115 ?definition .
        FILTER ( strstarts(str(?fbbtClass), "http://purl.obolibrary.org/obo/FBbt_"))
    }"""
    qres = fbbt_graph.query(list_fbbt_entities)

    concept_details = {}    # dictionary of concept_id -> {
                            #                 'concept_id': str,
                            #                 'canonical_name': str
                            #                 'aliases': List[str]
                            #                 'types': List[str]
                            #                 'definition': str
                            # }
    for row in qres:
        if str(row.id) in concept_details:
            concept_info = concept_details[str(row.id)]
        else:
            concept_info = {'concept_id': str(row.id),
                            'canonical_name': str(row.label),
                            'aliases': list(),
                            'types': list(),
                            'definition': str(row.definition)}
            concept_details[str(row.id)] = concept_info

        if str(row.aliases) not in concept_info['aliases']:
            concept_info['aliases'].append(str(row.aliases))

        if str(row.id) not in concept_info['aliases']:
            concept_info['aliases'].append(str(row.id))

        if str(row.parent).startswith(OBO_NAMESPACE):
            parent_short_name = str(row.parent).replace(OBO_NAMESPACE, "").replace("_", ":")
            if parent_short_name not in concept_info['types']:
                concept_info['types'].append(parent_short_name)

    fbbt_graph.close()
    return concept_details


def save_to_json(concept_details, ouput_path):
    print('Exporting to the a jsonl file {} ...'.format(ouput_path))
    with open(ouput_path, 'w') as fout:

        for value in concept_details.values():
            fout.write(json.dumps(value) + "\n")
    print('DONE.')


def owl_2_json(ontology_path, json_output_path):
    concept_details = parse_fbbt_ontology(ontology_path)
    save_to_json(concept_details, json_output_path)


if __name__ == '__main__':
    owl_2_json(FBBT_ONT, FBBT_JSON)
