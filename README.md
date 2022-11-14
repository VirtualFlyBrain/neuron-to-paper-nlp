# neuron-to-paper-nlp

A repository to link neuron names/mentions that exist in the publications with the [FBBT Ontology](https://www.ebi.ac.uk/ols/ontologies/fbbt) terms.

This project works in collaboration with [europmc_crawler](https://github.com/VirtualFlyBrain/europmc_crawler) to retrieve publication contents from the [Europe PMC](https://europepmc.org/RestfulWebService). 
[/data](data) folder provides sample output of the europmc_crawler   

# Table of Contents
1. [Approach](#approach)
2. [Training](#training)
3. [Installation](#installation)
4. [Evaluation](#evaluation)

## Approach

Used terminology is as follows:

- __Mention__: A noun or noun phrase in the publication (such as `MP1`) to search for the related entities in the ontology (`adult Drosulfakinin MP1 neuron`, `FBbt:00051431`).

- __Entity linking candidate__: For evey mention a set of ontology term nominees with different confidence scores are calculated. Each nominee is called an entity linking candidate.

  - _FBbt:00001599, MP1 neuron, 0.99999_ 
  - _FBbt:00051431, adult Drosulfakinin MP1 neuron, 0.99999_ 
  - _FBbt:00001600, MP1a neuron, 0.96954_

1. Publication content represented in tabular format (see [/data](data) folder) is processed in batches using [SciSpacy](https://github.com/allenai/scispacy).

1. A confidence threshold (0.85) is applied to filter low confidence candidates. 

1. Mentions that exist in the stopwords ([resources/stopwords.txt](resources/stopwords.txt)) are filtered.  

1. Additionally, for every mention a relative threshold based filtering is applied. Candidates that are significantly lower than the most confident candidate are filtered.  

1. Mentions shorter than 4 letters must exist in the ontology term's label or synonyms.

1. Not frequent entities (linked less than 3 times) are filtered

1. For each paper, specimen term ('male', 'female', 'larval') frequencies are calculated. Candidates whose specimen not mentioned in the paper are filtered (`adult corazonin neuron` vs ` 	larval corazonin neuron`).

1. Outlier detection is applied to all linking results:
   1. OWL2Vec* model is trained that represents the semantic similarity of the ontology terms.
   1. For each paper the most confident linking candidates (confidence > 0.95 and mentioned at least for 10 times) in the paper are selected. 
   1. Using OWL2Vec* embeddings calculates the average of the high confident entities. This vector represent the context of the paper.
   1. Calculates each candidate's distance to the paper context vector.
   1. Outliers filtered using standard deviation: term_similarity < (mean_similarity - 2 * stdev_score):

1. Finally, ROBOT templates for the publication metadata and entity linking results are generated in the [/robot_templates](robot_templates) folder.

## Training

Project uses [SciSpacy](https://github.com/allenai/scispacy) and [OWL2Vec*](https://github.com/KRR-Oxford/OWL2Vec-Star) 
for entity linking and results' filtering (outlier detection). Pre-trained models for both can be found at:

- SciSpacy: [/linker](linker) 
- OWL2Vec*: [/owl2vec/embeddings](owl2vec/embeddings)

In case the FBBT ontology change, these models need to be retrained following the given steps:

1- SciSpacy requires a json representation of the ontology, generate it through running:
```
python src/owl_to_json.py
```
This script only transforms the subclasses of the `neuron` class (`FBbt:00005106`) and generates the [fbbt-cedar.jsonl](resources/fbbt-cedar.jsonl)

During this transformation a set of steps are applied to entity labels and synonyms to enrich aliases and generate new ones:
    1. Texts inside parentheses are removed
    1. '-' replaced by ' '
    1. Ignored words (eg. neuron, secondary etc.) cleaned to increase match
    1. Plural and singular variations of 'neuron'
    1. Greek letters replaced by their symbol (alpha -> α)

2- Run SciSpacy model trainer: 
```
python src/train_fbbt_linker.py
```

3- Run OWL2Vec* trainer:
```
python semantics/OWL2Vec_Standalone.py
```
This step uses the [/owl2vec/default.cfg](owl2vec/default.cfg) configuration file.  

## Installation

### Docker

To run the project, build the Docker image and run with the required environment variables

```
docker build -t virtualflybrain/neuron-to-paper-nlp .
```

```
docker run --volume=/home/my/volume:/my_volume/ -e DATA_FOLDER=/my_volume/data -e OUTPUT_FOLDER=/my_volume/output -e ONTOLOGY_FOLDER=/my_volume/ontology virtualflybrain/neuron-to-paper-nlp:latest
```

### Development environment

Project requires python `>=3.7`, `<3.9` venv, due to dependencies of the [OWL2Vec*](https://github.com/KRR-Oxford/OWL2Vec-Star)

Create virtual environment for this project. Then install the following dependencies:

```
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.0/en_core_sci_sm-0.5.0.tar.gz
```

```
pip install -r requirements.txt
```

Run `main.py` to test the model with the sample data in the [data](data) folder. Linking results are generated in the [output](output) folder.

## Evaluation

Project uses a manually annotated corpus ([/evaluation](evaluation)) to evaluate the accuracy of the system. To evaluate the tool, run:
```
python src/evaluation.py
```
Tester runs the tool and compares the generated entity linking results with the expected ones through calculating FN, TP, FP, precision, recall and F1.