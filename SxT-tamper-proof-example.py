import requests
import sys
import logging
from dotenv import dotenv_values
from nacl.signing import SigningKey
from pyarrow.ipc import RecordBatchStreamReader
import base64
from biscuit_auth import BiscuitBuilder, KeyPair, PrivateKey, PublicKey, Rule
import random
import string
import time

logging.basicConfig(level=logging.INFO)


def main():
    # 1) Authenticate with SxT API
    access_token = authenticate()
    # 2) Create a biscuit 
    biscuit = generate_biscuit()
    # 3) Create a tamperproof table
    create_tamperproof_table(biscuit, access_token)
    # 4) Insert data into the tamperproof table
    insert_data(biscuit, access_token)
    # 5) Query the tamperproof table
    query_tamperproof_table(biscuit, access_token)

def create_tamperproof_table(biscuit, access_token):
    # https://docs.spaceandtime.io/reference/configure-resources-ddl
    # Note that we use the same DDL endpoint for creating tamper proof tables as we do for regular tables

    url = conf['api_url'] + "sql/ddl"

    sqlText = f"CREATE TABLE {biscuit['resource_id']} (PROOF_ORDER BIGINT PRIMARY KEY, PLANET VARCHAR) WITH \
        \"public_key={biscuit['public_key']},access_type=public_read,tamperproof=true,immutable=true,persist_interval=10\""
    
    # needed for prod env    
    biscuit_token = [biscuit['token']]

    payload = {
        "sqlText": sqlText,
        "biscuits": biscuit_token
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}", 
        "biscuit": biscuit['token'] # needed for staging env. idk why.  
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status() 
    except requests.exceptions.RequestException as e:
        # if we don't get valid json response from the API
        logging.error(f"Table creation: {resp.status_code}\nSxT API Response text: {resp.text}")
        sys.exit()
        
    logging.info(f"Table {biscuit['resource_id']} created successfully with API response code : {resp.status_code}")
    return True

# Insert data into a tamperproof table
def insert_data(biscuit, access_token):
    # https://docs.spaceandtime.io/reference/modify-data-dml
    url = conf['api_url'] + "sql/dml"
    planet = random_planet()    
    # manual auto increment - We could get MAX PROOF_ORDER +1 via SxT query instead of hardcoding 0 here

    # add a row to the tamperproof table
    sqlText = f"INSERT INTO {biscuit['resource_id']} (PROOF_ORDER, PLANET) VALUES (0, '{planet}');"

    payload = {
        "resources": [biscuit['resource_id']],
        "sqlText": sqlText,
        "biscuits": [biscuit['token']]
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status() 
        logging.info(f"Inserted data '0', {planet} into tamper proof table successfully with response code : {resp.status_code} - Please wait 10 seconds for the data to be persisted...")
        _ = [time.sleep(1) for _ in range(11)] # wait 10 seconds for the data to be persisted
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Insert data failed with : {resp.status_code} and error : {resp.text}")
        sys.exit()

# Query a tamperproof table
def query_tamperproof_table(biscuit, access_token):

    url = conf['api_url'] + conf['tamperproof_url']
    sqlText = f"SELECT * FROM {biscuit['resource_id']}"

    payload = {
        "resourceId": biscuit['resource_id'],
        "sqlText": sqlText,
        "biscuits": [biscuit['token']]
    }
    headers = {
        "accept": "application/octet-stream",
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}",
      }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status() 
        logging.info(f"Query tamperproof table successfully with code : {resp.status_code}")
        logging.info(f"SxT query response data: {deserialize_batch(resp.content)}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Query tamperproof table failed with : {resp.status_code} and error : {resp.text}")
        sys.exit()
    
# process Arrow IPC binary response
def deserialize_batch(serialized_batch):
    """Converts the serialized record batch `serialized` (byte array) to a Record Batch"""
    deserializer = RecordBatchStreamReader(serialized_batch)
    return deserializer.read_all()

# Get envars from .env file, validate
def get_config(config):
    conf = {}

    try:
        conf['schema'] = sys.argv[1]
    except:
        logging.debug('No schema provided, so we will default to SE_PLAYGROUND')
        conf['schema'] = 'se_playground'

    """ If needed we could add support for existing biscuit auth here
    try: 
        conf['biscuit'] = config['BISCUIT']
    except:
        logging.error('A biscuit token is required to create a table with this script. Please set BISCUIT in .env')
        sys.exit()
    try: 
        conf['biscuit_public_key'] = config['BISCUIT_PUBLIC_KEY']
    except:
        logging.error('A biscuit public key is required to create a table with this script. Please set BISCUIT_PUB_KEY in .env')
        sys.exit()
    """

    try: 
        conf['api_url'] = config['API_URL']
    except:
        logging.error('Please make sure you set the SxT API_URL value in your .env file!')
        sys.exit() 

    try: 
        conf['tamperproof_url'] = config['TAMPERPROOF_URL']
    except:
        logging.error('Please make sure you set the SxT TAMPERPROOF_URL value in your .env file!')
        sys.exit()

    try:
        conf['user_id'] = config['USER_ID']
    except:
        logging.error('Please make sure you set the SxT USER_ID value in your .env file!')
        sys.exit()

    try:
        conf['user_private_key'] = config['USER_PRIVATE_KEY']
    except:
        logging.error('Please make sure you set the SxT USER_PRIVATE_KEY value in your .env file!')
        sys.exit()

    try:
        conf['user_public_key'] = config['USER_PUBLIC_KEY']
    except:
        logging.error('Please make sure you set the SxT USER_PUBLIC_KEY value in your .env file!')
        sys.exit()  
    
    try: 
        conf['AUTH_SCHEME'] = config['AUTH_SCHEME']
    except:
        logging.debug('AUTH_SCHEME not set in .env so we will default to ED25519') 
        conf['AUTH_SCHEME'] = 'ed25519'
    return conf


