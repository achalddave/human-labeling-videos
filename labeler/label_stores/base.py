from abc import ABC, abstractmethod


class LabelStore(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_unlabeled(self, num_items):
        pass

    @abstractmethod
    def num_completed(self):
        pass

    @abstractmethod
    def num_total(self):
        pass
