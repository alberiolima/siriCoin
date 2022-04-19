# Based https://github.com/Shreyas-ITB/SiriCoinPCMiner
import hashlib, time, importlib, json, serial
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct
from colorama import Fore

#change usb-serial port (baud=115200)
serialPort = "/dev/ttyUSB0"

#miner id
minerAddr = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"

#time job
tempoTrabalhar = 20

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
        _txs = self.requests.get(f"{self.node}/accounts/accountInfo/{self.acct.address}").json().get("result").get("transactions")
        self.lastSentTx = _txs[len(_txs)-1]
        self.refresh()
    
    def refresh(self):
        info = self.requests.get(f"{self.node}/chain/miningInfo").json().get("result")
        self.target = info["target"]
        self.difficulty = info["difficulty"]
        self.lastBlock = info["lastBlockHash"]
        _txs = self.requests.get(f"{self.node}/accounts/accountInfo/{self.acct.address}").json().get("result").get("transactions")
        self.lastSentTx = _txs[len(_txs)-1]
        self.timestamp = int(time.time())
        self.nonce = 0
    
    def submitBlock(self, blockData):
        data = json.dumps({"from": self.acct.address, "to": self.acct.address, "tokens": 0, "parent": self.lastSentTx, "blockData": blockData, "epoch": self.lastBlock, "type": 1})
        tx = {"data": data}
        tx = self.signer.signTransaction(self.priv_key, tx)        
        self.refresh()
        txid = self.requests.get(f"{self.node}/send/rawtransaction/?tx={json.dumps(tx).encode().hex()}").json().get("result")[0]
        print(f"SYS Mined block {blockData['miningData']['proof']}")
        print(f"Submitted in transaction {txid}")
        return txid

    def beaconRoot(self):        
        messagesHash = w3.keccak(self.messages)        
        bRoot = w3.soliditySha3(["bytes32", "uint256", "bytes32","address"], [self.lastBlock, self.timestamp, messagesHash, self.rewardsRecipient]) # parent PoW hash (bytes32), beacon's timestamp (uint256), hash of messages (bytes32), beacon miner (address)
        return bRoot.hex()

    def formatHashrate(self, hashrate):
        if hashrate < 1000:
            return f"{round(hashrate, 2)}H/s"
        elif hashrate < 1000000:
            return f"{round(hashrate/1000, 2)}kH/s"
        elif hashrate < 1000000000:
            return f"{round(hashrate/1000000, 2)}MH/s"
        elif hashrate < 1000000000000:
            return f"{round(hashrate/1000000000, 2)}GH/s"
            
    def startMining(self):
        print(f"SYS Started mining for {minerAddr}")
        self.refresh()
        ser  = serial.Serial(f"{serialPort}", baudrate=115200, timeout=2.5)        
        proof = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"        
        self_lastBlock = ""
        while True:
            self.refresh()                        
            if (self_lastBlock != self.lastBlock):
                self_lastBlock = self.lastBlock
                print(f"lastBlock  : {self_lastBlock}")
                print(f"target     : {self.target}")
                print(f"difficulty : {self.difficulty}")
            #self.timestamp = 1650303688
            bRoot = self.beaconRoot()                        
            ddata = f"{bRoot},{self.target},{tempoTrabalhar}\n"
            ser.flush()
            ser.write(ddata.encode('ascii'))            
            recebido = ""
            tempo_decorrido = tempoTrabalhar
            tinicial = time.time()
            q_bytes = 0
            self.nonce = 0
            while (time.time() - tinicial) < (tempoTrabalhar * 2):                
                if (ser.in_waiting>0):
                    byte_lido = ser.read()
                    q_bytes = q_bytes + 1
                    if (byte_lido == b'\n'):						
                        ress = recebido.split(',')
                        try:
                            self.nonce = int(ress[0].rstrip())
                            tempo_decorrido = round(int(ress[1].rstrip()) * 0.000001)
                            proof = ress[2].rstrip()
                        except:							
                            print(f"invalid data: {recebido}")
                        recebido = ""
                        print(f"SYS {self.timestamp} Last {round(tempo_decorrido,2)} seconds hashrate : {self.formatHashrate((self.nonce / tempo_decorrido))}")
                        if (q_bytes>32):
                            print(f"bRoot: {bRoot}")
                            self.submitBlock({"miningData" : {"miner": self.rewardsRecipient,"nonce": self.nonce,"difficulty": self.difficulty,"miningTarget": self.target,"proof": proof}, "parent": self.lastBlock,"messages": self.messages.hex(), "timestamp": self.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
                            print("")
                        q_bytes = 0
                        break
                    else:
                        recebido = recebido + byte_lido.decode("utf-8")

if __name__ == "__main__":
    miner = SiriCoinMiner(serverAddr, minerAddr)
    miner.startMining()
