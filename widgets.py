from PySide import QtWidgets


class DnDTreeWidget(QtWidgets.QTreeWidget):
    '''
    TreeWidget with DnD ON.

    Allows dropping items as childs of another items.
    '''
    
    def __init__(self):
        super().__init__()
        self.setup()
        self.dragged_items = []
        
    def setup(self):
        '''Initialize drag and drop settings'''
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        # Use InternalMove as base, we'll customize behavior
        self.setDragDropMode(QtWidgets.QTreeWidget.InternalMove)
        
    def dropEvent(self, event):
        '''
        Custom drop event handler
        Makes dropped items become children of the target item
        '''
        
        drop_pos = event.pos()
        target_item = self.itemAt(drop_pos)
        drop_indicator = self.dropIndicatorPosition()
        dragged_items = self.selectedItems()
        
        if not dragged_items:
            event.ignore()
            return
        
        print(f'Dragged items: {[item.text(0) for item in dragged_items]}')
        
        # CASE 1: Dropping on a valid target item
        if target_item and drop_indicator == QtWidgets.QTreeWidget.OnItem:
            # Validate drop
            if not self.isValidDrop(dragged_items, target_item):
                print('Invalid drop - rejected')
                event.ignore()
                return
            self.set_parent(dragged_items, target_item)
            event.accept()
            
        # CASE 2: Dropping between items (above/below) or on empty area
        else:
            super().dropEvent(event)
    
    def isValidDrop(self, dragged_items, target_item):
        '''Check if drop is valid'''
        
        # Can't drop on itself
        for item in dragged_items:
            if item == target_item:
                return False
            
            # Can't drop a parent onto its child
            if self.is_descendant(item, target_item):
                return False
        
        return True
    
    def is_descendant(self, ancestor, item):
        parent = item.parent()
        while parent:
            if parent == ancestor:
                return True
            parent = parent.parent()
        return False
    
    def set_parent(self, items, new_parent):
        '''
        Make the dropped items become children of new_parent
        
        This is the key function that does the actual reparenting
        '''
        print(f'Making {len(items)} items children of "{new_parent.text(0)}"')
        
        self.blockSignals(True)
        
        for item in items:
            old_parent = item.parent()
            old_parent_text = old_parent.text(0) if old_parent else "Top Level"
            if old_parent:
                old_parent.removeChild(item)
            else:
                self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            new_parent.addChild(item)
            
            print(f"  Moved '{item.text(0)}' from {old_parent_text} to '{new_parent.text(0)}'")
        new_parent.setExpanded(True)
        self.blockSignals(False)