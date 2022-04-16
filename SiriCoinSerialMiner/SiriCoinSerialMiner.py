# Based https://github.com/Shreyas-ITB/SiriCoinPCMiner
import hashlib, time, importlib, json, serial
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct
from colorama import Fore

#change usb-serial port (baud=115200)
serialPort = "/dev/ttyUSB0"

#change user_id
minerAddr = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"

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
        
        self.timestamp = time.time()
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
        self.timestamp = time.time()
        self.nonce = 0
    
    def submitBlock(self, blockData):
        data = json.dumps({"from": self.acct.address, "to": self.acct.address, "tokens": 0, "parent": self.lastSentTx, "blockData": blockData, "epoch": self.lastBlock, "type": 1})
        tx = {"data": data}
        tx = self.signer.signTransaction(self.priv_key, tx)
        txid = self.requests.get(f"{self.node}/send/rawtransaction/?tx={json.dumps(tx).encode().hex()}").json().get("result")[0]
        print(f"SYS{Fore.GREEN} Mined block {blockData['miningData']['proof']}")
        print(f"Submitted in transaction {txid}")
        return txid

    def beaconRoot(self):        
        messagesHash = w3.keccak(self.messages)        
        bRoot = w3.soliditySha3(["bytes32", "uint256", "bytes32","address"], [self.lastBlock, int(self.timestamp), messagesHash, self.rewardsRecipient]) # parent PoW hash (bytes32), beacon's timestamp (uint256), hash of messages (bytes32), beacon miner (address)
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
        ser  = serial.Serial(f"{serialPort}", baudrate=115200, timeout=2.5)
        print(f"SYS {Fore.GREEN}Started mining for {minerAddr}")
        proof = ""
        self_lastBlock = ""
        while True:
            self.refresh()
            bRoot = self.beaconRoot()
            if (self_lastBlock != self.lastBlock):
                self_lastBlock = self.lastBlock
                print(f"lastBlock: {self_lastBlock}")
            
            #Envia trabalho para trabalhador via porta serial: bRoot e target
            ddata = f"{bRoot},{self.target}\n"            
            ser.write(ddata.encode('ascii'))
            ser.flush()
            
            sucesso = False
            recebido = ""
            tempo_decorrido = 30
            tinicial = time.time()
            while (time.time() - tinicial) < 120:
				#recebe dados via porta serial
                if (ser.in_waiting>0):
                    byte_lido = ser.read()
                    if (byte_lido == b'\n'):						
                        ress = recebido.split(',')
                        self.nonce = int(ress[0])
                        tempo_decorrido = int(ress[1]) * 0.000001
                        proof = ress[2]
                        recebido = ""
                        if (len(proof)>20):
                            sucesso = True
                        print(f"SYS {Fore.YELLOW}Last {round(tempo_decorrido,2)} seconds hashrate : {self.formatHashrate((self.nonce / tempo_decorrido))}")
                        break
                    else:
                        recebido = recebido + byte_lido.decode("utf-8") 
                else:
                    info_ = self.requests.get(f"{self.node}/chain/miningInfo").json().get("result")
                    if (self_lastBlock != info_["lastBlockHash"]):
                        break
                # Envia bloco minerado
                if(sucesso):
                    self.submitBlock({"miningData" : {"miner": self.rewardsRecipient,"nonce": self.nonce,"difficulty": self.difficulty,"miningTarget": self.target,"proof": proof}, "parent": self.lastBlock,"messages": self.messages.hex(), "timestamp": self.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
                    break

if __name__ == "__main__":
    #minerAddr = input("Enter your SiriCoin address : ")    
    miner = SiriCoinMiner("https://siricoin-node-1.dynamic-dns.net:5005/", minerAddr)
    miner.startMining()
