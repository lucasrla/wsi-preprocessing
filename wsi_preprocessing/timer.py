import datetime


class Timer:
    def __init__(self):
        self.started_at = datetime.datetime.now()

    def elapsed(self):
        self.ended_at = datetime.datetime.now()
        return self.ended_at - self.started_at

    def print_elapsed(self, n):
        print(f"  {n} | {self.elapsed():-14s}")