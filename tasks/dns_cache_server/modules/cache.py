import datetime
import pickle


class Cache:
    def __init__(self):
        self.map = {}

    def __contains__(self, question_entry):
        return question_entry in self.map

    def get_response_records(self, question_entry):
        value = self.map.get(question_entry, None)
        if value is None:
            return None

        response_records, updated = value
        for section in response_records:
            for resource_record in section:
                passed = (datetime.datetime.now() - updated).total_seconds()
                if resource_record.ttl < passed:
                    return None
        return response_records

    def update(self, question_entry, response_records):
        self.map[question_entry] = (response_records, datetime.datetime.now())


    def save(self):
        with open('cache.pickle', 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls):
        try:
            with open('cache.pickle', 'rb') as f:
                return pickle.load(f)
        except (FileNotFoundError, EOFError):
            return cls()

