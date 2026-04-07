
import json
import os
from kafka import KafkaConsumer

TOPIC_NAME = os.getenv("KAFKA_TOPIC", "equipment.events")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "equipment-demo-group")


def main():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=GROUP_ID,
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    print(f"Listening on topic '{TOPIC_NAME}'...\n")

    for message in consumer:
        payload = message.value
        print("Received event:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("-" * 60)


if __name__ == "__main__":
    main()