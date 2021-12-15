import sys

import findspark

findspark.init()
findspark.find()
import pyspark

findspark.find()

from pyspark.sql import SparkSession

from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, BooleanType, LongType, IntegerType, TimestampType, DoubleType, \
    StringType
from pyspark.ml import PipelineModel

from pyspark.sql.functions import col

import pickle
import os

os.chdir('../')



features = ['TX_AMOUNT', 'TX_DURING_NIGHT', 'TX_DURING_WEEKEND', 'CUSTOMER_ID_AVG_AMOUNT_1DAY_WINDOW',
            'CUSTOMER_ID_AVG_AMOUNT_7DAY_WINDOW', 'CUSTOMER_ID_AVG_AMOUNT_30DAY_WINDOW',
            'CUSTOMER_ID_NB_TX_1DAY_WINDOW', 'CUSTOMER_ID_NB_TX_7DAY_WINDOW', 'CUSTOMER_ID_NB_TX_30DAY_WINDOW',
            'TERMINAL_ID_NB_TX_1DAY_WINDOW', 'TERMINAL_ID_NB_TX_7DAY_WINDOW', 'TERMINAL_ID_NB_TX_30DAY_WINDOW',
            'TERMINAL_ID_RISK_1DAY_WINDOW', 'TERMINAL_ID_RISK_7DAY_WINDOW', 'TERMINAL_ID_RISK_30DAY_WINDOW']


if __name__ == '__main__':
    # Spark session & context
    spark = (SparkSession
             .builder
             .master('local')
             .appName('transactions-consumer')
             # Add kafka package
             .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2")
             .getOrCreate())
    # sc = spark.sparkContext
    # # sqlContext = SQLContext(sc)

    # Create stream dataframe setting kafka server, topic and offset option
    df = (spark
          .readStream
          .format("kafka")
          .option("kafka.bootstrap.servers", "localhost:9092")  # kafka server
          .option("subscribe", "transactions")  # topic
          .option("startingOffsets", "earliest")  # start from beginning
          .load())

    readDF = df.selectExpr("CAST(value AS STRING)")

    schema = StructType(
        [
            StructField("index", LongType(), nullable=False),
            StructField("TRANSACTION_ID", LongType(), nullable=False),
            StructField("TX_DATETIME", StringType(), nullable=False),
            StructField("CUSTOMER_ID", LongType(), nullable=False),
            StructField("TERMINAL_ID", LongType(), nullable=False),
            StructField("TX_AMOUNT", DoubleType(), nullable=True),
            StructField("TX_TIME_SECONDS", LongType(), nullable=True),
            StructField("TX_TIME_DAYS", LongType(), nullable=True),
            StructField("TX_FRAUD", LongType(), nullable=True),
            StructField("TX_FRAUD_SCENARIO", LongType(), nullable=True),
            StructField("TX_DURING_NIGHT", LongType(), nullable=True),
            StructField("TX_DURING_WEEKEND", LongType(), nullable=True),
            StructField("CUSTOMER_ID_AVG_AMOUNT_1DAY_WINDOW", DoubleType(), nullable=True),
            StructField("CUSTOMER_ID_AVG_AMOUNT_7DAY_WINDOW", DoubleType(), nullable=True),
            StructField("CUSTOMER_ID_AVG_AMOUNT_30DAY_WINDOW", DoubleType(), nullable=True),
            StructField("CUSTOMER_ID_NB_TX_1DAY_WINDOW", LongType(), nullable=True),
            StructField("CUSTOMER_ID_NB_TX_7DAY_WINDOW", LongType(), nullable=True),
            StructField("CUSTOMER_ID_NB_TX_30DAY_WINDOW", LongType(), nullable=True),
            StructField("TERMINAL_ID_NB_TX_1DAY_WINDOW", LongType(), nullable=True),
            StructField("TERMINAL_ID_NB_TX_7DAY_WINDOW", LongType(), nullable=True),
            StructField("TERMINAL_ID_NB_TX_30DAY_WINDOW", LongType(), nullable=True),
            StructField("TERMINAL_ID_RISK_1DAY_WINDOW", DoubleType(), nullable=True),
            StructField("TERMINAL_ID_RISK_7DAY_WINDOW", DoubleType(), nullable=True),
            StructField("TERMINAL_ID_RISK_30DAY_WINDOW", DoubleType(), nullable=True)
        ]
    )

    df_transactions = (readDF.withColumn("value", from_json("value", schema)))
    df_formatted = (df_transactions.select(
        col("value.TRANSACTION_ID").alias("TRANSACTION_ID"),
        col("value.TX_DATETIME").alias("TX_DATETIME"),
        col("value.CUSTOMER_ID").alias("CUSTOMER_ID"),
        col("value.TERMINAL_ID").alias("TERMINAL_ID"),
        col("value.TX_AMOUNT").alias("TX_AMOUNT"),
        col("value.TX_TIME_SECONDS").alias("TX_TIME_SECONDS"),
        col("value.TX_TIME_DAYS").alias("TX_TIME_DAYS"),
        col("value.TX_FRAUD").alias("TX_FRAUD"),
        col("value.TX_FRAUD_SCENARIO").alias("TX_FRAUD_SCENARIO"),
        col("value.TX_DURING_NIGHT").alias("TX_DURING_NIGHT"),
        col("value.TX_DURING_WEEKEND").alias("TX_DURING_WEEKEND"),
        col("value.CUSTOMER_ID_AVG_AMOUNT_1DAY_WINDOW").alias("CUSTOMER_ID_AVG_AMOUNT_1DAY_WINDOW"),
        col("value.CUSTOMER_ID_AVG_AMOUNT_7DAY_WINDOW").alias("CUSTOMER_ID_AVG_AMOUNT_7DAY_WINDOW"),
        col("value.CUSTOMER_ID_AVG_AMOUNT_30DAY_WINDOW").alias("CUSTOMER_ID_AVG_AMOUNT_30DAY_WINDOW"),
        col("value.CUSTOMER_ID_NB_TX_1DAY_WINDOW").alias("CUSTOMER_ID_NB_TX_1DAY_WINDOW"),
        col("value.CUSTOMER_ID_NB_TX_7DAY_WINDOW").alias("CUSTOMER_ID_NB_TX_7DAY_WINDOW"),
        col("value.CUSTOMER_ID_NB_TX_30DAY_WINDOW").alias("CUSTOMER_ID_NB_TX_30DAY_WINDOW"),
        col("value.TERMINAL_ID_NB_TX_1DAY_WINDOW").alias("TERMINAL_ID_NB_TX_1DAY_WINDOW"),
        col("value.TERMINAL_ID_NB_TX_7DAY_WINDOW").alias("TERMINAL_ID_NB_TX_7DAY_WINDOW"),
        col("value.TERMINAL_ID_NB_TX_30DAY_WINDOW").alias("TERMINAL_ID_NB_TX_30DAY_WINDOW"),
        col("value.TERMINAL_ID_RISK_1DAY_WINDOW").alias("TERMINAL_ID_RISK_1DAY_WINDOW"),
        col("value.TERMINAL_ID_RISK_7DAY_WINDOW").alias("TERMINAL_ID_RISK_7DAY_WINDOW"),
        col("value.TERMINAL_ID_RISK_30DAY_WINDOW").alias("TERMINAL_ID_RISK_30DAY_WINDOW")
    ))

    pipelineModel = PipelineModel.load("models/random-forrest")

    results = pipelineModel.transform(df_formatted).writeStream.format("console")\
        .start().awaitTermination()

