import os
import unittest
from template_generator import generate_publications_robot_template
from pmc_utils import read_csv_to_dict


DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../data")
PUBLICATION_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_outputs/publication.tsv")


class RobotTemplateGeneratorCase(unittest.TestCase):

    def setUp(self):
        if os.path.isfile(PUBLICATION_TEMPLATE):
            os.remove(PUBLICATION_TEMPLATE)

    def test_publications_template(self):
        generate_publications_robot_template(DATA_FOLDER, PUBLICATION_TEMPLATE)
        table = read_csv_to_dict(PUBLICATION_TEMPLATE, delimiter="\t")[1]

        self.assertEqual(8, len(table.keys()))  # including robot template row
        self.assertTrue("https://doi.org/10.1038/s41467-019-12758-6" in table.keys())
        data = table["https://doi.org/10.1038/s41467-019-12758-6"]
        self.assertEqual("PMC6800437", data["PMCID"])
        self.assertEqual("Shunfan Wuet al., 2019", data["Label"])
