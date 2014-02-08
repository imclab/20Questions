import sys
import random
import socket
from PySide import QtGui, QtCore

class QuestionsGameTwoGUI(QtGui.QMainWindow):

    def __init__(self, qp):
        super(QuestionsGameTwoGUI, self).__init__()
        self.qp = qp
        self.answer = None

        #[[object, bool]]
        # The answers and questions being displayed
        self.answers = None
        self.questions = None

        # TCP connections
        self.clientConnection = None
        self.tmsConnection = None

        # UI elements
        self.qDict= None
        self.aDict = None
        self.status = None
        self.submitButton = None

        # The trial count
        self.trial = None

        # Sets whether answers are shown as red when they
        # are no longer feasible
        self.deleteAnswers = True

        self.setup()
        self.initUI()
        self.connectToClient('0.0.0.0', 10000)
        self.connectToTMS('128.208.5.218', 2223)
        self.populateList()

    def connectToClient(self, ip, port):
        print "Connecting to client app"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen(1)
        (self.clientConnection, addr) = s.accept()
        self.clientConnection.settimeout(10.0)
        self.sendRandomAnswer()

    def connectToTMS(self, ip, port):
        print "TCP connection opened for TMS"
        self.tmsConnection = socket.create_connection((ip, port), 10)
        self.tmsConnection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tmsConnection.settimeout(10.0)

    def setup(self):
        # For replaying
        self.answers = [[a, True] for a in self.qp.leafs]
        self.questions = [[q, True] for q in self.qp.questions]
        self.trial = 0

    def replay(self):
        self.setup()
        self.populateList()
        self.status.setText("Question #" + str(self.trial))
        self.sendRandomAnswer()

    def initUI(self):
        widget = QtGui.QWidget()
        grid = QtGui.QGridLayout()

        self.qList = QtGui.QListWidget()
        self.aList = QtGui.QListWidget()

        self.aList.itemClicked.connect(self.deselectQList)
        self.qList.itemClicked.connect(self.deselectAList)

        for i in [0,2]:
            grid.setColumnMinimumWidth(i,60)
            grid.setColumnStretch(i, 1)

        self.submitButton = QtGui.QPushButton("Submit")
        self.submitButton.clicked.connect(self.submit)

        aLabel = QtGui.QLabel("Possible Answers:")
        qLabel = QtGui.QLabel("Possible Questions:")
        self.status = QtGui.QLabel("Question #" + str(self.trial))

        grid.addWidget(aLabel,0,0)
        grid.addWidget(qLabel,0,2)
        grid.addWidget(self.aList,1,0)
        grid.addWidget(self.qList,1,2)
        grid.addWidget(self.submitButton, 4,2)
        grid.addWidget(self.status,4,0)

        widget.setLayout(grid)
        self.setCentralWidget(widget)
        self.setGeometry(300, 300, 640, 480)
        self.show()
        QtGui.QApplication.processEvents()

    def deselectQList(self, item):
        self.qList.setCurrentRow(-1)

    def deselectAList(self, item):
        self.aList.setCurrentRow(-1)

    def enableButton(self):
        self.submitButton.setEnabled(True)

    def submit(self):
        # Update trial text
        self.trial += 1
        self.status.setText("Question #" + str(self.trial))

        # Disable the button and re-enable after 15 seconds
        self.submitButton.setDisabled(True)
        self.update()

        # Determine if the user selected an answer or a question
        aRow = self.aList.currentRow()
        qRow = self.qList.currentRow()
        choice = self.questions[qRow] if aRow == -1 else self.answers[aRow]

        # Send text to client
        if aRow == -1:
            self.clientConnection.send("Question is " + choice[0].text+"\n")
        else:
            self.clientConnection.send("Is it a " + choice[0].text+"\n")

        # Get result from BCI
        print "getting bci answer"
        bciRes = self.bciAnswer()
        print "got bci answer " + str(bciRes)

        # Handle when timeout without data received
        if bciRes == None:
            QuestionsGameTwoGUI.showMessage("No Data Received")
            self.submitButton.setEnabled(True)
            return

        # Fire TMS
        if bciRes:
            print "sending to tms"
            self.tmsConnection.send("1\n")
            print "sent to tms"

        # Re-enable button after 15 seconds
        QtCore.QTimer.singleShot(15000, self.enableButton)

        # Perceived Result after querying user
        res = self.playAgain(False, "Did you see a light?")

        # Send the users selection back for logging
        response = "TMS SEEN\n" if res else "TMS NOT SEEN\n"
        self.clientConnection.send(response)


        if choice[0].isAnswer():
            if res:
                again = self.playAgain(True)
                if not again:
                    QtGui.QApplication.quit()
                else:
                    self.replay()
            else:
                if self.deleteAnswers:
                    for a in self.answers:
                        if a[0] == choice[0]:
                            a[1] = False
                            break

                if self.trial == 20:
                    again = self.playAgain(False)
                    if not again:
                        QtGui.QApplication.quit()
                    else:
                        self.replay()
                else:
                    QuestionsGameTwoGUI.showMessage("Wrong Choice")

        # User selected a question
        else:
            direction = False if res else True
            quesToRemove = self.qp.questionsBellow(choice[0], direction)
            quesToRemove.append(choice[0])

            # Mark above questions in red
            for r in quesToRemove:
                for q in self.questions:
                    if q[0] == r:
                        q[1] = False
                        break

            if self.deleteAnswers:
                noAnswers = self.qp.answersBellow(choice[0], direction)
                for n in noAnswers:
                    for a in self.answers:
                        if a[0] == n:
                            a[1] = False
                            break

        self.populateList()

    def sendRandomAnswer(self):
        """ Sends a random answer for the other user to answer
        yes or no to """
        self.answer = random.choice(self.answers)[0]
        print self.answer
        self.clientConnection.send("Answer: " + self.answer.text+"\n")

    def populateList(self):
        self.aList.clear()
        self.qList.clear()

        # Populate Lists
        for (k,v) in self.answers:
            t = QtGui.QListWidgetItem(k.text, self.aList)

            if not v:
                t.setBackground(QtGui.QColor('red'))


        for (k,v) in self.questions:
            t = QtGui.QListWidgetItem(k.text, self.qList)

            if not v:
                t.setBackground(QtGui.QColor('red'))


    def closeEvent(self, event):
        self.clientConnection.close()
        self.tmsConnection.close()

    def bciAnswer(self):
        try:
            data = self.clientConnection.recv(4096)
            print data

            if data == "yes":
                return True
            elif data == "no":
                return False
            else:
                return None
        except Exception:
            return None


    def playAgain(self, victory, customText=None):
        """ Displays a play again message, returns a boolean but
        does not handle setting up a new  game.

        Args:
            victory: a boolean that either displays a lost message or victory
            customText: if set, that text is displayed instead of
                        built in text
        """
        string = None
        if customText != None:
            string = customText
        elif victory:
            string = "You Won after " + str(self.trial) + " questions! Do you want to play again"
        else:
            string = "You lost! Play again?"

        msg = QtGui.QMessageBox()
        msg.setText(string)
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.No)
        msg.show()
        msg.raise_()
        ret = msg.exec_()

        if ret == QtGui.QMessageBox.Yes:
            return True
        else:
            return False

    @classmethod
    def showMessage(cls, string):
        msgBox = QtGui.QMessageBox()
        msgBox.setText(string)
        msgBox.show()
        msgBox.raise_()
        msgBox.exec_()


