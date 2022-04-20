###### TEST ######### TEST ########### TEST #############
### INCOMPLET
import time
import socketserver
import importlib
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct

# Create the server, binding to localhost on port 9999
HOST, PORT = "192.168.1.36", 9999

#time job
tempoTrabalhar = 20

#miner id
minerAddr = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"

#server
serverAddr = "http://138.197.181.206:5005/" #https://siricoin-node-1.dynamic-dns.net:5005/

class SignatureManager(object):
    def __init__(self):
        self.verified = 0
        self.signed = 0
    
    def signTransaction(self, private_key, transaction):
        message = encode_defunct(text=transaction["data"])
        transaction["hash"] = w3.soliditySha3(["string"], [transaction["data"]]).hex()
        _signature = w3.eth.account.sign_message(message, private_key=private_key).signature.hex()
        signer = w3.eth.account.recover_message(message, signature=_signature)
        sender = w3.toChecksumAddress(json.loads(transaction["data"])["from"])
        if (signer == sender):
            transaction["sig"] = _signature
            self.signed += 1
        return transaction
        
    def verifyTransaction(self, transaction):
        message = encode_defunct(text=transaction["data"])
        _hash = w3.soliditySha3(["string"], [transaction["data"]]).hex()
        _hashInTransaction = transaction["hash"]
        signer = w3.eth.account.recover_message(message, signature=transaction["sig"])
        sender = w3.toChecksumAddress(json.loads(transaction["data"])["from"])
        result = ((signer == sender) and (_hash == _hashInTransaction))
        self.verified += int(result)
        return result

class SiriCoinMiner(object):
    def __init__(self, NodeAddr):
        # self.chain = BeaconChain()
        self.requests = importlib.import_module("requests")        
        self.node = NodeAddr
        self.signer = SignatureManager()        
        self.proof = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.nonce = 0
    
    def refreshBlock(self):
        info = self.requests.get(f"{self.node}/chain/miningInfo").json().get("result")
        self.target = info["target"]
        self.difficulty = info["difficulty"]
        self.lastBlock = info["lastBlockHash"]
        self.timestamp = int(time.time())
    
    def beaconRoot(self, minerID):
        rewardsRecipient = w3.toChecksumAddress(minerID)
        messagesHash = w3.keccak(b"null")
        bRoot = w3.soliditySha3(["bytes32", "uint256", "bytes32","address"], [self.lastBlock, self.timestamp, messagesHash, rewardsRecipient]) # parent PoW hash (bytes32), beacon's timestamp (uint256), hash of messages (bytes32), beacon miner (address)
        return bRoot.hex()

    def startMining(self):        
        with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
            # Activate the server; this will keep running until you
            # interrupt the program with Ctrl-C
            print(f"Started gateway {HOST}:{PORT}")
            server.serve_forever()
        

class MyTCPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        print("{} wrote:".format(self.client_address[0]))
        self.data = str(self.request.recv(1024).strip(), "utf-8")
        print(self.data)
        cmd = self.data.split(',')
        if (cmd[0] == "$REQJOB"):
            print("Send job")
            miner.refreshBlock()
            pacq = miner.beaconRoot(minerAddr) + "," + miner.target + "," + "30\n"
            self.request.sendall(bytes(pacq,'UTF-8'))
        elif (cmd[0] == "$RESULT"):
            try:
                miner.nonce = int(cmd[1].rstrip())
                #tempo_decorrido = round(int(cmd[2].rstrip()) * 0.000001)
                miner.proof = cmd[3].rstrip()
                #miner.submitBlock({"miningData" : {"miner": self.rewardsRecipient,"nonce": self.nonce,"difficulty": self.difficulty,"miningTarget": self.target,"proof": self.proof}, "parent": self.lastBlock,"messages": self.messages.hex(), "timestamp": self.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
            except:
                print(f"invalid data: {self.data}")
            

if __name__ == "__main__":        
    miner = SiriCoinMiner(serverAddr)
    miner.startMining() 
