#Based on original SiriCoinPCMiner
import time, importlib, json, sha3
from web3.auto import w3
from eth_account.account import Account
from eth_account.messages import encode_defunct
from colorama import Fore
import platform
from random import randrange
import os.path 
import configparser

configMinerName = 'config.ini'
configMiner = configparser.ConfigParser()

#miner id
minerAddr = ""           

#time job
tempoTrabalhar = 20

#temperature control
maxTemperature = 90

NodeAddr = "https://node-1.siricoin.tech:5006/"

def readConfigMiner():
    global minerAddr,serialPorts,tempoTrabalhar
    configMiner['DEFAULT'] = {'miner_addr': '', 'time_work': 20 }
    if (os.path.exists(configMinerName) is False):
        writeConfigMiner()    
    try:        
        configMiner.read(configMinerName)
        def_config = configMiner["DEFAULT"]
        minerAddr = def_config["miner_addr"]
        tempoTrabalhar = int(def_config["time_work"])
    except:
        print("error read config file") 

def writeConfigMiner():
    global minerAddr,serialPorts
    global tempoTrabalhar
    def_config = configMiner["DEFAULT"]
    def_config["miner_addr"] = minerAddr
    def_config["time_work"] = str(tempoTrabalhar)
    try:
        with open(configMinerName, 'w') as configfile:
            configMiner.write(configfile)
    except:
        print("error write config file") 

