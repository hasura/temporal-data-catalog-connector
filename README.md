# Hasura Metadata Manager

## Description

The Hasura Metadata Manager is an agent process that runs temporarily
alongside a supergraph container in order to maintain a temporal database of schema changes in a database
and optionally manages the current state schema in a neo4j graph.

The neo4j graph allows you to do path analysis and graph analytics.

The database can be queried directly, it can be attached to a supergraph for 
querying through the supergraph, and if attached to the supergraph you can use
Hasura PromptQL to respond to natural language queries about the schema and its
changes over time.

## How does it work?

Start by cloning this repo, on the same machine where you do your supergraph builds/

There is subdirectory called the `hasura_metadata_agent`. A supergraph can invoke this agent
by simply including `hasura_metadata_agent/compose.yaml` in the supergraph compose file. 

On a supergraph startup it does the following.
<ol>
    <li>It will determine if the temporal, normalized supergraph metadata database exists.</li>
    <li>If it does not exist it will create it</li>
    <li>It will examine the `engine/build/metadata.json` file and determine if the date of 
    that file is after the last recorded date of the database version of the build
        <ul>
            <li>If the DB does not exist it will create it and populate with the initial values</li>
            <li>If the DB does exist
                <ul>
                    <li>and the date of the DB is on or after the file date - it will do nothing</li>
                    <li>otherwise, it examines each element
                        <ul>
                            <li>if the element has not changed, it does nothing</li>
                            <li>if it has changed, it makes the current
                                element not current, and append a new current 
                                element with the changes</li>
                        </ul>
                    </li>
                </ul>
            </li>
        </ul>
    </li>
    <li>At the end of this process it will also synchronize a neo4j graph database to the current schema.</li>
</ol>

### Configuring the Agent

#### Environment Variables Documentation

You can modify the behavior of the agent by making changes to `hasura_metadata_agent/.env`

###### General Configuration

| **Variable**         | **Description**                                                                                                                                                  | **Example Value**        |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| `ENGINE_BUILD_PATH`   | File path to the metadata JSON file used during the build process. This is copied in this location within the container, you probably don't need to change this. | `/build/metadata.json`   |

---

###### Keep-Alive Configuration

These variables configure **keep-alive** settings for maintaining persistent connections with timeouts. Some databases use these. If you database does not use these, you may need to remove them.

| **Variable**           | **Description**                                                                                 | **Example Value**        |
|-------------------------|-----------------------------------------------------------------------------------------------|--------------------------|
| `KEEPALIVES`           | Enables or disables keep-alive connections. Set to `1` to enable, `0` to disable.             | `1`                      |
| `KEEPALIVES_COUNT`     | Maximum number of keep-alive probes to send before closing the connection.                     | `20`                     |
| `KEEPALIVES_IDLE`      | Timeout in seconds before the first keep-alive probe is sent when the connection is idle.      | `1800`                   |
| `KEEPALIVES_INTERNAL`  | Interval in seconds between keep-alive probes when no response is received.                   | `60`                     |

---

###### Database Pooling Configuration

These variables control the behavior of database connection pooling to manage and optimize database connections.

| **Variable**       | **Description**                                                                               | **Example Value**        |
|---------------------|-----------------------------------------------------------------------------------------------|--------------------------|
| `MAX_OVERFLOW`     | Maximum number of connections allowed to be created above the pool size.                      | `30`                     |
| `POOL_SIZE`        | Size of the connection pool, i.e., the number of connections maintained in the pool.          | `20`                     |
| `POOL_PRE_PING`    | Validates the connection before it is checked out of the pool (`yes` or `no`).                | `yes`                    |

---

###### Authentication Configuration

| **Variable**       | **Description**                                                                                                                                                        | **Example Value**        |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| `M_AUTH_KEY`       | Secret authentication key used for securing requests. You can change this if you would like - provided you change the corresponding version in the related containers. | `secret`                 |

---

###### Database Configuration

| **Variable**       | **Description**                                                                                                                                                                                            | **Example Value**        |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| `DATABASE_URL`     | Connection string for the database, including credentials and endpoint. Currently its designed to point to an private provisioned postgres database. But anything that SQLAlchemy supports will work fine. | `postgresql://postgres:password@db:5432` |