class QuestionParser():
    """
    Given a file describing a 20 Question game,
    it builds a tree and provides helper methods to
    facilitate the playing of a game
    """

    def __init__(self, qFile):
        """
        Initializes the tree

        Args:
            qFile:  Path to the file describing the game.
                    An example file is as follows.

                    Q: Is it an animal
                    A: Laptop
                    Q: Can it fly?
                    A: Bird
                    A: Cat

                    Animal?
                   /       \
            Laptop          Can it fly?
                            /           \
                        Bird            Cat
        """
        try:
            self.file = open(qFile, "r")
        except IOError as e:
            print "Could not open file: ", e
            sys.exit(1)

        self.leafs = []
        self.questions = []
        self.root = self.buildTree(self.file)

    def buildTree(self, f, parent=None):
        """ Recursively builds up the tree

        Args:
            f:  f is an open file handle on a file as
                described in the __init__ method
            parent: Defaults to None, but if provided,
                    sets new nodes parents to the parameter
        """
        cur = f.readline()
        parts = cur.split(":") #["Q/A", "Text"]

        if len(cur) == 0:
            # This is the end of file
            return None
        elif parts[0] == "A":
            temp = Node(parts[1], parent)
            self.leafs.append(temp)
            return temp
        else:
            temp = Node(parts[1], parent)
            left = self.buildTree(f, temp)
            right = self.buildTree(f, temp)

            temp.setLeft(left)
            temp.setRight(right)
            self.questions.append(temp)
            return temp


    def questionsBellow(self, node, direction):
        """ Returns a list of all the question nodes
        below the given node in either direction

        Args:
            node: The node to look bellow
            direction: A boolean value, true for left
                        and false for right
        """
        questions = []
        queue = []

        if direction:
            queue.append(node.left)
        else:
            queue.append(node.right)

        while len(queue) != 0:
            cur = queue.pop(0)

            if cur.isAnswer():
                continue
            else:
                questions.append(cur)
                queue.append(cur.left)
                queue.append(cur.right)

        return questions

    def answersBellow(self, node, direction):
        """ Returns a list of all the answer nodes
        below the given node in either direction

        Args:
            node: The node to look bellow
            direction: A boolean value, true for left
                        and false for right
        """
        answers = []
        queue = []

        if direction:
            queue.append(node.left)
        else:
            queue.append(node.right)

        while len(queue) != 0:
            cur = queue.pop(0)

            if cur.isAnswer():
                answers.append(cur)
            else:
                queue.append(cur.left)
                queue.append(cur.right)

        return answers

class Node():
    """
    Generic BST Node with a parent pointer
    """
    def __init__(self, text, par=None, left=None, right=None):
        """ A node of a tree that stores text and
            references to a left and right branch

        Args:
            text: Text representing a question/answer
            left/right: Default value is None, if provided
                        points to another Node
            par: Default is None, if provided is a ref to
                parent Node
        """

        self.text   = text
        self.left   = left
        self.right  = right
        self.parent = par

    def getText(self):
        """ Returns the text stored by the node """
        return self.text

    def setParent(self, node):
        """ Sets the parent node

        Args:
            node: the parent Node
        """
        self.parent = node

    def setLeft(self, node):
        """ Sets the left node

        Args:
            node: the left child Node
        """
        self.left = node

    def setRight(self, node):
        """ Sets the right node

        Args:
            node: the right child Node
        """
        self.right = node

    def isAnswer(self):
        """ Returns whether the current Node is an answer """
        return self.left == None and self.right == None

    def __repr__(self):
        if self.isAnswer():
            return "[Answer]: " + self.text
        else:
            return "[Question]: " + self.text

def usage():
    print "python questions.py [file]"

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        usage()
        sys.exit(1)

    questions = QuestionParser(sys.argv[1])
    app = QtGui.QApplication([])
    g = QuestionsGameTwoGUI(questions)
    app.exec_()
