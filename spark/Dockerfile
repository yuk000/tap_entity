FROM openjdk:8-jre

ENV PATH $SPARK_DIR/bin:$PATH
ENV SPARK_VERSION=3.1.1
ENV SPARK_DIR=/opt/spark
ENV PATH $SPARK_DIR/bin:$PATH

ADD setup/spark-${SPARK_VERSION}-bin-hadoop2.7.tgz /opt
ADD model/entity_recognizer_lg_it_3.0.0_3.0_1616465464186 /opt/model/entity_recognizer_lg_it_3.0.0_3.0_1616465464186
RUN apt-get update && apt-get -y install bash python3 python3-pip

RUN pip3 install pyspark numpy elasticsearch sparknlp
# Create Sym Link ....
RUN ln -s /opt/spark-${SPARK_VERSION}-bin-hadoop2.7 ${SPARK_DIR} 

# Add Python Code
#ADD code/*  /opt/tap/
# Add Java Code
#ADD apps /opt/tap/apps
# Add Spark Manager
ADD spark-manager.sh $SPARK_DIR/bin/spark-manager/

WORKDIR ${SPARK_DIR}/bin/spark-manager
ENTRYPOINT [ "./spark-manager.sh" ]