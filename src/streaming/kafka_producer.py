

import json
import os
import time
from kafka import KafkaProducer

INPUT_JSONL = os.getenv("KAFKA_PAYLOADS_FILE", "outputs/kafka_payloads.jsonl")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "equipment.events")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SEND_DELAY_SEC = float(os.getenv("KAFKA_SEND_DELAY_SEC", "0.03"))


def json_serializer(data):
    return json.dumps(data).encode("utf-8")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=json_serializer
    )


def main():
    producer = create_producer()
    sent_count = 0

    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            payload = json.loads(line)

            producer.send(TOPIC_NAME, value=payload)
            sent_count += 1

            print(
                f"Sent event #{sent_count} | "
                f"frame_id={payload['frame_id']} | "
                f"state={payload['utilization']['current_state']} | "
                f"activity={payload['utilization']['current_activity']}"
            )

            time.sleep(SEND_DELAY_SEC)

    producer.flush()
    producer.close()

    print(f"\nFinished sending {sent_count} events to topic '{TOPIC_NAME}'")


if __name__ == "__main__":
    main()