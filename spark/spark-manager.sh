#!/bin/bash
[[ -z "${SPARK_SCRIPT}" ]] && { echo "SPARK_ACTION required"; exit 1; }

/opt/spark/bin/spark-submit --packages "com.johnsnowlabs.nlp:spark-nlp_2.12:3.1.3,org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,org.elasticsearch:elasticsearch-spark-30_2.12:7.12.1" /opt/tap/${SPARK_SCRIPT} 
