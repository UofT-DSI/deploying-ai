# Dataset Notes

`travel_knowledge.jsonl` is generated from Wikivoyage summaries using:

- script: `build_wikivoyage_dataset.py`
- API endpoint pattern: `https://en.wikivoyage.org/api/rest_v1/page/summary/<Destination>`

Each record stores:

- destination name
- short overview text
- source URL
- license metadata (`CC BY-SA 4.0`)

To rebuild the dataset:

```bash
python build_wikivoyage_dataset.py
```
