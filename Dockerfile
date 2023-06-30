FROM python:3.8

ENV DATA_FOLDER=./data
ENV OUTPUT_FOLDER=./output
ENV ONTOLOGY_FOLDER=./ontology

ENV WORKSPACE=/opt/VFB
RUN mkdir $WORKSPACE

# for robot path variable
ENV PATH "/opt/VFB/:$PATH"

RUN mkdir $WORKSPACE/src/
ADD requirements.txt setup.py runner.sh $WORKSPACE/
ADD src/semantics $WORKSPACE/src/semantics
ADD src/main.py $WORKSPACE/src/
ADD src/file_utils.py $WORKSPACE/src/
ADD src/nlp_utils.py $WORKSPACE/src/
ADD src/ontology_utils.py $WORKSPACE/src/
ADD src/owl_to_json.py $WORKSPACE/src/
ADD src/template_generator.py $WORKSPACE/src/
ADD src/train_fbbt_linker.py $WORKSPACE/src/
ADD src/__init__.py $WORKSPACE/src/

ADD linker $WORKSPACE/linker/
ADD owl2vec $WORKSPACE/owl2vec/
ADD resources $WORKSPACE/resources/
ADD robot_templates $WORKSPACE/robot_templates/

RUN python -m pip install --upgrade pip
RUN pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.0/en_core_sci_sm-0.5.0.tar.gz
RUN pip install -r $WORKSPACE/requirements.txt

RUN apt-get -qq update || apt-get -qq update && apt-get -qq -y install wget default-jdk


###### ROBOT ######
ENV ROBOT v1.8.3
ENV ROBOT_ARGS -Xmx20G
ARG ROBOT_JAR=https://github.com/ontodev/robot/releases/download/$ROBOT/robot.jar
ENV ROBOT_JAR ${ROBOT_JAR}
RUN wget $ROBOT_JAR -O $WORKSPACE/robot.jar && \
    wget https://raw.githubusercontent.com/ontodev/robot/$ROBOT/bin/robot -O $WORKSPACE/robot && \
    chmod +x $WORKSPACE/robot && chmod +x $WORKSPACE/robot.jar

RUN chmod +x $WORKSPACE/runner.sh

RUN cd $WORKSPACE && python3 setup.py develop

CMD ["/opt/VFB/runner.sh"]
