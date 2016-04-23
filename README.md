![FunkyStore](https://raw.githubusercontent.com/MEDVEDx64/FunkyStore/master/storage/funky.png)

***
*Disclaimer. This stuff may not be suitable for you, because
it is initially were written for my own Minecraft server.
It is quite possible that you will need to change something in the code.*
***
*Disclaimer #2. FunkyStore may become a reason of your Minecraft server crash.*
***

This is an online in-game item store for vanilla Minecraft servers.
It DOES NOT deals with real money, there are an internal
pseudo-currency called Funks is used to buy things.
FunkyStore includes .schematiic file format printer feature,
that allows to print buildings (etc.) directly to server's world.

Requirements
------------

* Vanilla Minecraft >= 1.7 server with configured RCON
* MongoDB and pymongo
* PyYaml
* [pymclevel](https://github.com/mcedit/pymclevel) and it's dependencies
* [MCRcon](https://github.com/barneygale/MCRcon)

*RockMongo* web interface installation is recommended.

Getting it working
------------------

* Copy/move `config_default.py` to `config.py` and edit it
* Run `python funky.py`.

Becoming an administrator
-------------------------

* Register an account
* Append "admin" string to "flags" field of your account entry from collection "punky". It can be achieved by executing the following code in mongo console: `db.accounts.update({}, {"$push":{"flags": "admin"}})`
