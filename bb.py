#!/usr/bin/env python
import requests, os, uuid
import curlify
import json
from dotenv import load_dotenv

load_dotenv()
import csv, sys
csv.field_size_limit(100000000000)
key = os.environ.get("FASTINO_KEY")

with open(sys.argv[1]) as obj:
    rows= json.loads(obj.read())
print("loaded", file=sys.stderr)

for row in rows:
    response = requests.post(
        "https://api.pioneer.ai/inference",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": key
        },
        json={
            "model_id": "839c367a-bfa3-4b78-8f3e-85c44f619106",
            "task": "generate",
            "messages": [ 
                { "role": "system", "content": "You are an inference engine that processes text and outputs strict json with the following labels to the dict object: software version, platform, bug behaviour, crash, user frustration, technical description, input data, expected behaviour. You are not conversational." },
                { "role": "user", "content": row.get('text') } ],
            "temperature": 0,
            "max_tokens": 256
        }
    )

    try:
        obj = response.json()
        row['uuid'] = str(uuid.uuid4())
        row.update(json.loads(obj.get('completion')))
        print(json.dumps(row))
        sys.stdout.flush()
    except:
        pass