def get_cpu_temp():
    try:
        tempFile = open("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = tempFile.read()
        tempFile.close()
    except:
        cpu_temp = 0
    return float(cpu_temp) / 1000 

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
    def __init__(self, RewardsRecipient):
        self.requests = importlib.import_module("requests")
        self.signer = SignatureManager()

        self.difficulty = 1
        self.target = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.lastBlock = ""
        self.rewardsRecipient = w3.toChecksumAddress(RewardsRecipient)
        self.priv_key = w3.solidityKeccak(["string", "address"], ["SiriCoin Will go to MOON - Just a disposable key", self.rewardsRecipient])

        self.timestamp = 0
        self.nonce = 0
        self.acct = w3.eth.account.from_key(self.priv_key)
        self.messages = b"null"

        self.lastSentTx = ""
        self.balance = 0

        self.send_url = NodeAddr + "send/rawtransaction/?tx="
        self.block_url = NodeAddr + "chain/miningInfo"        
        self.accountInfo_url = NodeAddr + "accounts/accountInfo/" + RewardsRecipient
        self.balance_url = NodeAddr + "accounts/accountBalance/" + RewardsRecipient
        self.refreshBlock()
        self.refreshAccountInfo()
               
    def refreshBlock(self):
        try:
            info = self.requests.get(self.block_url).json().get("result")
            self.target = info["target"]
            self.difficulty = info["difficulty"]
            self.lastBlock = info["lastBlockHash"]            
        except:
            print("refreshBlock: error")
        self.timestamp = int(time.time())

    def refreshAccountInfo(self):
        try:
            temp_txs = self.requests.get(self.accountInfo_url).json().get("result")
            _txs = temp_txs.get("transactions")
            self.lastSentTx = _txs[len(_txs)-1]
            self.balance = temp_txs.get("balance")
        except:
            print("refreshAccountInfo: error")

    def submitBlock(self, blockData):
        txid = "None"
        self.refreshAccountInfo()
        data = json.dumps({"from": self.acct.address, "to": self.acct.address, "tokens": 0, "parent": self.lastSentTx, "blockData": blockData, "epoch": self.lastBlock, "type": 1})
        tx = {"data": data}
        tx = self.signer.signTransaction(self.priv_key, tx)
        tmp_get = self.requests.get(f"{self.send_url}{json.dumps(tx).encode().hex()}")
        if (tmp_get.status_code != 500 ):
            txid = tmp_get.json().get("result")[0]
        print(f"{Fore.GREEN}TimeStamp: {self.timestamp}, Nonce: {self.nonce}")
        print(f"Mined block {blockData['miningData']['proof']}")
        print(f"Submitted in transaction {txid}")
        return txid

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
        print(f"{Fore.GREEN}Balance: ", self.balance)
        proof = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self_lastBlock = ""
        int_target = 0
        print(f"{Fore.WHITE}Started mining")        
        while True:
            #Temperature check
            tempe = get_cpu_temp() 
            if (tempe > maxTemperature):
                while (tempe > maxTemperature):
                    print(f"{Fore.RED}Temperature : {tempe}, paused")
                    time.sleep(10)
                    tempe = get_cpu_temp()
                print(f"{Fore.YELLOW}Temperature : {tempe}, resumed")
            
            #mining
            self.refreshBlock()
            if (self.lastBlock == "" ):
                time.sleep(10)
                continue
            if (self_lastBlock != self.lastBlock):
                self_lastBlock = self.lastBlock
                int_target = int(self.target, 16)
                print("")
                print(f"{Fore.YELLOW}lastBlock   : {self_lastBlock}")
                print(f"{Fore.YELLOW}target      : {self.target}")
                print(f"{Fore.YELLOW}difficulty  : {self.difficulty}")
            messagesHash = w3.keccak(self.messages)
            bRoot = w3.soliditySha3(["bytes32", "uint256", "bytes32","address"], [self.lastBlock, self.timestamp, messagesHash, self.rewardsRecipient])
            try:
                self.nonce = randrange(int(self.difficulty/2))
            except:
                pass
            second_nonce = 0
            send_block_mined = False
            tmp0 = 0
            ctx_proof = sha3.keccak_256()
            ctx_proof.update(bRoot)
            ctx_proof.update(tmp0.to_bytes(24, "big"))
            t0 = time.time()
            t1 = t0 + tempoTrabalhar
            while (time.time() < t1):
                tp = time.time() + 5
                while (time.time() < tp):                    
                    
                    #try 1
                    self.nonce += 1
                    ctx_proof2 = ctx_proof.copy()
                    ctx_proof2.update(self.nonce.to_bytes(8, "big"))
                    bProof = ctx_proof2.digest()
                    if (int.from_bytes(bProof, "big") < int_target):
                        send_block_mined = True
                        break                    
                    
                    #try 2
                    second_nonce += 1
                    ctx_proof2 = ctx_proof.copy()
                    ctx_proof2.update(second_nonce.to_bytes(8, "big"))
                    bProof = ctx_proof2.digest()
                    if (int.from_bytes(bProof, "big") < int_target):
                        self.nonce = second_nonce
                        send_block_mined = True
                        break
                    
                    #try 3
                    self.nonce += 1
                    ctx_proof2 = ctx_proof.copy()
                    ctx_proof2.update(self.nonce.to_bytes(8, "big"))
                    bProof = ctx_proof2.digest()
                    if (int.from_bytes(bProof, "big") < int_target):
                        send_block_mined = True
                        break                    
                    
                    #try 4
                    second_nonce += 1
                    ctx_proof2 = ctx_proof.copy()
                    ctx_proof2.update(second_nonce.to_bytes(8, "big"))
                    bProof = ctx_proof2.digest()
                    if (int.from_bytes(bProof, "big") < int_target):
                        self.nonce = second_nonce
                        send_block_mined = True
                        break

                print(f"{Fore.YELLOW}Hashrate : {self.formatHashrate(((second_nonce*2) / (time.time() - t0)))} Last {round(time.time() - t0,2)} seconds")
                if send_block_mined is True:
                    proof = "0x" + bProof.hex()
                    self.submitBlock({"miningData" : {"miner": self.rewardsRecipient,"nonce": self.nonce,"difficulty": self.difficulty,"miningTarget": self.target,"proof": proof}, "parent": self.lastBlock,"messages": self.messages.hex(), "timestamp": self.timestamp, "son": "0000000000000000000000000000000000000000000000000000000000000000"})
                    t1 = 0

if __name__ == "__main__":
    #Read config
    readConfigMiner()

    print(f"{Fore.WHITE}SiriCoinPCMiner")
    print(f"{Fore.WHITE}Platform    :", platform.system())
    print(f"{Fore.WHITE}Temperature :", get_cpu_temp())
    print(f"{Fore.WHITE}Server      :", NodeAddr)
    
    #Get SiriCoin address
    if ( minerAddr == "" ):
        minerAddr = input(f"{Fore.YELLOW}Enter SiriCoin address: {Fore.WHITE}")
    else:
        print(f"{Fore.YELLOW}SiriCoin address:{Fore.WHITE}", minerAddr )
        t_minerAddr = input(f"{Fore.YELLOW}Enter new SiriCoin address or ENTER to continue: {Fore.WHITE}")
        if (t_minerAddr != ""):
            minerAddr = t_minerAddr
    
    #Write config
    writeConfigMiner()
    
    miner = SiriCoinMiner(minerAddr)
    miner.startMining()