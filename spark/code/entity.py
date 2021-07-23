import sys
import random
import re

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession, Row
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import from_json, lit, split, col, concat, array_distinct
import pyspark.sql.types as tp


#Schema del Json mandato da kafka
itemKafka = tp.StructType([
    tp.StructField(name= 'source', dataType= tp.StringType(),  nullable= True),
    tp.StructField(name= 'title', dataType= tp.StringType(),  nullable= True),
    tp.StructField(name= 'summary', dataType= tp.StringType(),  nullable= True),
    tp.StructField(name= 'link', dataType= tp.StringType(),  nullable= True),
    tp.StructField(name= 'pubDate', dataType= tp.StringType(),  nullable= True),
    tp.StructField(name= 'language', dataType= tp.StringType(),  nullable= True)
])


kafkaServer="kafka:9092"
topic="rss"
elastic_host="elasticsearch"
elastic_index="rss"
# Spark
# sc = SparkContext(appName="StructuredStreamRSS")
spark = SparkSession.builder.appName("StructuredStreamRSS").master("local[4]").config("spark.driver.memory","6G").getOrCreate()
spark.sparkContext.setLogLevel("WARN")
#SparkNLP
pipeline = PipelineModel.load("/opt/model/entity_recognizer_lg_it_3.0.0_3.0_1616465464186/")


def wcDataframe(record):
  record.wc=len(record.parole)

def elaborate(df: DataFrame, epoch_id: int):
  df_1=df.select("title").select("title",split(df.title," ").alias("parole"), lit(0).alias("wc"))
  template=Row("title","parole","wc")
  myrdd=df_1.rdd.map(lambda x: (template(x.title,x.parole,len(x.parole))) )
  print(myrdd.collect())
  if(myrdd.isEmpty() is not True ):
    mydf=spark.createDataFrame(myrdd,["title","parole","wc"])
    # mydf.printSchema()
    mydf.show()
  # df_1.show()

def cleanupDF(df: DataFrame):
  #DF to RDD, map rdd
  myrdd=df.select("link","entities").rdd.map(lambda x: (Row(x.link,cleanup(x.entities))))
  #RDD to MAP
  if(myrdd.isEmpty() is True): #il primo df in arrivo dallo Structured Stream è vuoto
    return df
  else:
    return  df.drop(col("entities")).\
            join(spark.createDataFrame(myrdd,["link","entities"])\
                      .select(col("link"), array_distinct(col("entities")).alias("entities")
                ),on="link"
            )

def cleanup(entities):
  clean = re.compile(',|;|:|\"|«|\'|\*|\)|\(|!|\?')
  for i in range(0,len(entities)):
    entities[i]=re.sub(clean, '', entities[i])
  return entities

def elaborateEntity(df: DataFrame, epoch_id: int):
  df_og=df.select('source','title','summary','pubDate','link')
  print("INPUT:")
  df_og.show()
  print("OUTPUT:")
  #extract entites from title
  df_ent_title=pipeline.transform(df_og.select(col("link"), col("title").alias("text"))).select(col("link"),col("entities.result").alias("ent_title"))
  # df_ent_title.show()
  #extract entites from summary
  df_ent_summary=pipeline.transform(df_og.select(col("link"), col("summary").alias("text"))).select(col("link"),col("entities.result").alias("ent_summary"))
  #join dei df con le entità
  df_ent_join=df_ent_title.join(df_ent_summary, on="link")
  #join in un unico df con i tutti i dati
  df_ent_join=df_og.join(df_ent_join,on="link")\
    .select(col("link"), col("source"), col("title"), col("summary"), col("pubDate"), concat(col("ent_title"),col("ent_summary")).alias("entities"))
  #pulizia delle entità
  df_ent_join=df_ent_join.transform(cleanupDF)
  #df_ent_join.printSchema()
  df_ent_join.show()

  
  df_ent_join.write\
    .format("org.elasticsearch.spark.sql")\
    .mode("append")\
    .option("es.mapping.id","link")\
    .option("es.nodes", elastic_host).save(elastic_index)
  print("mandato a ES!")
  
  return
  
#Data frame simbolico, popolato da kafka, sulla quale verranno effettuate le operazioni

df = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", kafkaServer) \
  .option("subscribe", topic) \
  .load()


#Avviamo lo structured streaming
# .format("console") \
df.selectExpr("CAST(value AS STRING)") \
  .select(from_json("value",itemKafka).alias("data"))\
  .select("data.*") \
  .writeStream \
  .foreachBatch(elaborateEntity)\
  .start() \
  .awaitTermination()