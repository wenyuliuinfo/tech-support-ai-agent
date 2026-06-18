# Deployment Configuration

## 1. Vector DB Configuration
Need to run the following command to start a docker container as Pinecone Vector DB:

```bash
docker run -d \
  --name pinecone-local \
  -e PORT=5080 \
  -e PINECONE_HOST=localhost \
  -p 5080-5090:5080-5090 \
  --platform linux/amd64 \
  ghcr.io/pinecone-io/pinecone-local:latest
```

## 2. Relational DB Configuration
Need to run the following command to start another docker container as PostgreSQL Relational DB:

```bash
docker run -d \
  --name postgres-local \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data
  postgres:16
```

## 3. Environment Variables
Set the following environment variables locally to form the connection with Pinecone and PostgreSQL:

```
# For connecting with Pinecone
PINECONE_API_KEY="your_key_here"
PINECONE_HOST_URL="http://localhost:5080"

# For connecting with PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME="your_db_name"
DB_USER="your_user_name"
DB_PASSWORD="your_password"
```