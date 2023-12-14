"""
Simple demonstration of TreeWidget, which is an extension of QTreeWidget
that allows widgets to be added and dragged within the tree more easily.
"""


import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets



class SettingsTree(pg.TreeWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(2)

        i1  = QtWidgets.QTreeWidgetItem(["Item 1"])
        i11  = QtWidgets.QTreeWidgetItem(["Item 1.1"])
        i12  = QtWidgets.QTreeWidgetItem(["Item 1.2"])
        i2  = QtWidgets.QTreeWidgetItem(["Item 2"])
        i21  = QtWidgets.QTreeWidgetItem(["Item 2.1"])
        i211  = pg.TreeWidgetItem(["Item 2.1.1"])
        i212  = pg.TreeWidgetItem(["Item 2.1.2"])
        i22  = pg.TreeWidgetItem(["Item 2.2"])
        i3  = pg.TreeWidgetItem(["Item 3"])
        i4  = pg.TreeWidgetItem(["Item 4"])
        i5  = pg.TreeWidgetItem(["Item 5"])
        b5 = QtWidgets.QPushButton('Button')
        i5.setWidget(1, b5)



        self.addTopLevelItem(i1)
        self.addTopLevelItem(i2)
        self.addTopLevelItem(i3)
        self.addTopLevelItem(i4)
        self.addTopLevelItem(i5)
        i1.addChild(i11)
        i1.addChild(i12)
        i2.addChild(i21)
        i21.addChild(i211)
        i21.addChild(i212)
        i2.addChild(i22)

        b1 = QtWidgets.QPushButton("Button")
        self.setItemWidget(i1, 1, b1)

if __name__ == '__main__':
    app = pg.mkQApp()
    tree = SettingsTree()
    tree.show()
    pg.exec()