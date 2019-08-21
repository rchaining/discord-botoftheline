This python bot fetches spells from a dropbox-hosted sqlite database, and posts them.
Currently the commands are:
$spell contains <keywords>
and
$spell named <keywords>

$spell contains will search for any spells whose names contain the supplied keywords. This returns a maximum of 10 spells
$spell named will return any spell whose name matches the supplied keywords. Some spells cannot be returned with $spell contains, as they will exceed the search limit.

Discord has a limit of 2000 characters per message, and spells that exceed that character limit will be sent with a truncated description.

The sqlite db is constructed using the excel provided here: http://www.pathfindercommunity.net, and converted into sql using a seperate python tool.

This app is currently hosted on Heroku. Due to heroku's ephemeral memory, the DB is stored on a seperate file system, within Dropbox.
To make this app work, you will need to host your db on dropbox in the root db. You can select a seperate root directory for a given application. The db must be named, 'spells_sqlite.db'.

This uses several configuration settings. Heroku will set these in the os environment variables. You will need to set these vars:
token: The discord token for your application
dbx_token: The dropbox token for your application

This bot will not work without these variables supplied. With heroku, you can set them in the settings tab, under 'config vars'