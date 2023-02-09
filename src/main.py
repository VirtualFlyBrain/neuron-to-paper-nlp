import os
from decimal import Decimal
from file_utils import read_csv_to_dict, write_mentions_to_file, clean_folder, read_txt_file
from nlp_utils import count_keywords
from template_generator import generate_publications_robot_template, generate_linkings_robot_template
from itertools import islice
from semantics.semantic_embedding import filter_outliers
from ontology_utils import calculate_node_depths

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
# apply a relative threshold based on the highest confidence per mention
RELATIVE_CONFIDENCE_DISPLACEMENT = 0.05
# Merge sentences with the given size and processes all together to build a context
NLP_TEXT_BATCH_SIZE = 50
# Number of maximum entity linking per mention
MAX_LINKING_PER_MENTION = 4
# An entity must be linked >= n times per paper, otherwise it is outlier
MIN_ENTITY_OCCURRENCE_COUNT = 3
# to understand the focus specimens of paper and link specimen related entities primarily
specimen_keywords = ["male", "female", "larval"]
# filter abstract classes and try to link more specific ones. Min distance to root neuron class.
CLASS_DEPTH_THRESHOLD = 1

DATA_FOLDER = os.getenv('DATA_FOLDER', os.path.join(os.path.dirname(os.path.realpath(__file__)), "../data"))
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', os.path.join(os.path.dirname(os.path.realpath(__file__)), "../output/brief_85_4/"))
ONTOLOGY_FOLDER = os.getenv('ONTOLOGY_FOLDER', os.path.join(os.path.dirname(os.path.realpath(__file__)), "../robot_templates"))

PUBLICATION_TEMPLATE = os.path.join(ONTOLOGY_FOLDER, "publication.tsv")
LINKING_TEMPLATE = os.path.join(ONTOLOGY_FOLDER, "linking.tsv")

IGNORED_EXTENSIONS = ("_tables.tsv", "_metadata.tsv")

FBBT_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar.jsonl")
# list of words to ignore in linking
STOPWORDS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/stopwords.txt")

nmslib_index = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/nmslib_index.bin")
concept_aliases = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/concept_aliases.json")
tfidf_vectorizer = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/tfidf_vectorizer.joblib")
tfidf_vectors_sparse = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/tfidf_vectors_sparse.npz")

OWL2VEC_MODEL = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../owl2vec/embeddings/fbbt_model")


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

# class_depths = calculate_node_depths()
specimen_stats = count_keywords(DATA_FOLDER, IGNORED_EXTENSIONS, specimen_keywords)
stopwords = read_txt_file(STOPWORDS)


def main():
    """
    Loads the pre-trained embedding model and processes pmc files existing in the data folder. As an output generates
    new entity linking tables in the data folder.
    """
    nlp = load_model()

    # process_test_sentence(nlp)
    all_data, entity_occurrence_count = process_data_files(nlp)
    # all_data = filter_data_by_neuron_class_distance(all_data)
    all_data = filter_outliers(OWL2VEC_MODEL, all_data, entity_occurrence_count)
    # all_data = filter_outliers_by_scipsacy_embeddings(all_data, nlp)
    # pmcid_doi_mapping = generate_publications_robot_template(DATA_FOLDER, PUBLICATION_TEMPLATE)
    generate_linkings_robot_template(all_data, DATA_FOLDER, LINKING_TEMPLATE)
    write_linkings_to_tsv(all_data)
    print("Outputs generated at: " + OUTPUT_FOLDER)
    print("SUCCESS")


def load_model():
    """
    Loads SciSpacy model.
    :return: NLP model
    """
    nlp = spacy.load("en_core_sci_sm")
    nlp.add_pipe("scispacy_linker",
                 config={"resolve_abbreviations": True, "linker_name": "fbbt", "threshold": CONFIDENCE_THRESHOLD})
    return nlp


