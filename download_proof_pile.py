from datasets import load_dataset

ds = load_dataset(
    "hoskinson-center/proof-pile",
    revision="refs/convert/parquet",
    split="train",
    streaming=True,
)

with open("proof_pile.txt", "w", encoding="utf-8") as f:
    for row in ds:
        text = row.get("text")
        if text:
            f.write(text)
            f.write("\n")