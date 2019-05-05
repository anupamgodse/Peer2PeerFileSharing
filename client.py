from multiprocessing import Process, Manager, Lock
import os
import time
import socket
import sys
import re
from os import listdir
from os.path import isfile, join
import platform
from time import gmtime, strftime
from threading import Thread

VERSION="P2P-CI/1.0"
HOSTOS=platform.platform()
MAX_RESPONSE_SIZE=4096
MAX_REQUEST_SIZE=4096
SERVER_PORT=7734
RFCS_PATH = "./RFCs/client1/"
OK=200
BAD_REQUEST=400
NOT_FOUND=404
VERSION_NOT_SUPPORTED=505
STATUS_CODES={OK:"OK", BAD_REQUEST:"Bad Request", NOT_FOUND:"Not Found", VERSION_NOT_SUPPORTED:"P2P-CI Version Not Supported"}

SERVER_NAME = '192.168.1.27'

#HOSTNAME=socket.gethostname()
HOSTNAME = '192.168.1.27'
HOST_IP = socket.gethostbyname(HOSTNAME)


#init
my_rfcs = list();

#lock to perform operations on list of RFCS
lock_my_rfcs = Lock()

#upload port for client
upload_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
upload_sock.bind((HOST_IP, 0));
my_upload_port = upload_sock.getsockname()[1]


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


def serve_peers():
    #start listening to peer requests
    upload_sock.listen()

    while True:
        peer_sock, peer_address = upload_sock.accept()
        #print("Accepted ", peer_address)
        request = peer_sock.recv(MAX_REQUEST_SIZE)
        if not request:
            continue;

        request = request.decode().split('\r\n')
        request_row_1 = request[0].split()  
        request_type = request_row_1[0]
        rfc_number = int(request_row_1[2])
        version = request_row_1[-1]

        response_code = OK

        data = ""
        filepath = ""
        response=""

        if(version != VERSION):
            response_code = VERSION_NOT_SUPPORTED
        else:
            #check if requested rfc is present
            lock_my_rfcs.acquire() 
            if(rfc_number not in my_rfcs):
                response_code = NOT_FOUND
            lock_my_rfcs.release()
                
            if(response_code == NOT_FOUND):
                response = VERSION+" "+str(response_code)+" "+STATUS_CODES[response_code]+"\r\n"+\
                            "\r\n"
            else:
                filepath = RFCS_PATH+'rfc'+str(rfc_number)+'.txt'
                current_time = strftime("%a, %d %b %Y %X GMT", gmtime())
                modified_time = strftime("%a, %d %b %Y %X GMT", time.localtime(os.path.getmtime(filepath)))
                with open(filepath, 'r') as myfile:
                      data = myfile.read()

                data_length = str(len(data))

                response = VERSION+" "+str(response_code)+" "+STATUS_CODES[response_code]+"\r\n"+\
                            "Date: "+current_time+"\r\n"+\
                            "OS: "+HOSTOS+"\r\n"+\
                            "Last-Modified: "+ modified_time+"\r\n"+\
                            "Content-Length: " + data_length+"\r\n"+\
                            "Content Type: text/text\r\n"+\
                            data+"\r\n"+\
                            "\r\n"

        peer_sock.sendall(response.encode())
        peer_sock.close()


#Add available RFC to the server
def add_rfc(sock, rfc):
    rfc_title = rfc.split('.')[0]
    rfc_number = int(rfc_title[3:])
    add_request = "ADD"+" "+"RFC "+str(rfc_number)+" "+VERSION+"\r\n"+\
                    "Host:"+" "+HOSTNAME+"\r\n"+\
                    "Port:"+" "+str(my_upload_port)+"\r\n"+\
                    "Title:"+" "+rfc_title+"\r\n"+\
                    "\r\n";
    
    #print(add_request)

    sock.sendall(add_request.encode());

    response = sock.recv(MAX_RESPONSE_SIZE).decode();

    if(int((response.split('\r\n')[0]).split()[1]) == OK):
        lock_my_rfcs.acquire()
        if rfc_number not in my_rfcs:
            my_rfcs.append(rfc_number)
        lock_my_rfcs.release()

    return response;

