import os
from file_utils import read_csv_to_dict
from main import main as entity_linker_main
from main import OUTPUT_FOLDER

EVAL_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../evaluation")


class Evaluator:

    F1_sum = 0
    TP_sum = 0
    FP_sum = 0
    FN_sum = 0
    eval_dataset_count = 0

    @classmethod
    def main(cls):
        """
        Runs entity linker (main.py) and compares its outputs with the manually generated evaluation dataset.
        :return: logs results to the console.
        """
        evaluator = Evaluator()
        entity_linker_main()
        evaluator.evaluate_results(OUTPUT_FOLDER, EVAL_FOLDER)
        evaluator.calculate_average()

    def evaluate_results(self, output_folder, evaluation_folder):
        """
        Compares generated entity linking results with the expected ones and calculates FN, TP, FP, precision, recall and F1.
        :param output_folder: generated results
        :param evaluation_folder: expected results
        :return: logs results to the console.
        """
        out_files = sorted(os.listdir(output_folder))
        for file_name in out_files:
            evaluation_file = os.path.join(evaluation_folder, file_name.replace(".tsv", "") + " review.csv")
            if os.path.exists(evaluation_file):
                self.eval_dataset_count += 1
                prediction_table = read_csv_to_dict(os.path.join(output_folder, file_name), delimiter="\t", generated_ids=True)[1]
                predictions = set()
                for row in prediction_table:
                    record = prediction_table[row]
                    predictions.add(record["candidate_entity_iri"])

                evaluation_table = read_csv_to_dict(evaluation_file, generated_ids=True)[1]
                ground_truth = set()
                for row in evaluation_table:
                    record = evaluation_table[row]
                    ground_truth.add(record["expected_entity"].replace("_", ":"))

                tp_list = ground_truth.intersection(predictions)
                fn_list = ground_truth - tp_list
                fp_list = predictions - tp_list

                precision = len(tp_list) / len(predictions)
                recall = len(tp_list) / len(ground_truth)
                f1_score = (2 * precision * recall) / (precision + recall)

                print("Evaluation of " + file_name)
                print("FN\tTP\tFP")
                print("%d\t%d\t%d" % (len(fn_list), len(tp_list), len(fp_list)))
                print("Precision: " + str(precision))
                print("Recall: " + str(recall))
                print("F1: " + str(f1_score))
                print("")

                self.F1_sum += f1_score
                self.TP_sum += len(tp_list)
                self.FN_sum += len(fn_list)
                self.FP_sum += len(fp_list)

    def calculate_average(self):
        # print("Macro-averaged F1: " + str(self.F1_sum/self.eval_dataset_count))

        precision = self.TP_sum / (self.TP_sum + self.FP_sum)
        recall = self.TP_sum / (self.TP_sum + self.FN_sum)
        f1_score = (2 * precision * recall) / (precision + recall)

        print("General Evaluation")
        print("FN\tTP\tFP")
        print("%d\t%d\t%d" % (self.FN_sum, self.TP_sum, self.FP_sum))
        print("Precision: " + str(precision))
        print("Recall: " + str(recall))
        print("Micro-averaged F1: " + str(f1_score))


if __name__ == "__main__":
    Evaluator.main()
