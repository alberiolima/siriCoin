import requests
import json
import time
import sha3
from threading import Thread
from random import randrange

siriAddress = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"
url_pool = "http://168.138.151.204/poolsiri/"

#calculate messagesHash
ctx_keccak = sha3.keccak_256()
ctx_keccak.update(b"null")
messagesHash = ctx_keccak.digest()

def formatHashrate(hashrate):
    if hashrate < 1000:
        return f"{round(hashrate, 2)}H/s"
    elif hashrate < 1000000:
        return f"{round(hashrate/1000, 2)}kH/s"
    elif hashrate < 1000000000:
        return f"{round(hashrate/1000000, 2)}MH/s"
    elif hashrate < 1000000000000:
        return f"{round(hashrate/1000000000, 2)}GH/s"

def mine_pool():    
    print("Starting")
    while True:    
        #login        
        login_data = {'id':'', 'method': 'mining.authorize', 'params': [siriAddress]}
        try:
            login_result = requests.post(url_pool, data=json.dumps(login_data)).json();            
        except:
            print("Thread", threadid, "connection error")
            time.sleep(randrange(thread_count+3))
            continue
        miner_id = login_result['id']    
        
        #print(login_data)
        print("login:", login_result)
        while True:
            #request job
            req_job_data = {"id": miner_id, "method": "mining.subscribe", "params": ["PC"]}
            try:
                req_job_result = requests.post(url_pool, data=json.dumps(req_job_data)).json();
            except:
                break
            #print(req_job_result)
        
            #mount job
            try:
                req_job_params = req_job_result['params']
            except:
                continue    
            job_id = req_job_params[0]
            lastBlock = req_job_params[1]
            int_target = int(req_job_params[2], 16)
            nonce = int(req_job_params[3])
            nonce_final = int(req_job_params[4])
            timestamp = int(req_job_params[7])
            poolSiriAddress = req_job_params[9]
            #print(poolSiriAddress)
            print("Job", job_id, "timestamp:", timestamp, "nonce", nonce, "to", nonce_final )
        
            #calculate bRoot
            ctx_keccak = sha3.keccak_256()
            ctx_keccak.update(bytes.fromhex(lastBlock[2:]))
            ctx_keccak.update(timestamp.to_bytes(32, "big"))
            ctx_keccak.update(messagesHash)
            ctx_keccak.update(bytes.fromhex(poolSiriAddress[2:]))
            bRoot = ctx_keccak.digest()
       
            tmp0 = 0
            ctx_proof = sha3.keccak_256()
            ctx_proof.update(bRoot)
            ctx_proof.update(tmp0.to_bytes(24, "big"))        
        
            #work
            bProof = b"0"
            send_block_mined = False
            start_nonce = nonce        
            start_time = time.time();            
            while nonce < nonce_final:
                #teste1
                ctx_proof2 = ctx_proof.copy()
                ctx_proof2.update(nonce.to_bytes(8, "big"))
                bProof = ctx_proof2.digest()
                if (int.from_bytes(bProof, "big") < int_target):
                    send_block_mined = True                    
                    break
                nonce += 1
                
                #teste2
                ctx_proof2 = ctx_proof.copy()
                ctx_proof2.update(nonce_final.to_bytes(8, "big"))
                bProof = ctx_proof2.digest()
                if (int.from_bytes(bProof, "big") < int_target):
                    nonce = nonce_final
                    send_block_mined = True                    
                    break
                nonce_final -= 1
            
            #send mined block 
            if (send_block_mined):
                proof = "0x" + bProof.hex()
                print("mined proof:", proof, "nonce: ", nonce )
                submit_data = {"id":miner_id,"method":"mining.submit","params":[siriAddress,job_id,proof,timestamp,nonce]}
                submit_result = requests.post(url_pool, data=json.dumps(submit_data)).json();
                print(submit_result);
            
            calculations = (nonce - start_nonce) * 2
            elapsed_time_s = time.time() - start_time
            hr = calculations / elapsed_time_s
            print("Hashrate:", formatHashrate(hr), "Time (secs):", round(elapsed_time_s,3), "calculations:", calculations )

if __name__ == "__main__":
    print("pool        :", siriAddress)
    mine_pool()
