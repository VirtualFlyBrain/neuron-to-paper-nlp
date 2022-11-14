import numpy as np
import gensim
from gensim.models import KeyedVectors
from decimal import Decimal

MIN_OCCURRENCE_COUNT = 10


def filter_outliers(owl2vec_embedding_file, all_data, entity_occurrence_count):
    """
    Filter outliers based on semantic similarity. Identifies context of the paper and removes unrelated linkings.
    :param owl2vec_embedding_file: semantic embedding model
    :param all_data: all linking results
    :param entity_occurrence_count: entity id - occurrence count dictionary
    """
    model = gensim.models.Word2Vec.load(owl2vec_embedding_file)

    filtered = dict()
    for file_name in all_data:
        # print(file_name)
        data = all_data[file_name]

        # for a mention we only have singe high confidence result
        all_mention_texts = [str(i["mention_text"]).lower() for n, i in enumerate(data)]
        # high_confidence = [i["candidate_entity_iri"] for n, i in enumerate(data)
        #                    if all_mention_texts.count(str(i["mention_text"]).lower()) == 1
        #                    and Decimal(i["confidence"]) > Decimal(0.89)]
        high_confidence = set(i["candidate_entity_iri"] for n, i in enumerate(data)
                              if Decimal(i["confidence"]) > Decimal(0.95))

        context_entities = set()
        paper_context = np.zeros(model.vector_size)
        n = 0
        # print("High Conf Count: " + str(len(high_confidence)))
        counts = sorted(list(c for c in entity_occurrence_count[file_name].values() if c > 1), reverse=True)
        print(counts)
        q1_occurrence = counts[int(len(counts)/4)]
        for entity_iri in high_confidence:
            if entity_occurrence_count[file_name][entity_iri] > q1_occurrence:
                paper_context += model.wv.get_vector(entity_iri.replace("FBbt:", "http://purl.obolibrary.org/obo/FBbt_"))
                context_entities.add(entity_iri)
                n += 1
        print(file_name + "  context size: " + str(n))
        print(file_name + "  : " + str(context_entities))
        paper_context = paper_context / n if n > 0 else paper_context

        term_similarities = dict()
        all_sims = list()
        for n, record in enumerate(data):
            # print(str(record["candidate_entity_iri"]))
            entity_iri = str(record["candidate_entity_iri"]).replace("FBbt:", "http://purl.obolibrary.org/obo/FBbt_")
            entity_embedding = model.wv.get_vector(entity_iri)
            similarity = KeyedVectors.cosine_similarities(paper_context, np.array([entity_embedding]))[0]
            # print(str(similarity))
            term_similarities[record["candidate_entity_iri"]] = similarity
            all_sims.append(similarity)

        all_sims = sorted(all_sims)
        # print("ALLLL:")
        # print(all_sims)
        # print("FILTERED:")
        filteredz = reject_outliers2(np.array(all_sims))
        # print(filteredz.tolist())

        # cutoff_index = len(all_sims) * 10 / 100
        # threshold_old = all_sims[int(cutoff_index)]
        # print("OLD THR: " + str(threshold_old))

        threshold = filteredz[0]
        # print("NEW THR: " + str(threshold))

        to_remove = [k for k, v in term_similarities.items() if Decimal(v) < Decimal(threshold)]
        filtered[file_name] = [record for record in data if Decimal(record["confidence"]) > 0.97
                               or record["candidate_entity_iri"] not in to_remove]
        # values = list()
        # for record in data:
        #     if Decimal(record["confidence"]) > 0.96 or record["candidate_entity_iri"] not in to_remove:
        #         values.append(record)
        #     else:
        #         print(record["candidate_entity_iri"] + "   " + str(term_similarities[record["candidate_entity_iri"]]) + "   " + str(record["confidence"]))
        # filtered[file_name] = values

    return filtered


def reject_outliers(data, m=2):
    """
    if word_score < (mean_score - X*stdev_score):
     is_outlier = True
    :param data: all similarity scores
    :param m: trigger_sensitivity
    :return: data without outliers
    """
    return data[abs(data - np.mean(data)) < m * np.std(data)]


def reject_outliers2(data, m=2.):
    """
    Performs better compared to classical outlier approach. Because, the mean of a distribution will be biased by
    outliers but e.g. the median will be much less. Also, replaces the standard deviation with the median absolute
    distance to the median. Then scales the distances by their (again) median value so that m is on a reasonable
    relative scale.
    :param data: all similarity scores
    :param m: trigger_sensitivity
    :return: data without outliers
    """
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.
    return data[s < m]
