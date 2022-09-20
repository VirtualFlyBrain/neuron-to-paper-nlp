import os
from decimal import Decimal
from pmc_utils import read_csv_to_dict, write_mentions_to_file, clean_folder
from template_generator import generate_publications_robot_template, generate_linkings_robot_template
from evaluation import evaluate_results
from itertools import islice

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
# CONFIDENCE_THRESHOLD = 0.25
# apply a relative threshold based on the highest confidence per mention
RELATIVE_CONFIDENCE_DISPLACEMENT = 0.05
# Merge sentences with the given size and processes all together to build a context
NLP_TEXT_BATCH_SIZE = 50

DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../data")
EVAL_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../evaluation")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../output/brief_85_4/")
PUBLICATION_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../robot_templates/publication.tsv")
LINKING_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../robot_templates/linking.tsv")

IGNORED_EXTENSIONS = ("_tables.tsv", "_metadata.tsv")

FBBT_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar.jsonl")
# list of words to ignore in linking
BLACKLIST = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/black_list.txt")
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

    all_data = filter_outliers(all_data, nlp)
    pmcid_doi_mapping = generate_publications_robot_template(DATA_FOLDER, PUBLICATION_TEMPLATE)
    generate_linkings_robot_template(all_data, pmcid_doi_mapping, LINKING_TEMPLATE)
    write_linkings_to_tsv(all_data)
    evaluate_results(OUTPUT_FOLDER, EVAL_FOLDER)


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
    sentence = "Leveraging these transgenes, we tracked Unc-4 expression in the peripheral nervous system (PNS) and found that Unc-4 is expressed in all progenitors of leg chordotonal neurons (also called sensory organ precursors [SOPs]) and head sense organs in the larvae as well as many adult sensory neurons including chordotonal and bristle sensory neurons in the leg and Johnston’s organ and olfactory neurons in the antenna (Figure 1G-H; Figure 1-figure supplement 1)."
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
            for chunk in chunks(table, NLP_TEXT_BATCH_SIZE):
                batch_process_table(all_mentions, chunk, filename, nlp)

            file_name = all_mentions[0]["file_name"]
            if file_name in all_data:
                existing_data = all_data[file_name]
                existing_data.extend(all_mentions)
            else:
                all_data[file_name] = all_mentions
    return all_data


def batch_process_table(all_mentions, chunk, filename, nlp):
    """
    Chunks data, merges sentences in the chunk and processes all together to build a context
    :param all_mentions:
    :param chunk:
    :param filename:
    :param nlp:
    :return:
    """
    batch_text = ""
    for row in chunk:
        sentence = chunk[row]["text"]
        batch_text = batch_text + " " + sentence
    mentions = process_sentence(nlp, batch_text.strip())
    for mention in mentions:
        mention["file_name"] = str(filename).split(".")[0].split("_")[0]
        if mention not in all_mentions:
            all_mentions.append(mention)


def chunks(data, size=NLP_TEXT_BATCH_SIZE):
    """
    Chunks given dictionary to multiple dictionaries with fixed size
    :param data: dictionary to chunk
    :param size: chunk size
    :return: chunk generator
    """
    it = iter(data)
    for i in range(0, len(data), size):
        yield {k: data[k] for k in islice(it, size)}


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
        if ent._.kb_ents and len(ent.text) > 1 and ent.text.lower() not in blacklist:
            highest_confidence = Decimal(0)
            mention_candidates = list()
            for entity in ent._.kb_ents:
                entity_id = entity[0]
                confidence = Decimal(entity[1])
                if confidence > highest_confidence:
                    highest_confidence = confidence
                linking = linker.kb.cui_to_entity[entity_id]
                # 2-3 letter mentions must exist in the label or synonyms
                if len(ent.text) > 3 or ent.text in " ".join(linking.aliases) or ent.text in linking.canonical_name:
                    mention_candidate = {
                        "mention_text": ent.text,
                        # "sentence": sentence,
                        "candidate_entity_iri": entity_id,
                        "candidate_entity_label": linking.canonical_name,
                        "candidate_entity_aliases": ",".join(linking.aliases),
                        "confidence": str(confidence)
                    }
                    mention_candidates.append(mention_candidate)
            # apply a relative threshold based on the highest confidence
            mentions.extend([m for m in mention_candidates if Decimal(m["confidence"]) >= highest_confidence - Decimal(
                RELATIVE_CONFIDENCE_DISPLACEMENT)])
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


def filter_outliers(all_data, nlp):
    """
    Filters based on embedding vector similarities. Tries to understand paper context from high confident exact matches
    and filters rest of the results based on their embedding vector's distance to the context.
    :param all_data: all linkings
    :param nlp: nlp module
    :return: filtered linlings
    """
    filtered = dict()
    for file_name in all_data:
        data = all_data[file_name]

        # for a mention we only have singe high confidence result
        all_mention_texts = [str(i["mention_text"]).lower() for n, i in enumerate(data)]
        high_confidence = [i["candidate_entity_iri"] for n, i in enumerate(data)
                           if all_mention_texts.count(str(i["mention_text"]).lower()) == 1
                           and Decimal(i["confidence"]) > Decimal(0.89)]

        high_confidence_doc = " ".join(high_confidence)
        hc_doc = nlp(high_confidence_doc)

        term_similarities = dict()
        all_sims = list()
        for n, record in enumerate(data):
            # print(str(record["candidate_entity_iri"]))
            similarity = nlp(record["candidate_entity_iri"]).similarity(hc_doc)
            # print(str(similarity))
            term_similarities[record["candidate_entity_iri"]] = similarity
            all_sims.append(similarity)

        all_sims = sorted(all_sims)
        cutoff_index = len(all_sims) * 10 / 100
        threshold = all_sims[int(cutoff_index)]

        to_remove = [k for k, v in term_similarities.items() if Decimal(v) < Decimal(threshold)]
        filtered[file_name] = [record for record in data if Decimal(record["confidence"]) > 0.995
                               or record["candidate_entity_iri"] not in to_remove]
    return filtered


def read_file(file_path):
    """
    Reads file content line by line into a list
    :param file_path: file path
    :return: list of rows
    """
    with open(file_path) as f:
        lines = f.read().splitlines()
    return lines


if __name__ == "__main__":
    blacklist = read_file(BLACKLIST)
    main()
