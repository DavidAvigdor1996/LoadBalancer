import socket, Queue, sys, time, threading

HTTP_PORT = 80
previous_server = 3
lock = threading.Lock()
SERV_HOST = '10.0.0.1'
serverWeights = {"M": [2, 2, 1], "V": [1, 1, 3], "P": [1, 1, 2]}
serverWorkTimes = [0, 0, 0]
prevreqTime = 0
servers = {'serv1': ('192.168.0.101', None), 'serv2': ('192.168.0.102', None), 'serv3': ('192.168.0.103', None)}
BUFFER_SIZE=1024
def LBPrint(string):
    print('%s: %s-----' % (time.strftime('%H:%M:%S', time.localtime(time.time())), string))

def createSocket(addr, port):
    for res in socket.getaddrinfo(addr, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        try:
            new_sock = socket.socket(af, socktype, proto)
        except socket.error as msg:
            LBPrint(msg)
            new_sock = None
            continue

        try:
            new_sock.connect(sa)
        except socket.error as msg:
            LBPrint(msg)
            new_sock.close()
            new_sock = None
            continue

        break

    if new_sock is None:
        LBPrint('could not open socket')
        sys.exit(1)
    return new_sock

def getServerSocket(servID):
    name = 'serv%d' % servID
    return servers[name][1]

def getServerAddr(servID):
    name = 'serv%d' % servID
    return servers[name][0]

def getNextServer(req_type, req_time, serverWorkTimes):
    global lock
    global previous_server
    global prevreqTime
    global serverWeights
    computedWorkTimes = [(serverWorkTimes[i] + serverWeights[req_type][i] * req_time) for i in range(3)]
    return computedWorkTimes.index(min(computedWorkTimes))

    for i in range(3):
        serverWorkTimes[i] = max(serverWorkTimes[i] - req_time, 0)
    lock.acquire()
    next_server = previous_server % 3 + 1
    previous_server = next_server
    lock.release()
    return next_server

def parseRequest(req):
    return (req[0], req[1])

def handle_client(client_sock):
    global lock
    global prevreqTime
    global serverWorkTimes
    currentTime = time.clock()
    passed = currentTime - prevreqTime
    prevreqTime = currentTime

    req = client_sock.recv(1024)
    req_type, req_time = parseRequest(req)
    LBPrint('received a request for type ' + req_type + ' and time ' + req_time)
    lock.acquire()
    for i in range(3):
        serverWorkTimes[i] = max(serverWorkTimes[i] - passed, 0)
    servID = getNextServer(req_type, int(req_time), serverWorkTimes) + 1
    LBPrint('this is the server chosen: ' + str(servID))
    serverWorkTimes[servID - 1] += serverWeights[req_type][servID - 1] * int(req_time)
    LBPrint('this is server work times: ')
    LBPrint(serverWorkTimes)
    lock.release()
    LBPrint('received request %s from %s, sending to %s' % (req, client_sock.getpeername(), getServerAddr(servID)))
    serv_sock = getServerSocket(servID)
    serv_sock.sendall(req)

    client_sock.close()

if __name__ == '__main__':
    try:
        LBPrint('LB Started')
        LBPrint('My LB Started')
        LBPrint('Connecting to servers')
        for name, (addr, sock) in servers.items():
            servers[name] = (addr, createSocket(addr, HTTP_PORT))

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((SERV_HOST, HTTP_PORT))
        server_sock.listen(5)
        LBPrint('Load Balancer listening on %s:%d' % (SERV_HOST, HTTP_PORT))

        while True:
            client_sock, addr = server_sock.accept()
            LBPrint('Accepted connection from %s' % str(addr))
            client_handler = threading.Thread(target=handle_client, args=(client_sock,))
            client_handler.start()

    except socket.error as msg:
        LBPrint(msg)