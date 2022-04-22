#### TEST VERSION
#### TEST VERSION
#### TEST VERSION
import socket
import threading
import time, importlib, json
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct
from colorama import Fore #Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
from random import randrange

# Create the server, binding to localhost on port 9999
#HOST, PORT = "localhost", 9999
HOST, PORT = "192.168.1.36", 9999

#time job
tempoTrabalhar = 30

#miner id (temporary)
minerAddr = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"

#server
serverAddr = "https://siricoin-node-1.dynamic-dns.net:5005/"
#serverAddr = "http://138.197.181.206:5005/" 

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
    def __init__(self, NodeAddr, RewardsRecipient):
        # self.chain = BeaconChain()
        self.requests = importlib.import_module("requests")
        
        self.node = NodeAddr
        self.signer = SignatureManager()
        self.difficulty = 1
        self.target = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.lastBlock = ""
        self.rewardsRecipient = w3.toChecksumAddress(RewardsRecipient)
        self.priv_key = w3.solidityKeccak(["string", "address"], ["SiriCoin Will go to MOON - Just a disposable key", self.rewardsRecipient])

        self.nonce = 0
        self.acct = w3.eth.account.from_key(self.priv_key)
        self.messages = b"null"
        
        self.timestamp = int(time.time())
        url_req = self.node+"/accounts/accountInfo/"+self.acct.address
        _txs = self.requests.get(url_req).json().get("result").get("transactions")
        self.lastSentTx = _txs[len(_txs)-1]
        self.refresh()
    
    def refresh(self):
        url_req = self.node+"/chain/miningInfo"
        info = self.requests.get(url_req).json().get("result")
        self.target = info["target"]
        self.difficulty = info["difficulty"]
        self.lastBlock = info["lastBlockHash"]
        url_req = self.node+"/accounts/accountInfo/"+self.acct.address
        _txs = self.requests.get(url_req).json().get("result").get("transactions")
        self.lastSentTx = _txs[len(_txs)-1]
        self.timestamp = int(time.time())
        self.nonce = 0
        
    def submitBlock(self, blockData):
        data = json.dumps({"from": self.acct.address, "to": self.acct.address, "tokens": 0, "parent": self.lastSentTx, "blockData": blockData, "epoch": self.lastBlock, "type": 1})
        tx = self.signer.signTransaction(self.priv_key, {"data": data})
        url_req = self.node + "/send/rawtransaction/?tx=" + json.dumps(tx).encode().hex()
        resp_req = self.requests.get(url_req)
        txid = ""
        if (resp_req.status_code != 500 ):
            txid = resp_req.json().get("result")[0]
        else:
            print("<tx>")
            print(json.dumps(tx).encode().hex())
            print("</tx>")
        print(Fore.WHITE,"SYS Mined block ",blockData['miningData']['proof'])
        print(Fore.WHITE,"Submitted in transaction ",txid)
        return txid
    
    def beaconRoot(self):
        messagesHash = w3.keccak(b"null")
        bRoot = w3.soliditySha3(["bytes32", "uint256", "bytes32","address"], [self.lastBlock, self.timestamp, messagesHash, self.rewardsRecipient]) # parent PoW hash (bytes32), beacon's timestamp (uint256), hash of messages (bytes32), beacon miner (address)
        return bRoot.hex()
    
    def formatHashrate(self, hashrate):
        if hashrate < 1000:
            return str(round(hashrate, 2))+"H/s"
        elif hashrate < 1000000:
            return str(round(hashrate/1000, 2))+"kH/s"
        elif hashrate < 1000000000:
            return str(round(hashrate/1000000, 2))+"MH/s"
        elif hashrate < 1000000000000:
            return str(round(hashrate/1000000000, 2))+"GH/s"    

def handle_client(conn, address):
    print(Fore.GREEN,"Connected to {}".format(address[0]))
    tempo_decorrido = 30
    connTemp = time.time()
    minerID = minerAddr
    miner = SiriCoinMiner(serverAddr,minerID)
    proof = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    while (time.time() - connTemp < (tempoTrabalhar * 2)):
        try:
          data = str(conn.recv(300).strip(), "utf-8")        
        except:
          data = ""
        if (len(data) > 0):
            connTemp = time.time()
            data = data.splitlines()[0]
            #print("{} wrote: ".format(address[0])+data)            
            cmd = data.split(',')
            if (cmd[0] == "$REQJOB"):
                if ( cmd[1] != minerID ):                    
                    if ( len(cmd[1]) > 10 ):
                        print("Miner id: ",cmd[1])
                        minerID = cmd[1]
                        miner = SiriCoinMiner(serverAddr,minerID)
                miner.refresh()
                miner.timestamp = miner.timestamp + randrange(-10,10)
                print(Fore.YELLOW,"Send job",miner.timestamp,"to {}".format(address[0]))
                pacq = miner.beaconRoot() + "," + miner.target + "," + str(tempoTrabalhar + randrange(-10,10)) + "\n"
                conn.sendall(bytes(pacq,"utf-8"))
            elif (cmd[0] == "$RESULT"):				
                print(Fore.YELLOW,"Recv result from {} ".format(address[0]) + data )
                try:
                    miner.nonce = int(cmd[1])
                    tempo_decorrido = round(int(cmd[2]) * 0.000001)
                    proof = cmd[3]
                    #print(f"Last {round(tempo_decorrido,2)} seconds hashrate : {miner.formatHashrate((miner.nonce / tempo_decorrido))}")                    
                except:
                    print("Invalid data:",data)
                if (len(proof) > 30):
                    print("prof:", proof)
                    print("miner.nonce:", miner.nonce)
                    miner.submitBlock({"miningData" : {"miner": miner.rewardsRecipient,"nonce": miner.nonce,"difficulty": miner.difficulty,"miningTarget": miner.target,"proof": proof}, "parent": miner.lastBlock,"messages": miner.messages.hex(), "timestamp": miner.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
    print("{} closed".format(address[0]))
    try:
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
    except:
        print("close except")
      

def server():
    print("Starting server...")
    print(serverAddr)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    while True:
        (conn, address) = s.accept()
        t = threading.Thread(target=handle_client, args=(conn, address))
        t.daemon = True
        t.start() 

if __name__ == '__main__':
    try:
        server()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
