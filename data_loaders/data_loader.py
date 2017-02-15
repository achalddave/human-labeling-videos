from abc import ABCMeta, abstractmethod
from collections import namedtuple

FrameSample = namedtuple('FrameSample', ['filename', 'frame', 'pre_context',
                                         'post_context', 'labels'])

class DataLoader(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def sample(self,
               num_samples_per_label,
               num_background_samples,
               seed=None,
               pre_context=0,
               post_context=0):
        """
        Args:
            num_samples_per_label (int)
            seed (int)
            pre_context (int)
            post_context (int)

        Returns:
            samples (list of FrameSample)
        """
        pass

    @abstractmethod
    def labels(self):
        """
        Returns:
            labels (dict from string to int): Maps label names to (numeric)
                label ids.
        """
        pass
