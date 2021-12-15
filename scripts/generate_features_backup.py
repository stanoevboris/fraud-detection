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
        WITH cte as     
        (SELECT *,
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
         SUM(TX_FRAUD) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS fraud_delay, 
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 7 DAYS PRECEDING AND CURRENT ROW
         ) AS tx_frauds_delay,
         SUM(TX_FRAUD) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 8 DAYS PRECEDING AND CURRENT ROW
         ) AS fraud_delay_1day_window, 
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 8 DAYS PRECEDING AND CURRENT ROW
         ) AS tx_delay_1day_window,
         SUM(TX_FRAUD) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 14 DAYS PRECEDING AND CURRENT ROW
         ) AS fraud_delay_7day_window, 
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 14 DAYS PRECEDING AND CURRENT ROW
         ) AS tx_delay_7day_window,
         SUM(TX_FRAUD) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 37 DAYS PRECEDING AND CURRENT ROW
         ) AS fraud_delay_30day_window, 
         COUNT(TRANSACTION_ID) OVER (
            PARTITION BY TERMINAL_ID 
            ORDER BY CAST(TX_DATETIME AS timestamp) 
            RANGE BETWEEN INTERVAL 37 DAYS PRECEDING AND CURRENT ROW
         ) AS tx_delay_30day_window
          FROM df
         )
         SELECT *, 
         tx_delay_1day_window-tx_frauds_delay as TERMINAL_ID_NB_TX_1DAY_WINDOW,
         tx_delay_7day_window-tx_frauds_delay as TERMINAL_ID_NB_TX_7DAY_WINDOW,
         tx_delay_30day_window-tx_frauds_delay as TERMINAL_ID_NB_TX_30DAY_WINDOW,
         (fraud_delay_1day_window-fraud_delay)/(tx_delay_1day_window-tx_frauds_delay) as TERMINAL_ID_RISK_1DAY_WINDOW,
         (fraud_delay_7day_window-fraud_delay)/(tx_delay_7day_window-tx_frauds_delay) as TERMINAL_ID_RISK_7DAY_WINDOW,
         (fraud_delay_30day_window-fraud_delay)/(tx_delay_30day_window-tx_frauds_delay) as TERMINAL_ID_RISK_30DAY_WINDOW
         FROM cte""")
    # we expect some risk_window values to be null, so we replace them with 0
    df = df.fillna(0)

    # drop unnecessary columns
    df = df.drop('tx_frauds_delay', 'fraud_delay', 'fraud_delay_1day_window', 'tx_delay_1day_window',
                 'fraud_delay_7day_window', 'tx_delay_7day_window', 'fraud_delay_30day_window', 'tx_delay_30day_window')

    # save dataframe locally
    df.write.format('parquet') \
        .mode('overwrite') \
        .option("parquet.bloom.filter.enabled#favorite_color", "true") \
        .option("parquet.bloom.filter.expected.ndv#favorite_color", "1000000") \
        .option("parquet.enable.dictionary", "true") \
        .option("parquet.page.write-checksum.enabled", "false") \
        .save(dir_output)

    return df
