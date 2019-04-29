**Script that goes through every site specified in `config.ini`
and tries to reach it.**

Script is meant to be set on cron schedule. In our company we set it to be ran every 15 minutes.

If site can not be reached or responds with status code
other than 200, function will notify user via email. If the web-site stays down
for two checks in a row, you will not get notification that site is down.
After next check, if site goes back online, user will get an email notification.

Sites you want check, emails to sent notifications to, email server and account used to send 
notifications — all this is set in the `config.ini` file.

By default, script will use `config.ini` that is located in the same folder as `ping.py`. If you need other config
files, you can provide path to them as second console argument.

Log files stored in the same folder as `ping.py`. You can provide custom path for them in a `config.ini` file.

On the first launch script will generate `sites_state.json`, which is used to keep track of previous checks.

`**config.ini**` structure:

in the example is user GMAIL SMTP server, you can use any server you like

```
[EMAIL]
SMTP_SERVER = smtp.gmail.com
PORT = 465
FROM_EMAIL = yourEmail@gmail.com
PASSWORD = emailPassword

[RECIPIENTS]
EMAILS = ["JohnDoe@gmail.com", "wednesday@asgarg.com"]

[SITES]
SITES = ["https://www.google.com/", "https://duckduckgo.com/", "https://github.com/"]

[LOG]
PATH = ./ping.log
EMAIL = ./mail_error.log
```

