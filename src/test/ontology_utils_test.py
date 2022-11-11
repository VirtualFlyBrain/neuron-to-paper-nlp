import unittest
from ontology_utils import calculate_node_depths
import os
import gensim
from gensim.models import KeyedVectors
import numpy as np

OWL2VEC_MODEL_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../owl2vec/embeddings/fbbt_model")


class OntologyUtilsCase(unittest.TestCase):

    def test_ontology_depth(self):
        node_depths = calculate_node_depths()

        self.assertEqual(1, node_depths["FBbt:00047096"])
        self.assertTrue(node_depths["FBbt:00049443"] > 5)
        self.assertTrue(node_depths["FBbt:00007507"] > 5)
        self.assertTrue(node_depths["FBbt:00003650"] > 5)
        self.assertTrue(node_depths["FBbt:00003652"] > 5)
        self.assertTrue(node_depths["FBbt:00047039"] > 5)

    def test_owl_2_vec_star(self):
        model = gensim.models.Word2Vec.load(OWL2VEC_MODEL_FILE)
        main_entity = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00001987")  # 'abdominal neuron'

        # two direct (L1) child same level
        other1 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00001540")
        other2 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00001474")

        # L2 children
        other3 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00048779")
        # L3 children
        other4 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00048773")
        # L4 children
        other5 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00052045")

        # from other branches (no parent-child relation)
        other6 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00058204")
        other7 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00100662")
        other8 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00050052")
        other9 = model.wv.get_vector("http://purl.obolibrary.org/obo/FBbt_00051422")

        others = np.array([main_entity, other1, other2, other3, other4, other5, other6, other7, other8, other9])

        similarities = KeyedVectors.cosine_similarities(main_entity, others)
        print(similarities)

        self.assertTrue(similarities[0] > 0.999)
        self.assertTrue(all(similarities[1] > x for x in similarities[3:]))
        self.assertTrue(all(similarities[2] > x for x in similarities[3:5]))
        self.assertTrue(similarities[3] > similarities[4])


if __name__ == '__main__':
    unittest.main()
