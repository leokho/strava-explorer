import pathlib

class Rowling():
    def __init__(self, filepath):
        self.filepath = filepath
        if not filepath.exists():
            filepath.mkdir(exist_ok=True, parents=True)

    def file_exists(self, id):
        path_to_check = self.filepath / (id + '.json')
        return path_to_check.exists()

    def write_to_file(self, id, content):
        path_to_write = self.filepath / (id + '.json')
        path_to_write.write_text(content)
