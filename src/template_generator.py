import os
import pandas as pd
from file_utils import read_csv_to_dict


DOI_PREFIX = "https://doi.org/"
FBRF_PREFIX = "http://flybase.org/reports/"


def generate_publications_robot_template(data_folder, output_path):
    robot_template_seed = {'ID': 'ID',
                           'TYPE': 'TYPE',
                           'Label': 'LABEL',
                           'title': 'A dc:title',
                           'FlyBase': 'A neoc:FlyBase',
                           'nodeLabel': 'A neoc:nodeLabel',
                           'PMCID': 'A neoc:PMCID',
                           'DOI': 'A neoc:DOI',
                           'year': 'A dc:year',
                           'volume': 'A dc:volume',
                           'pages': 'A dc:pages',
                           'miniref': 'A neoc:miniref',
                           }
    dl = [robot_template_seed]

    data_files = sorted(os.listdir(data_folder))
    pmcid_doi_mapping = dict()
    for filename in data_files:
        file_path = os.path.join(data_folder, filename)
        if os.path.isfile(file_path) and filename.endswith("_metadata.tsv"):
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            metadata = table[1]
            d = dict()
            fbrf_id = metadata["FBrf_ID"]
            if fbrf_id.startswith(FBRF_PREFIX):
                d['ID'] = fbrf_id
            else:
                d['ID'] = FBRF_PREFIX + fbrf_id
            d['TYPE'] = "owl:NamedIndividual"
            d['FlyBase'] = fbrf_id
            d['DOI'] = metadata.get("DOI", "")
            d['nodeLabel'] = "pub"
            d['title'] = metadata["Title"]
            d['PMCID'] = metadata["PMCID"]
            authors = metadata["Authors"].split(",")
            if len(authors) > 1:
                author = authors[0] + " et al."
            else:
                author = authors[0]
            d['Label'] = author
            if "Year" in metadata:
                d['Label'] = d['Label'] + ", " + metadata["Year"]
            if "Journal" in metadata:
                d['Label'] = d['Label'] + ", " + metadata["Journal"]
            d['miniref'] = d['Label']
            if "Year" in metadata:
                d['year'] = metadata["Year"]
            if "Volume" in metadata:
                d['volume'] = metadata["Volume"]
            if "Pages" in metadata:
                d['pages'] = metadata["Pages"]
            dl.append(d)

            pmcid_doi_mapping[d['PMCID']] = d['ID']

    robot_template = pd.DataFrame.from_records(dl)
    robot_template.to_csv(output_path, sep="\t", index=False)

    return pmcid_doi_mapping


def generate_linkings_robot_template(all_data, data_folder, output_path):
    robot_template_seed = {'ID': 'ID',
                           'references': 'AI dc:references SPLIT=|',
                           'typ': '>A dc:typ'
                           }
    pmcid_fbrf_mapping = get_pmcid_fbrf_mapping(data_folder)
    dl = [robot_template_seed]

    neuron_mentions = dict()
    for file_name in all_data:
        data = all_data[file_name]
        for mention in data:
            if mention["candidate_entity_iri"] in neuron_mentions:
                neuron_mentions[mention["candidate_entity_iri"]].add(pmcid_fbrf_mapping[file_name])
            else:
                mentioned_files = set()
                mentioned_files.add(pmcid_fbrf_mapping[file_name])
                neuron_mentions[mention["candidate_entity_iri"]] = mentioned_files

    for neuron_mention in neuron_mentions:
        d = dict()
        d['ID'] = neuron_mention
        d['references'] = "|".join(neuron_mentions[neuron_mention])
        d["typ"] = "nlp"
        dl.append(d)

    robot_template = pd.DataFrame.from_records(dl)
    robot_template.to_csv(output_path, sep="\t", index=False)


def get_pmcid_fbrf_mapping(data_folder):
    pmcid_fbrf_mapping = dict()
    data_files = sorted(os.listdir(data_folder))
    for filename in data_files:
        file_path = os.path.join(data_folder, filename)
        if os.path.isfile(file_path) and filename.endswith("_metadata.tsv"):
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            metadata = table[1]
            print(filename)
            pmcid_fbrf_mapping[metadata["PMCID"]] = FBRF_PREFIX + metadata["FBrf_ID"]
    return pmcid_fbrf_mapping
