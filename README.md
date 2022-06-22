# neuron-to-paper-nlp

A repository for neuron entity linking in the VFB related publications.

Uses [SciSpacy](https://github.com/allenai/scispacy) to train the fbbt model and run entity linker.  

## Install

Create virtual environment for this project. Then install the following dependencies:

```
pip install scispacy
```

```
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.0/en_core_sci_sm-0.5.0.tar.gz
```

Run `main.py` to test the model with the sample data in the [data](data) folder. Linking results are generated in the [output](output) folder.