def process_data_files(nlp):
    """
    Processes all files in the data folder and generates result tables.
    :param nlp: entity linking model.
    """
    clean_folder(OUTPUT_FOLDER)
    data_files = sorted(os.listdir(DATA_FOLDER))

    all_data = dict()
    all_entity_counts = dict()
    for filename in data_files:
        print("Processing file: " + filename)
        file_path = os.path.join(DATA_FOLDER, filename)
        if os.path.isfile(file_path) and not filename.endswith(IGNORED_EXTENSIONS):
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            all_mentions = list()
            entity_occurrence_count = dict()
            for chunk in chunks(table, NLP_TEXT_BATCH_SIZE):
                batch_process_table(all_mentions, chunk, filename, nlp, entity_occurrence_count)
            if all_mentions:
                file_name = all_mentions[0]["file_name"]
                if file_name in all_data:
                    existing_data = all_data[file_name]
                    existing_data.extend(all_mentions)
                    # paper, captions etc. are processed as separate file, merge their stats
                    all_entity_counts[file_name] = merge_count_dicts(all_entity_counts[file_name], entity_occurrence_count)
                else:
                    all_data[file_name] = all_mentions
                    all_entity_counts[file_name] = entity_occurrence_count

    # filter mentions whose entity linked min n times
    filter_not_frequent_entities(all_data, all_entity_counts)
    return all_data, all_entity_counts


def filter_not_frequent_entities(all_data, all_entity_counts):
    """
    Filter mentions whose entity linked for min n times and confidence < 0.95
    :param all_data: all linking results
    :param all_entity_counts: entity - occurrence count dictionary
    """
    for file_name in all_data:
        all_mentions = all_data[file_name]
        entity_counts = all_entity_counts[file_name]
        # print(file_name)
        # print(entity_counts)
        entities_to_remove = list()
        for entity_id in entity_counts:
            if entity_counts[entity_id] < 5:
                entities_to_remove.append(entity_id)
        # filter related mentions
        all_data[file_name] = list(m for m in all_mentions if m["candidate_entity_iri"] not in entities_to_remove or
                                   Decimal(m["confidence"]) >= 0.95)


def merge_count_dicts(base_stats, new_stats):
    """
    Paper, captions etc. are processed as separate file, merge their stats
    :param base_stats: existing entity occurrence counts dict
    :param new_stats: new entity occurrence counts dict
    :return: merged dict
    """
    for entity_id in new_stats:
        if entity_id in base_stats:
            base_stats[entity_id] = base_stats[entity_id] + new_stats[entity_id]
        else:
            base_stats[entity_id] = new_stats[entity_id]
    return base_stats


def batch_process_table(all_mentions, chunk, filename, nlp, entity_occurrence_count):
    """
    Processes a batch of sentences and links entities.
    :param all_mentions: all entity linking candidates
    :param chunk: batch of rows to process
    :param filename: name of the processed file for logging purposes
    :param nlp: nlp model
    :param entity_occurrence_count: number of occurrences of each linked entities in the file
    :return:
    """
    mention_file = str(filename).split(".")[0].split("_")[0]
    unmentioned_specimens = [spes for spes in specimen_stats[filename] if specimen_stats[filename][spes] < 2]
    batch_text = ""
    for row in chunk:
        if "text" in chunk[row]:
            sentence = chunk[row]["text"]
            batch_text = batch_text + " " + sentence
    mentions = process_sentence(nlp, batch_text.strip())
    filter_mentions_unrelated_with_specimen(mentions, unmentioned_specimens)
    for mention in mentions:
        mention["file_name"] = mention_file
        if mention not in all_mentions:
            all_mentions.append(mention)
        entity_id = mention["candidate_entity_iri"]
        if entity_id not in entity_occurrence_count:
            entity_occurrence_count[entity_id] = 1
        else:
            entity_occurrence_count[entity_id] = entity_occurrence_count[entity_id] + 1


