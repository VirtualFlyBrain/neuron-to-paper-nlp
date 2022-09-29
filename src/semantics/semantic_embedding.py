import os
import gensim

CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../owl2vec/embeddings/fbbt_model")


def filter_outliers(word2vec_embedding_file):
    model = gensim.models.Word2Vec.load(word2vec_embedding_file)


if __name__ == '__main__':
    filter_outliers(CONFIG_FILE)