---

###### Database Cleaning

| **Variable**       | **Description**                                                                                                                                                                                                                           | **Example Value**        |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| `CLEAN_DATABASE`   | Determines whether to clean the database on startup (`yes` or `no`). Typically you set this to no, if the DB doesn't exist it will create it anyways. If you want to start tracking over, set this to yes and run once, then set it back. | `no`                     |

---

###### Build Configuration

| **Variable**         | **Description**                                                                                                                                                                                                                                       | **Example Value** |
|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| `EXCLUDED_SUBGRAPHS` | Subgraphs to exclude from operations (comma-separated list). If you expose the build database into the same supergraph you don't want to analyze its metadata. I recommend you create a subgraph called `data_quality` and expose the build db there. | `data_quality`    |
| `SRC_DIR`            | Point this to the directory where your supergraph build is placed                                                                                                                                                                                     | `example`         |
---

###### Neo4j Configuration

These variables define the configuration for interacting with a **Neo4j** graph database.

| **Variable**       | **Description**                                                                                                                                              | **Example Value**        |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| `NEO4J_URI`        | URI of the Neo4j instance, specifying the protocol (`bolt`) and endpoint. Its currently set to point to a private provisioned neo4j db within the container. | `bolt://neo4j:7687`      |
| `NEO4J_DATABASE`   | Name of the Neo4j database to use.                                                                                                                           | `neo4j`                  |
| `NEO4J_AUTH`       | Credentials for connecting to the Neo4j instance, formatted as `username,password`.                                                                          | `neo4j,password`         |

---

###### Notes:
- Remember to use secure mechanisms (e.g., secret management systems) for sensitive details like `DATABASE_URL`, `M_AUTH_KEY`, and `NEO4J_AUTH`.
- Adjust the values as per your specific environment setup. 

### More Configuration Options Through the Agent's `compose.yaml` File.

```yaml
services:
  db:
    image: postgres:15
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - 32100:5432
  metadata-app:
    depends_on:
      - db
      - neo4j
    build:
      context: ..
      dockerfile: hasura_metadata_agent/Dockerfile
      # We can use ARGS in Docker Compose to pass parameters during the build process.
      args:
        - SRC_DIR=$SRC_DIR
    env_file:
      - .env

  neo4j:
    image: neo4j:5
    container_name: neo4j
    ports:
      - 7474:7474  # HTTP port for accessing Neo4j Browser
      - 7687:7687  # Bolt port for database interactions
    environment:
      NEO4J_AUTH: "neo4j/password"  # Username: neo4j, Password: password
    volumes:
      - neo4j_data:/data  # Persistent data storage
      - neo4j_logs:/logs  # Persistent logs storage
      - neo4j_import:/var/lib/neo4j/import  # Import directory if needed
      - neo4j_plugins:/plugins  # Plugins directory if needed

volumes:
  db_data:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:

```

You could choose to NOT use the neo4j or pg instances - and host them externally.

### Putting it All Together
Finally include the compose file at the top of your supergraph compose file.

Here's an example (you may need to alter the path of the `hasura_metadata_agent` depending on its 
relationship to the supergraph build like this example:

```yaml
include:
  - path: app/connector/chinook/compose.yaml
  - path: ../hasura_metadata_agent/compose.yaml
```

Now run `ddn run docker-start` and within a few minutes your initial db will be populated.

## Adding Schema Metadata to the Supergraph

You may choose to expose your supergraph schema db as a data source within your supergraph. 
The instructions below assume you are doing a local build, you would need
work through adjusting these to a cloud build.

<ol>
<li>Within your supergraph, run `ddn subgraph init data_quality`
<li>The next step depends on you choice of database, but something like - `ddn connector init mdata -i --subgraph data_quality/subgraph.yaml` 
and add in the correct database params.</li>
<li>Then, `ddn connector introspect mdata --subgraph data_quality/subgraph.yaml --add-all-resources`</li>
<li>Then, `ddn supergraph build local</li>
<li>Then, `ddn run docker-start`</li>
</ol>

# Wrapping it up

Your supergraph metadata is now available within the supergraph for direct reporting and analysis, its available as a direct connection to your database, and you can browse your metadata through neo4j.

