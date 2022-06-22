import os

from pmc_utils import read_csv_to_dict, write_mentions_to_file, clean_folder

import spacy
import scispacy
from scispacy.linking import EntityLinker
from scispacy.linking_utils import KnowledgeBase
from scispacy.candidate_generation import DEFAULT_PATHS, DEFAULT_KNOWLEDGE_BASES
from scispacy.candidate_generation import (
    CandidateGenerator,
    LinkerPaths
)

LINKING_FILE_EXTENSION = "_linking.tsv"
DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../data")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../output")

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
    nlp = spacy.load("en_core_sci_sm")
    nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": "fbbt", "threshold": 0.85})

    # process_test_sentence(nlp)
    process_data_files(nlp)


def process_test_sentence(nlp):
    """
    Runs entity linking on a basic test sentence.
    :param nlp: embedding model
    :return:
    """
    sentence = "The metameric furrows and MesEc that forms between segments during embryonic stage 11 and persists to the " \
               "larval stage (Campos-Ortega and Hartenstein, 1985). Any tracheal lateral trunk anterior branch primordium " \
               "(FBbt:00000234) that is part of some metathoracic tracheal primordium (FBbt:00000188)."
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
    for filename in data_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        if os.path.isfile(file_path) and LINKING_FILE_EXTENSION not in filename:
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            all_mentions = list()
            for row in table:
                record = table[row]
                mentions = process_sentence(nlp, record["text"])
                for mention in mentions:
                    mention["file_name"] = str(filename).split(".")[0].split("_")[0]
                    if "section" in record:
                        mention["section"] = record["section"]
                    elif "tag" in record:
                        mention["section"] = record["tag"]
                    if "paragraph" in record:
                        mention["paragraph"] = record["paragraph"]
                    elif "label" in record:
                        mention["paragraph"] = record["label"]
                    if "sentence" in record:
                        mention["sentence_num"] = record["sentence"]

                    all_mentions.append(mention)
            output_path = str(file_path).replace("/data/", "/output/")
            output_path = output_path.replace("_captions", "")
            write_mentions_to_file(output_path, all_mentions, append=True)


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
            entity = ent._.kb_ents[0]
            entity_id = entity[0]
            confidence = entity[1]
            linking = linker.kb.cui_to_entity[entity_id]
            if not is_already_mentioned(mentions, ent.text):
                mentions.append({
                    "mention_text": ent.text,
                    "sentence": sentence,
                    "candidate_entity_iri": entity_id,
                    "candidate_entity_label": linking.canonical_name,
                    "candidate_entity_aliases": ",".join(linking.aliases),
                    "confidence": confidence
                })
            # print("Mention : " + ent.text)
            # for fbbt_ent in ent._.kb_ents:
            #     print("----------")
            #     print(fbbt_ent)
            #     linking = linker.kb.cui_to_entity[fbbt_ent[0]]
            #     print(linker.kb.cui_to_entity[fbbt_ent[0]])
            # print("********")
    return mentions


if __name__ == "__main__":
    main()
