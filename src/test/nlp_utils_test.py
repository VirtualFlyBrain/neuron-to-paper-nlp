import unittest
from nlp_utils import generate_phrase_variances


class NLPUtilsCase(unittest.TestCase):

    def test_alias_variances(self):
        aliases = list(generate_phrase_variances("dsx-pC1 (female)"))
        print(aliases)
        self.assertTrue("pC1" in aliases)
        self.assertTrue("dsx-pC1" in aliases)
        self.assertTrue("dsx pC1" in aliases)
        self.assertTrue("dsx-pC1 (female)" in aliases)

        self.assertTrue("adult doublesex pC1e neuron" in generate_phrase_variances("adult doublesex pC1e (female) neuron (dsx)"))

        self.assertTrue("P1" in generate_phrase_variances("P1 neuron"))
        self.assertTrue("P1" in generate_phrase_variances("P1 neurons"))

        self.assertTrue("MP1a" in generate_phrase_variances("adult Drosulfakinin MP1a neuron"))


if __name__ == '__main__':
    unittest.main()
