class Orwell():
    def __init__(self, filepath):
        self.filepath = filepath
        self.cache = []

        if not filepath.exists():
            filepath.parent.mkdir(exist_ok=True, parents=True)
            filepath.touch()

        self.load()

    def __contains__(self, item):
        return item in self.cache

    def load(self):
        self.cache = self.filepath.read_text().splitlines()

    def add(self, item):
        if item is None:
            return
        if str(item) not in self.cache:
            self.cache.append(str(item))
            with self.filepath.open("a") as f:
                f.write(str(item) + "\n")
