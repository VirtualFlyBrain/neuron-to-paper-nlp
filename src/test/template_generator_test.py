import os
import unittest
from template_generator import generate_publications_robot_template
from file_utils import read_csv_to_dict


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
        self.assertTrue("http://flybase.org/reports/FBrf0254421" in table.keys())
        data = table["http://flybase.org/reports/FBrf0254421"]
        self.assertEqual("PMC6800437", data["PMCID"])
        self.assertEqual("Shunfan Wu et al., 2019, Nature Communications", data["Label"])
        self.assertEqual("owl:NamedIndividual", data["TYPE"])
        self.assertEqual("Drosulfakinin signaling in fruitless circuitry antagonizes P1 neurons to regulate sexual arousal in Drosophila", data["title"])
        self.assertEqual("FBrf0254421", data["FlyBase"])
        self.assertEqual("pub", data["nodeLabel"])
        self.assertEqual("10.1038/s41467-019-12758-6", data["DOI"])
