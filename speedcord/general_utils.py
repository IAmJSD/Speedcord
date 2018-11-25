class DictSwitch(dict):
    """A class that automatically flips a boolean in a class depending on if it is occupied or not."""
    def __init__(self, cls, attribute, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cls = cls
        self._attribute = attribute

    def __setitem__(self, key, value):
        before = len(self)
        try:
            return super().__setitem__(key, value)
        finally:
            if before == 0:
                attr_res = self._cls.__getattr__(self._attribute)
                self._cls.__setattr__(self._attribute, not attr_res)

    def __delitem__(self, key):
        try:
            return super().__delitem__(key)
        finally:
            if len(self) == 0:
                attr_res = self._cls.__getattr__(self._attribute)
                self._cls.__setattr__(self._attribute, not attr_res)
