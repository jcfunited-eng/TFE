import os
from openai import OpenAI

# -------- CONFIG --------
BOOTSTRAP_FILE = "uf_canonical_bootstrap.txt"
MODEL = "gpt-4.1"
TEMPERATURE = 0.1
# ------------------------


def load_bootstrap():
    with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
        return f.read()


def main():
    if not os.path.exists(BOOTSTRAP_FILE):
        print(f"ERROR: {BOOTSTRAP_FILE} not found.")
        return

    bootstrap = load_bootstrap()

    print("UF Assistant CLI")
    print("Paste your task below. End with an empty line:\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    task = "\n".join(lines)

    prompt = bootstrap + "\n\nTASK:\n" + task

    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": prompt}
        ]
    )

    print("\n--- RESPONSE ---\n")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
