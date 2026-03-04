import json

class StorageField:
    def __init__(self, value=None, default=None):
        self._default = default
        
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        storage = instance._storage
        handler = self.set(storage)
        handler(self.name, value)
        
        instance.__dict__[self.name] = value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        storage = instance._storage
        handler = self.get(storage)
        value = handler(self.name, self._default)
        
        return value

    def get(self, storage):
        raise NotImplementedError('<get handler> method is not implemented.')

    def set(self, storage):
        raise NotImplementedError('<set handler> method is not implemented.')


class BooleanField(StorageField):
    def get(self, storage):
        return storage.GetBool

    def set(self, storage):
        return storage.SetBool


class IntegerField(StorageField):
    def get(self, storage):
        return storage.GetInt

    def set(self, storage):
        return storage.SetInt


class FloatField(StorageField):
    def get(self, storage):
        return storage.GetFloat

    def set(self, storage):
        return storage.SetFloat


class StringField(StorageField):
    def get(self, storage):
        return storage.GetString

    def set(self, storage):
        return storage.SetString


class StringListField(StringField):
    def __set__(self, instance, value: list | tuple):
        value = ','.join(value)
        super().__set__(instance, value)
        return value

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        value = value.split(',')
        return value

class JsonField(StringField):
    def __set__(self, instance, value: list | tuple):
        value = json.dumps(value)
        super().__set__(instance, value)
        return value

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        value = json.loads(value)
        return value
    

class Storage:
    shape = StringField(default='line')
    overlay_panel_on = BooleanField(default=False)
    tools = JsonField(default='{}')

    def __init__(self, storage):
        self._storage = storage
        self.active_wb = None

        self.checked_tools = None
        self.workbenches = None
        self.wbtools = {}
