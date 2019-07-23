from abc import ABC, abstractmethod


class Labeler(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def submit(self, info):
        pass
    
    def public_directories(self):
        return []
