
class NotContained(Exception):
    def __init__(self, message):
        super().__init__(message)

class Environment:

    def __init__(self, filePath):
        self.env = {}
        self.envFilePath = filePath

        try:
            with open(self.envFilePath, "r") as env_file:
                for line in env_file:
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    self.env[key.strip().upper()] = value.strip()
        except FileNotFoundError:
            pass

    def get(self, key):
        key = key.upper();
        if not key in self.env:
            raise NotContained(f"Environment does not contain key: {key}")
        return self.env[key]


    def add(self, key, value):
        self.env[key.upper()] = str(value);

    def save(self):
       with open(self.envFilePath, 'w') as envFile:
           for key in sorted(self.env):
               envFile.write(f"{key}={self.env[key]}\n")

