import csv
import json
import re
import socket
from pprint import pprint
from time import sleep

import feedparser
import dateparser
import redis

EXPIRATION_SECONDS=86400*2 #2 GIORNI
LOGSTASH_SERVER="rsslogstash"

redisCache=redis.Redis('redis', port=6379 , charset="utf-8", decode_responses=True)
redisPersistent=redis.Redis('redis', port=6379 , charset="utf-8", decode_responses=True,db=1)

#logstash

LogstashSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

while(True):
    try:
        LogstashSocket.connect((socket.gethostbyname(LOGSTASH_SERVER),5055))
        break
    except ConnectionRefusedError:
        sleep(5)

def myprint(row):
    print(row["SOURCE"])
    rssfeed=feedparser.parse(row["URL"])
    for item in rssfeed["items"]:
        # print('\t'+item["title"])
        # json.dumps({"source":row["SOURCE"],"title":row["TITLE"],"url":item["url"]})        
        print('\t'+json.dumps(item))

def removeHtmlTags(text):
    #Remove html tags from a string
    clean = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(clean, '', text)


def buildJson(item,source,language):
    try:
        return json.dumps(
            {
                "source":source,
                "title":item["title"],
                "summary":removeHtmlTags(item["summary"]),
                "link":item["link"],
                "pubDate":dateparser.parse(item["published"]).isoformat(), #PROBLEMINO
                "language":language
            }
        )
    except KeyError:
        return None

def sendToLogstash(JsonItem): #string
    LogstashSocket.send( bytes(JsonItem,"utf-8") )
    LogstashSocket.send( bytes('\n',"utf-8"))


def checkCache(item,source,language="it-IT"):
    print(item["link"])
    if not redisCache.exists(item["link"]):
        print("DATO NON PRESENTE IN CACHE. AGGIUNGO")
        value=buildJson(item,source,language)
        if value is not None:
            print("CACHING RESPONSE:" + str(redisCache.set(item["link"],value,ex=EXPIRATION_SECONDS)) )
            redisPersistent.set(item["link"],value,nx=True)
        else:
            print("RSS_ITEM NOT VALID, SKIPPING THIS NEWS.(non sara' niente di importante...)")
        return value
    else:
        print("DATO GIÀ PRESENTE IN CACHE")
        return None



with open("rss_sources_update.csv",newline='') as csvfile:
    feedListReader=list(csv.DictReader(csvfile, delimiter=';'))
    #pprint(feedListReader)
    while True:
        for row in iter(feedListReader):
            rssFeed=feedparser.parse(row["URL"])
            for rssItem in rssFeed["items"]:
                #pprint(rssItem)
                #pass
                JsonItem=checkCache(rssItem,row["SOURCE"],row["LANGUAGE"])

                if JsonItem is not None:
                    #send JsonItem to Logstash
                    sendToLogstash(JsonItem)
                sleep(3) #prova
            sleep(10)
        print("--------------")
        sleep(60*30)
