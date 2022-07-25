import re

DSX_PREFIX = "dsx-"
IGNORE_WORDS = ["neuron", "neurons"]


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

    to_add = set()
    for variance in variances:
        to_add.add(variance.replace(DSX_PREFIX, "").strip())
    variances = variances.union(to_add)

    to_add = set()
    for variance in variances:
        removed_parentheses = re.sub(r'\([^)]*\)', "", variance).strip()
        removed_parentheses = removed_parentheses.replace("  ", " ")  # drop double spaces
        to_add.add(removed_parentheses)
    variances = variances.union(to_add)

    to_add = set()
    for variance in variances:
        to_add.add(variance.replace("-", " ").strip())
    variances = variances.union(to_add)

    to_add = set()
    for variance in variances:
        for ignore_word in IGNORE_WORDS:
            if ignore_word in variance:
                # whole word match \b
                clean_sentence = re.sub(r"\b%s\b" % ignore_word, "", variance).strip()
                clean_sentence = clean_sentence.replace("  ", " ")  # drop double spaces
                to_add.add(clean_sentence)
    variances = variances.union(to_add)

    return variances
