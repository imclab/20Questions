from TCPIPWrapper import TCPClient

s = TCPClient('d-173-250-205-216.dhcp4.washington.edu', 2223)

while True:
    print s.recvmostrecent()
