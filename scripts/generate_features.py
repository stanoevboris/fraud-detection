import os

print(os.listdir())
import findspark
import pyspark

findspark.init()
findspark.find()

from pyspark import SparkContext, SparkConf
from pyspark.sql import SparkSession
from pyspark.sql import SQLContext
import pyspark.sql.functions as F
from pyspark.sql.functions import col

from scripts.generate_data import load_dataset


def transform_data(spark, dir_input, dir_output, begin_date, end_date):
    df = load_dataset(spark, dir_input, begin_date, end_date)

    df = df.withColumn('TX_DURING_NIGHT', F.when(F.date_format('TX_DATETIME', 'H') <= 6, 1) \
                       .otherwise(0))
    df = df.withColumn('TX_DURING_WEEKEND', F.when(F.date_format('TX_DATETIME', 'F') >= 5, 1) \
                       .otherwise(0))

    df.createOrReplaceTempView("df")
    df = spark.sql(
        """
        SELECT *,
         AVG(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 1 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_AVG_AMOUNT_1DAY_WINDOW, 
         AVG(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_AVG_AMOUNT_7DAY_WINDOW,
         AVG(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 30 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_AVG_AMOUNT_30DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 1 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_NB_TX_1DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_NB_TX_7DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 30 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_NB_TX_30DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY (CUSTOMER_ID, TERMINAL_ID) 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 1 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_TERMINAL_ID_NB_TX_1DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY (CUSTOMER_ID, TERMINAL_ID) 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_TERMINAL_ID_NB_TX_7DAY_WINDOW,
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY (CUSTOMER_ID, TERMINAL_ID)  
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 30 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_TERMINAL_ID_NB_TX_30DAY_WINDOW,
         MAX(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 1 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_MAX_AMOUNT_1DAY_WINDOW, 
         MAX(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_MAX_AMOUNT_7DAY_WINDOW,
         MAX(TX_AMOUNT) OVER (
            PARTITION BY CUSTOMER_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 30 DAYS PRECEDING AND CURRENT ROW
         ) AS CUSTOMER_ID_MAX_AMOUNT_30DAY_WINDOW
          FROM df
          """)
    # we expect some values to be null, so we replace them with 0
    df = df.fillna(0)

    # save dataframe locally
    df.write.format('parquet') \
        .mode('overwrite') \
        .option("parquet.bloom.filter.enabled#favorite_color", "true") \
        .option("parquet.bloom.filter.expected.ndv#favorite_color", "1000000") \
        .option("parquet.enable.dictionary", "true") \
        .option("parquet.page.write-checksum.enabled", "false") \
        .save(dir_output)

    return df
