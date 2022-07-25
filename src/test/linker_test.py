import unittest
from main import load_model, process_sentence


class NLPUtilsCase(unittest.TestCase):

    def test_multiple_linking(self):
        nlp = load_model()
        sentence = "Analysis of the new DskGAL4 and DskLexA using a myr::GFP reporter revealed similar expression " \
                   "patterns, both of which label a subset of neurons in the brain that were previously identified " \
                   "as Dsk-expressing neurons [39], including four pairs of neurons in the medial protocerebrum " \
                   "(two pairs of MP1 and two pairs of MP3 cells), and a few IPCs (Fig 2a and Supplementary Fig 2a)."

        mentions = process_sentence(nlp, sentence)

        phrase_mentions = list(mention for mention in mentions if mention['mention_text'] == 'MP1')
        self.assertEqual(2, len(phrase_mentions))
        linked_labels = (ment['candidate_entity_label'] for ment in phrase_mentions)
        self.assertTrue("MP1a neuron" in linked_labels)
        self.assertTrue("MP1 neuron" in linked_labels)

        phrase_mentions = list(mention for mention in mentions if mention['mention_text'] == 'brain')
        self.assertEqual(3, len(phrase_mentions))
        linked_labels = (ment['candidate_entity_label'] for ment in phrase_mentions)
        self.assertTrue("brain" in linked_labels)
        self.assertTrue("adult cerebral ganglion" in linked_labels)
        self.assertTrue("adult brain" in linked_labels)

    def test_multiple_linking2(self):
        nlp = load_model()
        sentence = "The suppression of male and female sexual behaviors depends on the secretion of the neuropeptide " \
                   "DSK-2, which then acts on one of its receptors CCKLR-17D3 that is expressed in many fru^M " \
                   "neurons including P1 neurons and the mushroom bodies."
        mentions = process_sentence(nlp, sentence)

        phrase_mentions = list(mention for mention in mentions if mention['mention_text'] == 'P1')
        # self.assertEqual(5, len(phrase_mentions))
        linked_labels = (ment['candidate_entity_label'] for ment in phrase_mentions)
        self.assertTrue("prothoracic ventral campaniform sensillum vc1" in linked_labels)
        self.assertTrue("mesothoracic ventral campaniform sensillum vc1" in linked_labels)
        self.assertTrue("metathoracic ventral campaniform sensillum vc1" in linked_labels)
        self.assertTrue("abdominal ventral campaniform sensillum vc1" in linked_labels)
        self.assertTrue("P1 neuron" in linked_labels)

