#!/bin/bash

set -e
set -o pipefail

echo "Entity linking started"
echo "VFBTIME:"
date

cd ${WORKSPACE}
python3 src/main.py

cd ${ONTOLOGY_FOLDER}
robot template --template linking.tsv --output linking.owl
robot template --template publication.tsv --output publication.owl

robot merge -i linking.owl -i publication.owl -o merged.owl

cp merged.owl "$(basename merged.owl .owl)_$(date +'%Y%m%d%H%M').owl"