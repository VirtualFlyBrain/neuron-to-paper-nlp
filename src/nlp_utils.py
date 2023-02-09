import re
import os
from file_utils import read_csv_to_dict

DSX_PREFIX = "dsx-"
IGNORE_WORDS = ["neuron", "neurons", "proboscis motor neuron", "secondary", "adult drosulfakinin"]
GREEK_SYMBOLS = {"alpha": "α", "beta": "β", "gamma": "γ"}


def extract_acronyms(sentence):
    for match in re.finditer(r"\((.*?)\)", sentence):
        start_index = match.start()
        abbr = match.group(1)
        size = len(abbr)
        words = sentence[:start_index].split()[-size:]
        definition = " ".join(words)

        print(abbr, definition)


def generate_phrase_variances(phrase):
    """
    Gets a phrase and manipulates it (removes the text between parentheses, dashes, 'dsx-' prefixes etc.) to generate
    phrase variances.
    :param phrase: phrase to generate name variances
    :return: set of phrase variances
    """
    variances = set()
    variances.add(phrase)

    # remove dsx- prefix
    to_add = set()
    for variance in variances:
        to_add.add(variance.replace(DSX_PREFIX, "").strip())
    variances = variances.union(to_add)

    # remove text inside parentheses
    to_add = set()
    for variance in variances:
        removed_parentheses = re.sub(r'\([^)]*\)', "", variance).strip()
        removed_parentheses = removed_parentheses.replace("  ", " ")  # drop double spaces
        to_add.add(removed_parentheses)
    variances = variances.union(to_add)

    # replace dash with space
    to_add = set()
    for variance in variances:
        to_add.add(variance.replace("-", " ").strip())
    variances = variances.union(to_add)

    # remove ignored words
    to_add = set()
    for variance in variances:
        # remove ignore words one by one
        for ignore_word in IGNORE_WORDS:
            if ignore_word in str(variance).lower():
                # whole word match \b
                clean_sentence = re.sub(r"\b%s\b" % ignore_word, "", variance, flags=re.IGNORECASE).strip()
                clean_sentence = clean_sentence.replace("  ", " ")  # drop double spaces
                to_add.add(clean_sentence)
        # remove ignore words all together
        all_clean = variance
        for ignore_word in IGNORE_WORDS:
            if ignore_word in str(all_clean).lower():
                # whole word match \b
                all_clean = re.sub(r"\b%s\b" % ignore_word, "", all_clean, flags=re.IGNORECASE).strip()
                all_clean = all_clean.replace("  ", " ")  # drop double spaces
        to_add.add(all_clean.strip())
    variances = variances.union(to_add)

    # add plural neuronS variance
    to_add = set()
    for variance in variances:
        to_add.add(re.sub(r"\b%s\b" % "neuron", "neurons", variance).strip())
    variances = variances.union(to_add)

    # add greek letter variance
    to_add = set()
    for variance in variances:
        in_symbols = variance
        for key in GREEK_SYMBOLS:
            in_symbols = in_symbols.replace(key, GREEK_SYMBOLS[key])
        to_add.add(in_symbols.strip())
    variances = variances.union(to_add)

    return variances


def count_keywords(data_folder, ignored_extensions, keywords):
    data_files = sorted(os.listdir(data_folder))

    all_keyword_stats = dict()
    for filename in data_files:
        file_path = os.path.join(data_folder, filename)
        if os.path.isfile(file_path) and not filename.endswith(ignored_extensions):
            table = read_csv_to_dict(file_path, delimiter="\t", generated_ids=True)[1]
            all_paper_text = ""
            for row in table:
                if "text" in table[row]:
                    sentence = table[row]["text"]
                    all_paper_text = all_paper_text + " " + sentence
            paper_stats = dict()
            for keyword in keywords:
                paper_stats[keyword] = sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(keyword), all_paper_text))
            all_keyword_stats[filename] = paper_stats
    return all_keyword_stats
