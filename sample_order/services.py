"""Sample registration/lookup/search services. No console input/output here."""


class DuplicateSampleError(Exception):
    """Raised when registering a sample_id that already exists."""


class SampleService:
    def __init__(self):
        self._samples = []

    def register(self, sample):
        if any(s.sample_id == sample.sample_id for s in self._samples):
            raise DuplicateSampleError(f"이미 등록된 시료 ID입니다: {sample.sample_id}")
        self._samples.append(sample)
        return sample

    def list_all(self):
        return list(self._samples)

    def search(self, keyword):
        return [s for s in self._samples if keyword in s.name or keyword in s.sample_id]
