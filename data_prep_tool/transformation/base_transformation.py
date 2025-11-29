class BaseTransformation:
    def apply(self, data):
        raise NotImplementedError()
    
    def to_script(self):
        raise NotImplementedError()
    
    def undo(self):
        raise NotImplementedError()