from TCPIPWrapper import TCPClient
from PySide import QtGui, QtCore
from Queue import Queue

class QuestionsClient(QtGui.QMainWindow):
    def __init__(self, ip, port):
        super(QuestionsClient, self).__init__()
        self.coms = Communicate()
        self.netQueue = Queue()

        self.coms.up.connect(self.handleUpdate)

        self.tcp = TCP(ip, port, self.netQueue, self.coms)
        self.tcp.start()

        # UI Elements
        self.answer = None
        self.question = None

        # Book keeping
        self.first = True
        self.trial = 0

        self.initUI()

    def initUI(self):
        widget = QtGui.QWidget()
        grid = QtGui.QGridLayout()

        self.answer = QtGui.QLabel()
        self.question = QtGui.QLabel()

        grid.addWidget(self.answer,0,0)
        grid.addWidget(self.question,1,0)

        widget.setLayout(grid)
        self.setCentralWidget(widget)
        self.setGeometry(300, 800, 200, 150)
        self.show()

    def handleUpdate(self):
        data = self.netQueue.get().strip()

        if self.first:
            text = ("The answer the other player is trying to "
                    + "guess is: {}".format(data))
            self.answer.setText(text)
            self.first = False
        elif data[-1] == "?":
            # Its a question :O
            self.trial += 1
            text = "Question {}: {}".format(self.trial, data)
            self.question.setText(text)
            QtGui.QApplication.processEvents()
            #self.sendResponse(data)
        elif data == "EOGW":
            self.question.setText("Game Over! They Won")
            self.tcp.con.close()
            self.tcp.terminate()
        elif data == "EOGL":
            self.question.setText("Game Over! They Lost")
            self.tcp.con.close()
            self.tcp.terminate()
        elif data == "REPLAY":
            self.first = True
            self.answer.setText("")
            self.question.setText("")
        else:
            # Its a guess
            text = "Is it...  {}".format(data)
            self.question.setText(text)
            QtGui.QApplication.processEvents()
            #self.sendResponse(text)

    def sendResponse(self, question):
        selection = raw_input(question.strip() + ": ")
        self.tcp.con.send(selection)

    # On close it closes the socket
    def closeEvent(self, event):
        if self.tcp.isRunning():
            self.tcp.terminate()

class TCP(QtCore.QThread):
    def __init__(self, ip, port, queue, coms):
        super(TCP, self).__init__()
        self.con = TCPClient(ip, port)
        self.q = queue
        self.coms = coms

    def run(self):
        while True:
            data = self.con.recvmostrecent()
            self.q.put(data)
            self.coms.up.emit()

# Only subclasses of QObject can act as a generic signal. This
# is used to tell the window to delete a certain line
class Communicate(QtCore.QObject):
    speak = QtCore.Signal(str)
    up = QtCore.Signal()

if __name__ == "__main__":
    app = QtGui.QApplication([])
    q = QuestionsClient("localhost", 10000)
    app.exec_()
