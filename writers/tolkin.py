import pathlib, json

class Tolkin():
    def __init__(self, filepath):
        self.filepath = filepath
        if not filepath.exists():
            filepath.parent.mkdir(exist_ok=True, parents=True)
            filepath.touch()

    def add_json(self, content):
        with self.filepath.open("a") as f:
            f.write(json.dumps(content) + "\n")
