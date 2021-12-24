import os

import tqdm as tqdm

os.chdir("../")
print(os.listdir())

import json
import pandas as pd
from time import sleep
from kafka import KafkaProducer

if __name__ == '__main__':
    df = pd.read_parquet('transformed-data/test/test_set.parquet', engine='fastparquet')
    df['TX_DATETIME'] = df['TX_DATETIME'].astype(str)
    df = df.loc[df['TX_DATETIME'] >= '2021-12-09 00:00:00']

    # Create producer
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',  # Kafka server
        value_serializer=lambda v: json.dumps(v).encode('utf-8')  # json serializer
    )

    try:
        for index, row in df.sort_values('TX_DATETIME').iterrows():
            try:
                message = row.to_dict()
            except ValueError:
                pass
            else:
                producer.send('transactions', message)
                print(f"message-{index} successfully sent")
                sleep(0.3)
    except KeyboardInterrupt:
        print("process interrupted")
