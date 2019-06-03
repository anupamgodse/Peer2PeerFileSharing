# Peer2PeerFileSharing

Implemented a "Centralized Index Sever-P2P" system for file sharing between peers.
Following is short description of the system:
1) The Peers who wish to share files they have, can join the system by connecting to the server and add the list of files(to the centralized server) they wish to share with other client on a particular upload port.
2) Whenever a client needs a particular file, it can query the server for the available list of peers having that file.
3) The server replies with the upload port and ip address of the peer having the file.
4) The peer then can query any one of the peers for the file with a download request and then receives require file.

Following are the available query/request list (protocol):
Between Peer and Server:
  ADD file - Informs server that this peer has a file and is accepting request at upload port.  
  LOOKUP file - Asks server if this file is present with any of the peers, server returns with list of clients with their ip, upload port  
  LIST files - Asks server to list all the files with peer addresses(ip, upload port)  
  LOGOUT - Asks server to delete all the peer associated records indicating the peer is now offline  
  
Between Peer and Peer:  
  DOWNLOAD file - Asks a particular peer for some file (known from server that this peer has this file
