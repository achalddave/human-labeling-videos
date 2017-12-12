from abc import ABCMeta, abstractmethod
from collections import namedtuple

FrameSample = namedtuple('FrameSample', ['filename', 'frame', 'pre_context',
                                         'post_context', 'labels'])

class DataLoader(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def sample_balanced(self,
                        num_samples_per_label,
                        num_background_samples,
                        seed=None,
                        pre_context=0,
                        post_context=0):
        """
        Args:
            num_samples_per_label (int)
            num_background_samples (int)
            seed (int)
            pre_context (int)
            post_context (int)

        Returns:
            samples (list of FrameSample)
        """
        pass

    @abstractmethod
    def sample_random(self,
                      min_samples_per_label,
                      num_samples,
                      seed=None,
                      pre_context=0,
                      post_context=0):
        """
        Args:
            num_samples (int)
            min_samples_per_label (int): If specified and non-zero, then
                the num_samples argument is treated as a minimum number of
                samples. We will sample frames until there are at least
                num_samples samples, *and* at least min_samples_per_label for
                each label.
            seed (int)
            pre_context (int)
            post_context (int)

        Returns:
            samples (list of FrameSample)
        """
        pass

    def sample(self, method, *args, **kwargs):
        assert(method in ('balanced', 'random'))
        if method == 'balanced':
            return self.sample_balanced(*args, **kwargs)
        elif method == 'random':
            return self.sample_random(*args, **kwargs)

    @abstractmethod
    def frames_per_second(self):
        """
        Returns:
            frames_per_second (int)
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
