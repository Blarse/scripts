#!/bin/bash -efu

# https://gist.github.com/thingsiplay/e03a84ebc6e01c9b475cd0277fb81def

# Count unread mails in Thunderbird and write to stdout.
# Usage:
#     checkmails.sh

# Path to your Thunderbird profile.
profile="$HOME/.thunderbird/$(cat $HOME/.thunderbird/installs.ini | sed -n 's/Default=\(.*\)/\1/p')"

# Regex to find the unread message lines.
# Adding "9F" in front of regex works for ImapMail, but not for pop3. in Mail.
regex='\(\^A2=([0-9]+)'

count_unreadmails() {
    count=0
    result=$(grep -Eo "$regex" "$1" | tail -1)
    if [[ $result =~ $regex ]]
    then
        count="${BASH_REMATCH[1]}"
        unreadmail_count=$(($unreadmail_count + $count))
    fi
    return $count
}

unreadmail_count=0

# Includes all grouped mail specified in the right mouse menu on inbox folder.
for inbox in "$(find "$profile" -iname inbox.msf)"
do
    count_unreadmails "$inbox" ||:
done

# Use `echo -n` if no newline should be added.
echo -n "$unreadmail_count"
