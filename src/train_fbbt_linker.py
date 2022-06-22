import os
from scispacy.linking_utils import KnowledgeBase
from scispacy.candidate_generation import create_tfidf_ann_index

FBBT_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/fbbt-cedar.jsonl")
LINKER_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../linker/")


def train_fbbt_linker(kb_json_path):
    kb = KnowledgeBase(kb_json_path)
    create_tfidf_ann_index(LINKER_DIR, kb)


if __name__ == '__main__':
    train_fbbt_linker(FBBT_JSON)
