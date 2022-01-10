![FunkyStore](https://raw.githubusercontent.com/MEDVEDx64/FunkyStore/master/storage/funky.png)

***
*Disclaimer. This stuff may not be suitable for you, because
it is initially were written for my own Minecraft server.
It is quite possible that you will need to edit the code to fit your server setup.*
***
*Disclaimer #2. FunkyStore may become a reason of your Minecraft server crash.*
***
*Disclaimer #3. The code is **BAD**, please, never write web applications that way.*
***

This is an online in-game item store for vanilla Minecraft servers.
It is NOT about real money, there are an internal
pseudo-currency called Funks is used to buy things.

Requirements
------------

* **Python 2.7**
* Vanilla Minecraft >= 1.18 server with configured RCON
* MongoDB and pymongo
* PyYaml
* [pymclevel](https://github.com/mcedit/pymclevel) and it's dependencies
* [MCRcon](https://github.com/barneygale/MCRcon) (checkout to 149b9c1)

Getting it working
------------------

* Copy `config_default.py` to `config.py` and edit it;
* Run `./first_run.py`;
* Set up `./funky.py` to run as a system service or run it directly.

Becoming an administrator
-------------------------

* Register an account
* Append "admin" string to "flags" field of your account entry from collection "funky". It can be achieved by executing the following code in mongo console: `db.accounts.update({}, {"$push":{"flags": "admin"}})`

Markerplace definition example
------------------------------

Marketplaces has no implementation in FunkyStore's admin console
and have to be pushed into `markets` collection manually. See [an example](market_example.json).
