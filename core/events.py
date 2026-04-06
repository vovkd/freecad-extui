import uuid
import FreeCAD as App


class DocumentEventsHandler:
    def __init__(self, app, handlers=[]):
        self.app = app
        self.observer = None
        self.setup_observer()
        self.handlers = handlers
        self.is_created = False

    def setup_observer(self):
        self.observer = App.addDocumentObserver(self)

    def slotActivateDocument(self, doc):
        App.Console.PrintMessage(f"Document activated: {doc.Name}", self.is_created)
        if self.is_created:
            self.on_document_load(doc)

    def slotCreatedDocument(self, doc):
        App.Console.PrintMessage(f"Document created: {doc.Name}")
        doc.addProperty("App::PropertyString", "uid", "CustomAttributes")
        setattr(doc, "uid", str(uuid.uuid4()))
        self.is_created = True
        self.on_document_load(doc)

    def slotRestoredDocument(self, doc):
        App.Console.PrintMessage(f"Document to be opened: {doc.Name}")

    def on_document_load(self, doc):
        for handler in self.handlers:
            handler(doc)

    def __del__(self):
        try:
            App.removeDocumentObserver(self)
        except:
            pass
