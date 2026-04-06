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
        raise NotImplementedError

    def set(self, storage):
        raise NotImplementedError


class BooleanField(StorageField):
    def get(self, storage):
        return storage.GetBool

    def set(self, storage):
        return storage.SetBool


class StringField(StorageField):
    def get(self, storage):
        return storage.GetString

    def set(self, storage):
        return storage.SetString


class JsonField(StringField):
    def __set__(self, instance, value):
        value = json.dumps(value)
        super().__set__(instance, value)

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        return json.loads(value)


class Storage:
    shape = StringField(default="line")
    overlay_panel_on = BooleanField(default=False)
    tools = JsonField(default="{}")
    index = JsonField(default="{}")
    position = StringField(default="top")
    orientation = StringField(default="horizontal")

    def __init__(self, storage):
        self._storage = storage
        self.active_wb = None
        self.checked_tools = None
        self.workbenches = None
        self.wbtools = {}
