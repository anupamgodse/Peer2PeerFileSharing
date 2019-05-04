from multiprocessing import Process, Manager, Lock
import os
import time
import socket
import sys
from threading import Thread

VERSION="P2P-CI/1.0";
MAX_BUFF_LEN=4096
SERVER_PORT=7734
OK=200
BAD_REQUEST=400
NOT_FOUND=404
VERSION_NOT_SUPPORTED=505
STATUS_CODES={OK:"OK", BAD_REQUEST:"Bad Request", NOT_FOUND:"Not Found", VERSION_NOT_SUPPORTED:"P2P-CI Version Not Supported"}
#HOSTNAME=socket.gethostname()
HOST_IP = '10.155.18.166'
HOST_NAME = '10.155.18.166'

#a list to store active peers
peers = list();
# a lock to synchronise active peers list operations
lock_peers = Lock();

#a dictionary to store availabe RFCs and peers containing them
rfcs = dict();
# a lock to synchronise rfcs dictionary operations
lock_rfcs = Lock();

#a RFC dictionary item value (dictionary item key would be rfc number)
class Rfc:
    def __init__(self, number, title, hostname):
        self.number = number
        self.title = title
        self.hostname = hostname

#a peer would have a hostname and a port to communicate with CI server
class Peer:
    def __init__(self, hostname, port):
        self.hostname = hostname
        self.port = port

def check_peer_active(hostname, lock_peers, peers):
    lock_peers.acquire()
    for peer in peers:
        if(peer.hostname == hostname):
            lock_peers.release();
            return True

    lock_peers.release();
    return False;
    

def send_response(connection, status_code, data):
    response = VERSION+" "+str(status_code)+" "+STATUS_CODES[status_code]+"\r\n"+\
                "\r\n"

    for each in data:
        response = response+each[0]+" "+each[1]+" "+each[2]+" "+each[3]+"\r\n"

    response = response+"\r\n" 

    connection.sendall(response.encode())


def serve_client(connection, client_address):
    try:
        #serve client requests
        while True:
            data = connection.recv(MAX_BUFF_LEN)
            if not data:
                break;
                #continue;
            #print("received "+str(data.decode()))
            request = data.decode().split('\r\n');

            request_row_1 = request[0].split();
            request_type = request_row_1[0];
            rfc_version = request_row_1[-1];

            request_row_2=request[1].split();
            client_hostname=request_row_2[1];

            request_row_3=request[2].split();
            client_port=int(request_row_3[1]);

            response_data = [];
            #process ADD request from client
            if(request_type == "ADD"):
                rfc_number = int(request_row_1[2]);
                rfc_title = request[3].split()[1];
                response_code=OK;
                
                response_data.append(["RFC"+str(rfc_number), rfc_title, client_hostname, str(client_port)])
                #correct version check
                if(rfc_version!=VERSION):
                    response_code = VERSION_NOT_SUPPORTED;
                else:
                    #check if this peer is already present in active list
                    is_peer_active = check_peer_active(client_hostname, lock_peers, peers)
                    if not is_peer_active:
                        new_peer = Peer(client_hostname, client_port)
                        lock_peers.acquire()
                        peers.insert(0, new_peer);
                        lock_peers.release()

                    new_rfc = Rfc(rfc_number, rfc_title, client_hostname);
                    #Add this RFC to RFCs list
                    lock_rfcs.acquire()
                    #print("keys");
                    #print(rfcs.keys())
                    if rfc_number in rfcs.keys():
                        #check if client has already added that RFC(avoid duplication)
                        already_present = False;
                        for client in rfcs[rfc_number]:
                            if(client.hostname == client_hostname):
                                already_present = True;
                                #print("Already Present\n");
                                break;
                        if not already_present:
                            #print("appending")
                            #print(new_rfc.number, new_rfc.title, new_rfc.hostname)
                            #print(type(rfcs[rfc_number]))
                            #print(type(rfcs))
                            rfcs[rfc_number] = rfcs[rfc_number] + [new_rfc];
                        """for each, value in rfcs.items():
                            print(each);
                            for e in value:
                                print(e.number, e.title, e.hostname)
                            print("\n\n");"""
                    else:
                        #rfcs[rfc_number] = list();
                        rfcs[rfc_number] = [new_rfc] #list();
                        #rfcs[rfc_number].append(new_rfc);
                    lock_rfcs.release()
                send_response(connection, response_code, response_data);
                """for each, value in rfcs.items():
                    print(each);
                    for e in value:
                        print(e.number, e.title, e.hostname)
                    print("\n\n");"""
            elif(request_type=="LOOKUP"):
                rfc_number = int(request_row_1[2]);
                rfc_title = request[3].split()[1];
                response_code = OK;

                #correct version check
                if(rfc_version!=VERSION):
                    response_code = VERSION_NOT_SUPPORTED;
                else:
                    #check if this rfc is present
                    lock_rfcs.acquire()
                    lock_peers.acquire()
                    if rfc_number in rfcs.keys():
                        #if rfc is present add all hosts having this rfc to response_data
                        rfcs_list = rfcs[rfc_number]
                        for rfc in rfcs_list:
                            for peer in peers:
                                if(rfc.hostname == peer.hostname):
                                    response_data.append(["RFC"+str(rfc_number), rfc_title, peer.hostname, str(peer.port)])
                    else:
                        response_code = NOT_FOUND;
                    lock_peers.release()
                    lock_rfcs.release()
                send_response(connection, response_code, response_data);
            elif(request_type=="LIST"):
                """for each, value in rfcs.items():
                    print(each);
                    for e in value:
                        print(e.number, e.title, e.hostname)
                    print("\n\n");"""
                response_code = OK;
                lock_rfcs.acquire()
                lock_peers.acquire()
                for rfc_number in rfcs.keys():
                   rfcs_list = rfcs[rfc_number] 
                   for rfc in rfcs_list:
                       for peer in peers:
                           if(rfc.hostname == peer.hostname):
                                response_data.append(["RFC"+str(rfc_number), rfc.title, peer.hostname, str(peer.port)])
                lock_peers.release()
                lock_rfcs.release()
                send_response(connection, response_code, response_data);

    finally:
        # Clean up the connection
        print("Closing connection to ", client_address)

        lock_rfcs.acquire()

        for key, l in rfcs.copy().items():
            for each in l:
                if(each.hostname == client_address[0]):
                    rfcs[key].remove(each)

            if not l:
                rfcs.pop(key)
                
        lock_rfcs.release()

        lock_peers.acquire()

        print(client_address)
        for each in peers.copy():
            #print(each.hostname, each.port)
            if each.hostname == client_address[0]:
                peers.remove(each)

        #peers.remove(client_address[0])

        lock_peers.release()

        connection.close()
        exit(0)

#Server main
if __name__ == '__main__':
    #processes
    spawned = [];

    #a well known server port to accept requests from clients
    server_port = SERVER_PORT;

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);

    # Bind the socket to the port
    #server_address = (HOSTNAME, server_port);
    server_address = (HOST_IP, server_port);
    #print >>sys.stderr, 'starting up on %s port %s' % server_address
    sock.bind(server_address);

    
    #start listening on server_port
    sock.listen();
     
    i=0
    #keep on accepting new connections from client and spawn new process for each client
    while True:
        print('waiting for a connection');
        connection, client_address = sock.accept();

        #p = Process(target=serve_client, args=(peers, rfcs, lock_peers, lock_rfcs, connection, client_address))
        p = Thread(target=serve_client, args=(connection, client_address))
        i+=1

        spawned.append(p)

        p.start()

    #this should never be executed
    for process in spawned:
        process.join()
