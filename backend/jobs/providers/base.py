class JobProvider:
    def search_jobs(self, query, location=None, page=1):
        raise NotImplementedError('Subclasses must implement search_jobs().')
