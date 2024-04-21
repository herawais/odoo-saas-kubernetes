Either Use managed db service from [DO](https://www.digitalocean.com/products/managed-databases-postgresql)



or Setup a new VPS and install Postgres on your VPS 


and dont forget to setup and alowing remote host connections


    vim /etc/postgresql/14/main/postgresql.conf

Uncomment and edit the listen_addresses attribute to start listening to start listening to all available IP addresses.

    listen_addresses = '*'

Now edit the PostgreSQL access policy configuration file.

    vim /etc/postgresql/14/main/pg_hba.conf


    Append a new connection policy (a pattern stands for [CONNECTION_TYPE][DATABASE][USER] [ADDRESS][METHOD]) in the bottom of the file.


    host all all 0.0.0.0/0 md5

We are allowing TCP/IP connections (host) to all databases (all) for all users (all) with any IPv4 address (0.0.0.0/0) using an MD5 encrypted password for authentication (md5).

It is now time to restart your PostgreSQL service to load your configuration changes.

    systemctl restart postgresql

And make sure your system is listening to the 5432 port that is reserved for PostgreSQL.

    ss -nlt | grep 5432

