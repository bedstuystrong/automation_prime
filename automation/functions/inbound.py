class NewCallback:
    def __init__(self, conf):
        pass

    def __call__(self, record):
        print(record)
