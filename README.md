Using Proof of SQL (PoSQL) to run tamperproof queries with Space and Time follows a similar workflow to the standard process of executing against Space and Time. However, there are a couple of key differences that it's essential to be aware of. The following guide will walk you through the end-to-end process of creating a table, inserting data, and running tamperproof queries against your data. 

This guide assumes you have a Space and Time account and an understanding of basic concepts like logging in and running queries. If you're new to Space and Time, we recommend starting with our standard [Getting started](doc:getting-started) guide. 

> 📘 
> 
> With the initial release, tamperproof queries are not supported through the SxT CLI or JDBC.

Rather than walk through all steps of creating a table, inserting data, and querying the data, first, we will look at the specific steps unique to tamperproof queries. After that, we'll go through the end-to-end steps for running a sxt-tamper-proof-example.py script. 

## Tamperproof query basics

The end-to-end workflow involves the following steps: 

1. Authenticate with SxT API
2. Create a biscuit 
3. Create a tamperproof table
4. Insert data into a tamperproof table
5. Query the tamperproof table

Authentication and biscuit creation are the same, so we don't need to address those. 

### Create a tamperproof table

Let us take a look at the SQL used to create a tamperproof table:

```sql
CREATE TABLE <resource_id> (PROOF_ORDER BIGINT PRIMARY KEY, PLANET VARCHAR) WITH 
        "public_key=<biscuit_public_key>,access_type=public_read,tamperproof=true,immutable=true,persist_interval=10
```

**Please note that the `PROOF_ORDER` column is required with this initial release.** The PLANET column is just an example and is not required.   

`resource_id` will be for the schema.table that you're creating, and `biscuit_public_key` will be your biscuit public key. 

You've probably seen `access_type` before, but the next three WITH flags are likely new. 

- `tamperproof=true` - As you might expect, this tells SxT that you want to create a tamperproof table. 
- `immutable=true` - Immutable is also required for tamperproof tables. 
- `persist_interval=10` - While optional, this flag tells SxT to flush the data to ignite in 10 seconds. 

That's all you need on the CREATE side!

### Insert data into a tamperproof table

```sql
INSERT INTO <resource_id> (PROOF_ORDER, PLANET) VALUES (0,'EARTH')
```

The `PROOF_ORDER` column needs to be strictly increased. For now, this needs to be done manually, but in the future, `auto-increment` will handle this in the background for you. 

### Query tamperproof table

```sql
SELECT * FROM <resource_id>
```

**This SQL for a basic tamperproof query is identical, however, not all SQL is supported for tamper-proof queries at this time.** Also, there is a new tamperproof query endpoint and some notable differences in the header, payload, and response data that we need to look at. 

1. New API endpoint - This URL will be provided to you by the SxT team.  
2. In the headers, take note of the deviation from the standard JSON accept to: `"accept": "application/octet-stream",`  
3. In the payload, please note that we use `resourceId` for the resource id. This differs from other API endpoints. 
4. Response data - The tamperproof query endpoint returns query response data in Arrow IPC format. Therefore, we'll need to process the response data to deserialize it from binary and make it human-readable. You can find parsing libraries for various languages [here](https://arrow.apache.org/docs/status.html#ipc-format). 

## SxT-tamper-proof-example.py

This script goes through a full end-to-end demonstration of: 

1. Authenticating 
2. Creating a biscuit 
3. Creating a tamperproof table
4. Inserting data into a tamperproof table 
5. Querying a tamperproof table 

For the sake of simplicity, this script will create a new biscuit and random table for you under the `se_playground` schema. Optionally, you can use your schema by providing it as a command line arg to the script like this: `python SxT-tamper-proof-example.py <your-schema-here>`

### Setup and requirements

1. Download the repo  
   `git clone https://github.com/SxT-Community/tamper-proof-example.git`

2. Set up your Python virtual environment. 

It doesn't matter how you do this. This repo uses the virtualenv plugin for pyenv. You can create your environment with the virtualenv plugin like this:  
`pyenv virtualenv 3.11.2 POFSQL-3.11.2`

Now it will pick up the `.python-version` file from the repo and automatically activate this env when you are in this directory. 

3. Setup your env

`cp sample.env .env`

>  :warning: Make sure to use a SxT account with a valid subscription so that you have the needed permissions to create a table. 

Add your username and pub/priv key pair used for auth. 

4. Run it! 

`python SxT-tamper-proof-example.py`

The output will look like this:

```Text terminal
INFO:root:Biscuit private Key: c30f6...
INFO:root:Biscuit public Key: 63a0c...
INFO:root:Resource ID: se_playground.zcrcbuml
INFO:root:Biscuit: Et0CCvIBCg5zeHQ6Y2FwYWJp...==
INFO:root:Table se_playground.zcrcbuml created successfully with API response code : 200
INFO:root:Inserted data '0', Mercury into tamper proof table successfully with response code : 200 - Please wait 10 seconds for the data to be persisted...
INFO:root:Query tamperproof table successfully with code : 200
INFO:root:SxT query response data: pyarrow.Table
proof_order: int64 not null
planet: string not null
----
proof_order: [[0]]
planet: [["Mercury"]]
```