#lookup  RFC
def lookup_rfc(sock, rfc_number, rfc_title):
    lookup_request = "LOOKUP"+" "+"RFC "+str(rfc_number)+" "+VERSION+"\r\n"+\
                    "Host:"+" "+HOSTNAME+"\r\n"+\
                    "Port:"+" "+str(my_upload_port)+"\r\n"+\
                    "Title:"+" "+rfc_title+"\r\n"+\
                    "\r\n";
    
    #print(lookup_request)

    sock.sendall(lookup_request.encode());

    response = sock.recv(MAX_RESPONSE_SIZE).decode();
    return response;

#list RFCs at server
def list_rfcs(sock, my_upload_port):
    list_request = "LIST"+" "+"ALL "+VERSION+"\r\n"+\
                    "Host:"+" "+HOSTNAME+"\r\n"+\
                    "Port:"+" "+str(my_upload_port)+"\r\n"+\
                    "\r\n";
    
    #print(list_request)

    sock.sendall(list_request.encode());

    response = sock.recv(MAX_RESPONSE_SIZE).decode();
    return response;
    

def rfc_download_request(rfc_number, hostname, port):
    download_request = "GET"+" RFC "+str(rfc_number)+" "+VERSION+"\r\n"+\
                "Host: "+hostname+"\r\n"+\
                "OS: "+HOSTOS+"\r\n"+\
                "\r\n"

    
    download_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    host_ip = socket.gethostbyname(hostname)
    download_sock.connect((host_ip, port))
    
    download_sock.sendall(download_request.encode())
    
    data = ''
    while True:
        response = download_sock.recv(MAX_RESPONSE_SIZE).decode()
        if not response:
            break
        data+=response


    split_response = data.split('\r\n')

    #changed
    content_len = int(split_response[4].split(':')[1])

    if(int(split_response[0].split()[1]) != OK):
        return '\r\n'.join(split_response[:6])

    #data = split_response[6]
    data = data[-4-content_len:-4]

    filepath = RFCS_PATH+'rfc'+str(rfc_number)+'.txt'

    myfile = open(filepath, 'w')

    myfile.write(data)

    myfile.close()
    download_sock.close()
    
    return '\r\n'.join(split_response[:6])
    #return response

def print_options():
    print("1. ADD")
    print("2. LOOKUP")
    print("3. LIST")
    print("4. Download RFC")
    print("5. LOGOUT")

#Client main
if __name__ == '__main__':
    #spawn a thread to serve other peers
    p_serve_peers = Thread(target=serve_peers);

    p_serve_peers.daemon = True
    p_serve_peers.start()

    SERVER_IP = socket.gethostbyname(SERVER_NAME)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    sock.connect((SERVER_IP, SERVER_PORT))

    while True:
        print_options()
        option = int(input("Enter option: "))
        if(option == 1):
            rfc = input("Enter filename: ")
            response = add_rfc(sock, rfc)
            print("Added RFC "+ str(rfc) + "\nResponse from server is:\n" +response);
        elif(option == 2):
            lookup_rfc_number = input("Enter RFC number to lookup for: ")
            lookup_rfc_title = 'rfc'+str(lookup_rfc_number) 
            response = lookup_rfc(sock, lookup_rfc_number, lookup_rfc_title)
            print("Lookup RFC "+ str(lookup_rfc_number) + "\nResponse from server is:\n" +response);
        elif(option == 3):
            response = list_rfcs(sock, my_upload_port)
            print("LIST RFC\nResponse from server is:\n" +response);
        elif(option == 4):
            download_rfc_number = input("Enter RFC number: ");
            get_rfc_from = input("Enter host: ");
            get_rfc_from_port = int(input("Enter port: "));
            response = rfc_download_request(download_rfc_number, get_rfc_from, get_rfc_from_port);
            print("Download RFC\nResponse from server is:\n" +response);
        elif(option == 5):
            sock.close()
            exit(0)
