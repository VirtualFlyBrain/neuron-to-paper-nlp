import os
from decimal import Decimal
from pmc_utils import read_csv_to_dict, write_mentions_to_file, clean_folder
from template_generator import generate_publications_robot_template, generate_linkings_robot_template

import spacy
import scispacy
from scispacy.linking import EntityLinker
from scispacy.linking_utils import KnowledgeBase
from scispacy.candidate_generation import DEFAULT_PATHS, DEFAULT_KNOWLEDGE_BASES
from scispacy.candidate_generation import (
    CandidateGenerator,
    LinkerPaths
)

CONFIDENCE_THRESHOLD = 0.85

DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../data")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../output/brief_85_2/")
PUBLICATION_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../robot_templates/publication.tsv")
LINKING_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../robot_templates/linking.tsv")

IGNORED_EXTENSIONS = ("_tables.tsv", "_metadata.tsv")

FBBT_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar.jsonl")
nmslib_index = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/nmslib_index.bin")
concept_aliases = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/concept_aliases.json")
tfidf_vectorizer = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/tfidf_vectorizer.joblib")
tfidf_vectors_sparse = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/tfidf_vectors_sparse.npz")


CustomLinkerPaths_FBBT = LinkerPaths(
    ann_index=nmslib_index,
    tfidf_vectorizer=tfidf_vectorizer,
    tfidf_vectors=tfidf_vectors_sparse,
    concept_aliases_list=concept_aliases
)


class FBBTKnowledgeBase(KnowledgeBase):
    def __init__(
        self,
        file_path: str = FBBT_JSON,
    ):
        super().__init__(file_path)


# Admittedly this is a bit of a hack, because we are mutating a global object.
# However, it's just a kind of registry, so maybe it's ok.
DEFAULT_PATHS["fbbt"] = CustomLinkerPaths_FBBT
DEFAULT_KNOWLEDGE_BASES["fbbt"] = FBBTKnowledgeBase

linker = CandidateGenerator(name="fbbt")


def main():
    """
    Loads the pre-trained embedding model and processes pmc files existing in the data folder. As an output generates
    new entity linking tables in the data folder.
    """
    nlp = load_model()

    # process_test_sentence(nlp)
    all_data = process_data_files(nlp)

    pmcid_doi_mapping = generate_publications_robot_template(DATA_FOLDER, PUBLICATION_TEMPLATE)
    generate_linkings_robot_template(all_data, pmcid_doi_mapping, LINKING_TEMPLATE)
    write_linkings_to_tsv(all_data)


def load_model():
    nlp = spacy.load("en_core_sci_sm")
    nlp.add_pipe("scispacy_linker",
                 config={"resolve_abbreviations": True, "linker_name": "fbbt", "threshold": CONFIDENCE_THRESHOLD})
    return nlp


def process_test_sentence(nlp):
    """
    Runs entity linking on a basic test sentence.
    :param nlp: embedding model
    :return:
    """
    # sentence = "The metameric furrows and MesEc that forms between segments during embryonic stage 11 and persists to the " \
    #            "larval stage (Campos-Ortega and Hartenstein, 1985). Any tracheal lateral trunk anterior branch primordium " \
    #            "(FBbt:00000234) that is part of some metathoracic tracheal primordium (FBbt:00000188)."
    sentence = "The suppression of male and female sexual behaviors depends on the secretion of the neuropeptide DSK-2, which then acts on one of its receptors CCKLR-17D3 that is expressed in many fru^M neurons including P1 neurons and the mushroom bodies."
    mentions = analyze_sentence(nlp, sentence)
    mentions = process_sentence(nlp, sentence)
    for mention in mentions:
        print(mention)


def process_data_files(nlp):
    """
    Processes all files in the data folder and generates result tables.
    :param nlp: entity linking model.
    """
    clean_folder(OUTPUT_FOLDER)
    data_files = sorted(os.listdir(DATA_FOLDER))

    all_data = dict()
    for filename in data_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        if os.path.isfile(file_path) and not filename.endswith(IGNORED_EXTENSIONS):
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            all_mentions = list()
            for row in table:
                record = table[row]
                mentions = process_sentence(nlp, record["text"])
                for mention in mentions:
                    mention["file_name"] = str(filename).split(".")[0].split("_")[0]
                    if mention not in all_mentions:
                        all_mentions.append(mention)

            file_name = all_mentions[0]["file_name"]
            if file_name in all_data:
                existing_data = all_data[file_name]
                existing_data.extend(all_mentions)
            else:
                all_data[file_name] = all_mentions
    return all_data





def write_linkings_to_tsv(all_data):
    """
    Writes entity linking results a plain tsv file.
    :param all_data: entity linking results
    """
    for file_name in all_data:
        output_path = OUTPUT_FOLDER + file_name + ".tsv"
        data = all_data[file_name]
        unique = [i for n, i in enumerate(data) if i not in data[n + 1:]]
        sorted_data = sorted(unique, key=lambda x: str(x["mention_text"]).lower())
        write_mentions_to_file(output_path, sorted_data, append=False)


def is_already_mentioned(mentions, text):
    """
    Checks if text is already mentioned in the same sentence.
    :param mentions: list of existing mentions.
    :param text: new mention to evaluate
    :return: True id already mentioned, False otherwise
    """
    for mention in mentions:
        if mention["mention_text"] == text:
            return True
    return False


def process_sentence(nlp, sentence):
    """
    Processes a sentence to link entities.
    :param nlp: embedding model
    :param sentence: sentence to process
    :return: list of mentions (entity linking results)
    """
    doc = nlp(sentence)
    mentions = list()
    for ent in doc.ents:
        if ent._.kb_ents:
            highest_confidence = Decimal(0)
            for entity in ent._.kb_ents:
                entity_id = entity[0]
                confidence = Decimal(entity[1])
                if confidence > highest_confidence:
                    highest_confidence = confidence
                if confidence >= (highest_confidence - Decimal(0.1)):
                    linking = linker.kb.cui_to_entity[entity_id]
                    mentions.append({
                        "mention_text": ent.text,
                        # "sentence": sentence,
                        "candidate_entity_iri": entity_id,
                        "candidate_entity_label": linking.canonical_name,
                        "candidate_entity_aliases": ",".join(linking.aliases),
                        "confidence": str(confidence)
                    })
    return mentions


def analyze_sentence(nlp, sentence):
    """
    Processes a sentence to link entities and prints all mention-linking options for analysis.
    :param nlp: embedding model
    :param sentence: sentence to process
    :return: list of mentions (entity linking results)
    """
    doc = nlp(sentence)
    mentions = list()
    for ent in doc.ents:
        if ent._.kb_ents:
            print("Mention : " + ent.text)
            for fbbt_ent in ent._.kb_ents:
                print("----------")
                print(fbbt_ent)
                linking = linker.kb.cui_to_entity[fbbt_ent[0]]
                print(linker.kb.cui_to_entity[fbbt_ent[0]])
            print("********")
    return mentions


if __name__ == "__main__":
    main()
