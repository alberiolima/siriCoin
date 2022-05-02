# Based https://github.com/Shreyas-ITB/SiriCoinPCMiner
import hashlib, time, importlib, json, serial
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct
from colorama import Fore
from threading import Thread
import os.path 
import configparser

configMinerName = 'config.ini'
configMiner = configparser.ConfigParser()

#change usb-serial port (baud=115200)
serialPorts = ""

#miner id
minerAddr = ""

#time job
tempoTrabalhar = 20

#server
serverAddr = "http://138.197.181.206:5005/" 
#serverAddr = "https://siricoin-node-1.dynamic-dns.net:5005/"

self_lastBlock = ""

def readConfigMiner():
    global minerAddr,serialPorts,tempoTrabalhar
    configMiner['DEFAULT'] = {'miner_addr': '', 'serial_ports': '','time_work': 20 }
    if (os.path.exists(configMinerName) is False):
        writeConfigMiner()    
    try:        
        configMiner.read(configMinerName)
        def_config = configMiner["DEFAULT"]
        minerAddr = def_config["miner_addr"]
        serialPorts = def_config["serial_ports"]
        tempoTrabalhar = int(def_config["time_work"])
    except:
        print("error read config file") 

def writeConfigMiner():
    global minerAddr,serialPorts
    global tempoTrabalhar
    def_config = configMiner["DEFAULT"]
    def_config["miner_addr"] = minerAddr
    def_config["serial_ports"] = serialPorts
    def_config["time_work"] = str(tempoTrabalhar)
    try:
        with open(configMinerName, 'w') as configfile:
            configMiner.write(configfile)
    except:
        print("error write config file") 
    
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
        print(f"{Fore.GREEN}Mined block {blockData['miningData']['proof']}")
        print(f"{Fore.GREEN}Submitted in transaction {txid}")
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

    def startMining(self, indexThread, serial_port):        
        global self_lastBlock
        while True:
            while True:
                print(f"{Fore.WHITE}T{indexThread} {Fore.YELLOW}connecting to {Fore.WHITE}{serial_port}")
                try:
                    ser = serial.Serial(f"{serial_port}", baudrate=115200, timeout=2.5)
                    break
                except:
                    print(f"Error connecting {serial_port}")
                time.sleep(2)
            self.refresh()
            proof = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"        
            self_lastBlock = self.lastBlock
            while True:
                self.refresh()
                if (self_lastBlock != self.lastBlock):
                    self_lastBlock = self.lastBlock
                    print(f"{Fore.RED}New block")
                bRoot = self.beaconRoot()
                print(f"{Fore.WHITE}T{indexThread} {Fore.YELLOW}send job")
                ddata = f"{bRoot},{self.target},{tempoTrabalhar}\n"
                port_is_ok = False
                try:
                    ser_in_waiting = ser.in_waiting
                    port_is_ok = True
                except:
                    print(f"Error reading {serial_port}")
                    ser.close()
                    break
                ser.flush()
                ser.write(ddata.encode('ascii'))
                recebido = ""
                tempo_decorrido = tempoTrabalhar
                q_bytes = 0
                self.nonce = 0
                tinicial = time.time()
                while (time.time() - tinicial) < (tempoTrabalhar * 2):
                    ser_in_waiting = 0
                    try:
                        ser_in_waiting = ser.in_waiting
                    except:
                        ser.close()
                        break
                    if (ser_in_waiting>0):
                        byte_lido = ser.read()
                        q_bytes = q_bytes + 1
                        if (byte_lido == b'\n'):
                            ress = recebido.split(',')
                            try:
                                self.nonce = int(ress[0].rstrip())
                                tempo_decorrido = round(int(ress[1].rstrip()) * 0.000001)
                                proof = ress[2].rstrip()
                            except:
                                print(f"{Fore.YELLOW}Invalid data: {recebido}")
                            recebido = ""
                            print(f"{Fore.WHITE}T{indexThread} {Fore.YELLOW}Last {round(tempo_decorrido,2)} seconds hashrate : {self.formatHashrate((self.nonce / tempo_decorrido))}")
                            if (q_bytes>32):
                                self.submitBlock({"miningData" : {"miner": self.rewardsRecipient,"nonce": self.nonce,"difficulty": self.difficulty,"miningTarget": self.target,"proof": proof}, "parent": self.lastBlock,"messages": self.messages.hex(), "timestamp": self.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
                            q_bytes = 0
                            break
                        else:
                            recebido = recebido + byte_lido.decode("utf-8")

if __name__ == "__main__":
	
	#Read config
    readConfigMiner()
    
    print(f"{Fore.YELLOW}Server: {Fore.WHITE}{serverAddr}")
    
    #Get SiriCoin address
    if ( minerAddr == "" ):
        minerAddr = input(f"{Fore.YELLOW}Enter SiriCoin address: {Fore.WHITE}")
    else:
        print(f"{Fore.YELLOW}SiriCoin address:{Fore.WHITE}", minerAddr )
        t_minerAddr = input(f"{Fore.YELLOW}Enter new SiriCoin address or ENTER to continue: {Fore.WHITE}")
        if (t_minerAddr != ""):
            minerAddr = t_minerAddr
    
    #Get list of serial ports
    if ( serialPorts == "" ):
        serialPorts = input(f"{Fore.YELLOW}Enter list serial ports: {Fore.WHITE}")
    else:
        print(f"{Fore.YELLOW}List serial ports:{Fore.WHITE}", serialPorts )
        t_serialPorts = input(f"{Fore.YELLOW}Enter new list serial ports or ENTER to continue: {Fore.WHITE}")
        if (t_serialPorts != ""):
            serialPorts = t_serialPorts
    
    #Write config
    writeConfigMiner()
    
    listPorts = serialPorts.split(',')
    real_ports = list()
    for port in listPorts:
        if os.path.exists(port):
            real_ports.append(port)
            print(f"{Fore.YELLOW}{port}", f"{Fore.WHITE}[ok]")
        else:
            print(f"{Fore.YELLOW}{port}", f"{Fore.WHITE}[invalid]")    
   
    print(f"{Fore.YELLOW}...")
    print(f"{Fore.YELLOW}Started mining")
    
    #Threads
    index = 0
    for port in real_ports:
        miner = SiriCoinMiner(serverAddr, minerAddr)
        Thread(target=miner.startMining, args=(index, port)).start()
        index += 1
