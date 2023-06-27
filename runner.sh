#!/bin/bash

set -e
set -o pipefail

mkdir -p ${DATA_FOLDER}
mkdir -p ${ONTOLOGY_FOLDER}
mkdir -p ${OUTPUT_FOLDER}

echo "Entity linking started"
echo "VFBTIME:"
date

cd ${WORKSPACE}
python3 src/main.py

cd ${ONTOLOGY_FOLDER}
robot template --template linking.tsv --output linking.owl
#robot template --template publication.tsv --output publication.owl

#robot merge -i linking.owl -i publication.owl -o merged.owl

#cp linking.owl "$(basename linking.owl .owl)_$(date +'%Y%m%d%H%M').owl"

FILE=merged.owl
if [ -f "$FILE" ]; then
    robot merge -i merged.owl -i linking.owl -o merged.owl
else
    robot merge -i linking.owl -o merged.owl
fi

echo "Process completed!"
echo "VFBTIME:"
date