# https://docs.spaceandtime.io/reference/token-request
def request_token(auth_code, signed_auth_code):
    headers = {"accept": "application/json"}
    url = conf['api_url'] + "auth/token"
    payload = {
        "userId": conf['user_id'],
        "authCode": auth_code,
        "signature": signed_auth_code,
        "key": conf['user_public_key'],
        "scheme": conf['AUTH_SCHEME']
    }

    resp = requests.post(url, json=payload, headers=headers)
    
    if resp.status_code != 200:
        logging.error('Failed to request token from the API!')
        logging.error(resp.status_code, resp.text)
        sys.exit()
    
    jsonResp = resp.json()
    logging.debug(f'auth/token response: {jsonResp}')

    return jsonResp["accessToken"],jsonResp["refreshToken"]

def sign_message(auth_code):
    # get bytes of the auth code for signing  
    bytes_message = bytes(auth_code, 'utf-8')
    # decode private key for signing 
    key = base64.b64decode(conf['user_private_key'])
    # create signing key
    signingkey = SigningKey(key)
    # finally, sign the auth code with our private key
    signed_message = signingkey.sign(bytes_message)

    logging.debug("Signature | hashed message, hex: " + signed_message.hex())
    logging.debug("Signature, hex: " + signed_message[:64].hex())

    return signed_message[:64].hex()


# https://docs.spaceandtime.io/reference/authentication-code
def request_auth_code():
    
    headers = {"accept": "application/json"}
    url = conf['api_url'] + "auth/code"
    
    payload = {
        "userId": conf['user_id'],
    }

    resp = requests.post(url, json=payload, headers=headers)
   
    jsonResponse = resp.json()
    logging.debug(f'auth/code response: {jsonResponse}')

    if resp.status_code == 200: 
        auth_code = jsonResponse["authCode"]
    else: 
        print('Non 200 response from the auth/code endpoint! Stopping.')
        sys.exit()

    return auth_code 


# https://docs.spaceandtime.io/reference/authentication-code
def authenticate():
    # 1) Request auth code from SxT API 
    auth_code = request_auth_code()

    # 2) Sign the auth code with our private key
    signed_auth_code = sign_message(auth_code)
    
    # 3) Request access token using signed_auth_code 
    access_token, refresh_token = request_token(auth_code, signed_auth_code)
    
    logging.debug(f'Authenticaiton to the SxT API has been completed successfully!\n Access token: {access_token}\n Refresh token: {refresh_token}')
    
    return access_token

def random_planet():
    # List of planets' names
    planets = ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune']

    # Randomly pick a planet name
    return random.choice(planets)

def load_env():
    try:
        config = dotenv_values(".env")
    except:
        logging.error('Please make sure you have a .env file in the same directory as this script!')
        sys.exit() 
    return config

def generate_biscuit():
    keypair = KeyPair()
    private_key_str = keypair.private_key.to_hex()
    public_key_str = keypair.public_key.to_hex()
    generate_random_word = lambda: ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 11)))
    random_word = generate_random_word()
    resourceId = f"{conf['schema']}.{random_word}"

    builder = BiscuitBuilder("""
        sxt:capability("ddl_create", {resourceId});
        sxt:capability("ddl_drop", {resourceId});
        sxt:capability("dml_insert", {resourceId});
        sxt:capability("dml_update", {resourceId});
        sxt:capability("dml_merge", {resourceId});
        sxt:capability("dml_delete", {resourceId});
        sxt:capability("dql_select", {resourceId});
    """,
    {
        'resourceId': resourceId
    }
    )
    token = builder.build(keypair.private_key)
    token_string = token.to_base64()
    
    logging.info(f"Biscuit private Key: {private_key_str}")
    logging.info(f"Biscuit public Key: {public_key_str}")
    logging.info(f"Resource ID: {resourceId}")    
    logging.info(f"Biscuit: {token_string}")
    
    biscuit = {
        "private_key": private_key_str,
        "public_key": public_key_str,
        "resource_id": resourceId,
        "token": token_string
    }
    return biscuit

if __name__ == "__main__":
    # Load envars from .env file, validate
    conf = get_config(load_env())
    main()



