import os
from file_utils import read_csv_to_dict


def evaluate_results(output_folder, evaluation_folder):
    out_files = sorted(os.listdir(output_folder))
    for file_name in out_files:
        # print(file_name)
        evaluation_file = os.path.join(evaluation_folder, file_name.replace(".tsv", "") + " review.csv")
        if os.path.exists(evaluation_file):
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


# OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../output/brief_85_3/")
# EVAL_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../evaluation")
#
# evaluate_results(OUTPUT_FOLDER, EVAL_FOLDER)
