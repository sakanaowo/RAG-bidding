# This environment setup is for linux (ubuntu) only:  
## Setup local database:

- Install postgres:
```shell
sudo apt install postgresql
sudo apt install postgresql-16-pgvector
``` 
- Setup database:
```shell
sudo -u postgres psql
```
- Create Database:
```shell
create role <your-role> with login password 'your-password' nosuperuser nocreatedb nocreaterole
```
```shell
create database <your-db-name> owner <your-role> encoding 'UTF8' template template0
```
- Create extension:
```shell
sudo -u postgres psql -d ragdb -c 'create extension if not exists vector;'
```
- Check if extension installed:
```shell
sudo -u postgres psql -d ragdb -c '\dx'
```
- It should show up `plpgsql` and `vector`

## Setup conda environment 
```ps
conda create -n rag-bidding python=3.10 # env name could be change if u want
```
```shell
pip install -U 
  "langchain==0.3.27"
  "langchain-openai==0.3.33"
  "langchain-postgres==0.0.15"
  "langchain-community==0.3.29"
  "langchain-text-splitters==0.3.11"
  "psycopg[binary]"
```
## Configure environment
```shell
OPENAI_API_KEY=
DATABASE_URL=
EMBED_MODEL=
EMBED_DIM=3072
CHAT_MODEL=
DB_USER=rag
DB_PASSWORD=
DB_NAME=
``` 