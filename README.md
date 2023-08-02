# Getting Started with Tamperproof Queries

Using Proof of SQL (PoSQL) to run tamper-proof queries with Space and Time follows a very similar workflow to the standard process of executing against Space and Time. However, there are a couple of key differences that it's important to be aware of. The following guide will walk you through the end-to-end process of creating a table, inserting data, and running tamper-proof queries against your data. 

This guide assumes you have a Space and Time account and an understanding of basic concepts like logging in and running queries. If you're new to Space and Time, we recommend that you start first with our Getting Started guide.

| NOTE With the initial release, tamper-proof queries are not supported through the SxTCLI or JDBC. 

Rather than walk through all steps of creating a table, inserting data, and querying the data, we're going to take a look at the specific steps that are unique to tamper-proof queries. After that, we'll walk through the end-to-end steps for running running a sxt-tamper-proof-example.py script. 

## Tamper-proof query basics 

The end-to-end workflow involves the following steps: 

1) Authenticate with SxT API
2) Create a biscuit 
3) Create a tamperproof table
4) Insert data into a tamper-proof table
5) Query the tamperproof table

Authentication and biscuit creation are the same so we don't need to address those. 

### Create a tamper-proof table 

Let us take a look the SQL used to create a tamper-proof table:

```SQL
CREATE TABLE <resource_id> (ID BIGINT, PROOF_ORDER BIGINT, PLANET VARCHAR, PRIMARY KEY(ID)) WITH 
        "public_key=<biscuit_public_key>,access_type=public_read,tamperproof=true,immutable=true,persist_interval=10
```

**Please note that the `PROOF_ORDER` column is required with this initial release.** The ID and PLANET columns are just examples and are not required.   

`resource_id` will be for the schema.table that you're creating, and `biscuit_public_key` will be your biscuit public key. 

You've probably seen `access_type` before but the next three WITH flags are likely new. 

- `tamperproof=true` - As you might expect, this tells SxT that you want to create a tamper-proof table. 
- `immutable=true` - Immutable is also required for tamper-proof tables. 
- `persist_interval=10` - While optional, this flag tells SxT to flush the data to ignite in 10 seconds. 

That's all you need on the CREATE side!

### Insert data into a tamper-proof table

```SQL 
INSERT INTO <resource_id> (ID, PROOF_ORDER, PLANET) VALUES (0, 0, 'VENUS')
```

The `PROOF_ORDER` column needs to be strictly increased. For now, this needs to be done manually but in the future,`auto-increment`` will handle this in the background for you. 

### Query tamper-proof table 

```SQL
SELECT * FROM <resource_id>
```
The SQL itself for a tamper-proof query is identical, however, there is a new tamper-proof query endpoint and some notable differences in the header, payload, and response data that we need to look at. 

1) new API endpoint - This URL will be provided to you by the SxT team  
2) In the headers take note of the deviation from the standard JSON accept: `"accept": "application/octet-stream",`  
3) In the payload, please note that we use `resourceId` for the resource id.
4) Response data - The tamper-proof query endpoint returns query response data in Arrow IPC format. For that reason, we'll need to do a little processing on the response data to deserialize it from binary and make it human-readable. 

## SxT-tamper-proof-example.py 

This script goes through a full end-to-end demonstration of: 
1) Authenticating 
2) Creating a biscuit 
3) Creating a tamper-proof table
4) Inserting data into a tamper-proof table 
5) Querying a tamper-proof table 

For the sake of simplicity, this script will create a new biscuit and random table for you under the `se_playground` schema. You can use your own schema by providing it as a command line arg to the script like this: `python SxT-tamper-proof-example.py <your-schema-here>`

### Setup and requirements 

1) Download the repo 
`git clone... TBD`

2) Set up your Python virtual env 

It doesn't matter how you do this. I like to use the virtualenv plugin for pyenv. You can create your environment with the virtualenv plugin like this:
`pyenv virtualenv 3.11.2 POFSQL-3.11.2`

Now it will pick up the `.python-version` file from the repo and automatically activate this env when you are in this directory. 

3) Setup your env

`cp sample.env .env`

Add your username and pub/priv key pair used for auth. 

4) Run it

`python SxT-tamper-proof-example.py`








