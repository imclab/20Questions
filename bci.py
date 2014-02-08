from TCPIPWrapper import TCPServer

s = TCPServer(2222)

while True:
    input = raw_input("Enter 1 for Yes, 0 for No: ")
    s.send(input)