def filter_mentions_unrelated_with_specimen(mentions, unmentioned_specimens):
    """
    Filters mentions that are unrelated with the specimens of the paper.
    :param mentions: all neuron mentions that exists in the paper.
    :param unmentioned_specimens: specimens that are not mentioned in the paper
    :return: filtered mentions that are related with paper specimens
    """
    mentions_in_sentence = set(ment["mention_text"] for ment in mentions)
    for ment in mentions_in_sentence:
        related_mentions = list(m for m in mentions if m["mention_text"] == ment)
        if len(related_mentions) > 1:
            for unmentioned_specimen in unmentioned_specimens:
                for ment_to_check in related_mentions:
                    # if unmentioned_specimen in str(ment_to_check["candidate_entity_label"]).lower().split():
                    if unmentioned_specimen in str(ment_to_check["candidate_entity_label"]).lower() \
                            and ment_to_check in mentions:
                        mentions.remove(ment_to_check)


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
        output_path = os.path.join(OUTPUT_FOLDER, file_name + ".tsv")
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
        if ent._.kb_ents and len(ent.text) > 1 and ent.text.lower() not in stopwords:
            highest_confidence = Decimal(0)
            mention_candidates = list()
            for entity in ent._.kb_ents:
                entity_id = entity[0]
                confidence = Decimal(entity[1])
                if confidence > highest_confidence:
                    highest_confidence = confidence
                linking = linker.kb.cui_to_entity[entity_id]
                # 2-3 letter mentions must exist in the label or synonyms
                mention_text = str(ent.text).replace("neurons", "").replace("neuron", "").strip()
                if len(mention_text) > 4 or mention_text in " ".join(linking.aliases) or mention_text in linking.canonical_name:
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
            filtered_mentions = [m for m in mention_candidates if Decimal(m["confidence"]) >=
                                 highest_confidence - Decimal(RELATIVE_CONFIDENCE_DISPLACEMENT)]
            filtered_mentions = sorted(filtered_mentions, key=lambda m: m['confidence'], reverse=True)
            # get max n linking per mention
            mentions.extend(filtered_mentions[0:MAX_LINKING_PER_MENTION])
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


def filter_data_by_neuron_class_distance(all_data):
    """
    Not using now, also filtering some TPs like 'Drosulfakinin neuron' (FBbt:00048998)
    Aims to  filter abstract classes and try to link more specific ones. Filter classes higher in the ontology hierarchy.
    :param all_data: all linked entities
    :return: filtered linking results
    """
    filtered = dict()
    for file_name in all_data:
        data = all_data[file_name]
        filtered_data = list()
        for n, record in enumerate(data):
            if class_depths[record["candidate_entity_iri"]] > CLASS_DEPTH_THRESHOLD:
                filtered_data.append(record)
            else:
                print(record["candidate_entity_iri"])
        filtered[file_name] = filtered_data

    return filtered


def filter_outliers_by_scipsacy_embeddings(all_data, nlp):
    """
    DEPRECATED: please use filter_outliers which uses OWL2Vec* and performs better.

    Filters based on embedding vector similarities. Tries to understand paper context from high confident exact matches
    and filters rest of the results based on their embedding vector's distance to the context.
    :param all_data: all entity linkings
    :param nlp: nlp module
    :return: filtered entity linkings
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
            similarity = nlp(record["candidate_entity_iri"]).similarity(hc_doc)
            term_similarities[record["candidate_entity_iri"]] = similarity
            all_sims.append(similarity)

        all_sims = sorted(all_sims)
        cutoff_index = len(all_sims) * 10 / 100
        threshold = all_sims[int(cutoff_index)]

        to_remove = [k for k, v in term_similarities.items() if Decimal(v) < Decimal(threshold)]
        filtered[file_name] = [record for record in data if Decimal(record["confidence"]) > 0.995
                               or record["candidate_entity_iri"] not in to_remove]
    return filtered


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


if __name__ == "__main__":
    main()
