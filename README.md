# Cardinal Bombsquad Server Scripts
- script version: 1.7.61
- protocol version: 36/editable (game versions below script version won't be allowed to join)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-7289DA?style=for-the-badge&logo=discord&logoColor=white&labelColor=7289DA)](https://discord.gg/yrYqbSU7wT)

# Installation:
### Quick one-line installation
```
curl -fsSL https://install.thecardinal.workers.dev | bash
```

- you may now change mods_config.json to your liking.

### Cd into the directory
```
cd Cardinal
```

### Open a tmux session (you should always do this when starting the server)
```
tmux
```

### Run the server.
```
./bombsquad_server
```

# Discord Bot:
- runs the bot on a second process. (the server won't lag)
- uses socket tunnel to pass the payload through.
- you can toggle the bot and configure the owner-id and bot token in mods_config.json

## Bot Commands:
- /cmd <enter your chat-command to be send to game server.> (it runs according to the authority of the user.)
- /say <your chat message> (you can send a chat message to the game directly.)
- /owner or /admin <mention the user> (adds/removes from the owners or admins)
- /list (to receive list of players inside the game)

# Tournament System:
- it is an automated system made for tournaments.
- it works when bot is enabled, since all the tournaments are handled with bot commands only.

## Tournament Setup:
- you need to have three channels in your server:
- 1. brackets
- 2. results
- 3. dashboard
- you have to create webhook for each of the channels and put them in the mods_config.json under the discord's webhooks section.
- in the dist/ba_root/mods/tournament/graphics/runner.py, you have to replace the title and logo png with your own logo and title png urls (make sure they are raw urls)

## Tournament Features:
- Automatically generates brackets for the tournament based on the number of teams/solo.
- Automatically posts a result upon completion of the tournament match.
- Dashboard features a players ranking to see the top players of the tournament.
- If groups are made, it will automatically generate a group stage, and the dashboard for each group will be posted.
- note: make sure the number of teams is not less than 4 and is divisble by 4.

## Tournament Commands:
- /tournament create \<type> \<series> (creates a tournament season)
- /tournament registrations \<open/close> (opens/closes the registrations)
- /tournament register (registers a player to the tournament)
- /tournament uuid \<user-mention> \<uuid> (changes the uuid of the registered player)
- /tournament start (starts the tournament)
- note: only the leader can use the commands aside from the register command.

## Tournament Registration:
- /tournament register
- if solo, it will be quick with a verification code.
- if team, it will require you to invite your teammates and then send you the verification code.
- note: if any invited member is already registered, or one of them declines the invitation.. the registration will be cancelled.
- in game. you will have to run /verify \<code> to verify yourself.

## Tournament Match:
- /ready
- this command marks the player ready for their match, that is if they have one pending.
- once all the players of a certain match are ready, the match will start.

## Tournament Security:
- the device uuid and account id used when verifying with /verify command will be saved.
- if the player then tries to join the game with different device uuid or account id, they would be unable to join in a match.
- at this times, admins will need to use /tournament uuid command to change the uuid of the player if they see fit or disqualify the player.
