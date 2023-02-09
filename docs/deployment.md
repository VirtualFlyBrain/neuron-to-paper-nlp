# Deployment Guide
System composed of two modules. EuropePMC Crawler collects publications, parses their content (text, captions, tables, metadata) and saves to an output folder in tabular format. Then, neuron to paper module processes these files, links entities and generates a entity linking ontology (entity -> referring publications).

# Table of Contents
1. [Deploy EuropePMC Crawler](#deploy-europepmc-crawler)
2. [Deploy neuron-to-paper-nlp](#deploy-neuron-to-paper-nlp)

`$WORKSPACE` indicates a folder in the server where we will clone projects into it.

## Deploy EuropePMC Crawler
To build the project, clone the project to your server.
```
cd $WORKSPACE
git clone https://github.com/VirtualFlyBrain/europmc_crawler.git
```

Navigate to the project folder and build the docker image:
```
cd europmc_crawler/
docker build -t virtualflybrain/europmc_crawler .
```

The crawler expects a status file ($OUTPUT_FOLDER/crawling_status.txt) to read the last crawling date and continue crawling there. And at the end of its execution, program updates the status file. Let's create a status file (current latest file is https://ftp.flybase.net/flybase/associated_files/vfb/pmcid_new_vfb_fb_2022_06.tsv, set date accordingly).
```
mkdir data/publications
echo "2022-05" > data/publications/crawling_status.txt
```

To run the built Docker image:
```
docker run --volume=`pwd`/data:/data/ -e FTP_folder=https://ftp.flybase.net/flybase/associated_files/vfb/ -e output_folder=/data/publications/ virtualflybrain/europmc_crawler
```

When crawling complete, you should be able to see crawled files at `europmc_crawler/data/publications/out` folder. At the end of the successful crawling, status file will be updated with the current date.

## Deploy neuron-to-paper-nlp
To build the NLP module, clone the project to your server

```
cd $WORKSPACE
git clone https://github.com/VirtualFlyBrain/neuron-to-paper-nlp.git
```

Navigate to the project folder and build the docker image:
```
cd neuron-to-paper-nlp/
docker build -t virtualflybrain/neuron-to-paper-nlp .
```

To run the built Docker image:
```
cd $WORKSPACE
docker run --volume=`pwd`/europmc_crawler/data:/my_volume/ -e DATA_FOLDER=/my_volume/publications/out/ -e OUTPUT_FOLDER=/my_volume/nlp_output -e ONTOLOGY_FOLDER=/my_volume/ontology virtualflybrain/neuron-to-paper-nlp:latest
```

At the end of the crawling you should delete (backup if necessary) crawling output folder (`europmc_crawler/data/publications/out`) to be prepared for the next crawling. 