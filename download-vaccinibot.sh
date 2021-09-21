if [[ -z "$2" ]] ; then
    echo -n 'Token bot: '
    read Token
    echo -n 'Chat id amministratore: '
    read cid
else
    Token = $1
    cid = $2
fi

curl https://raw.githubusercontent.com/Aldo97/VacciniBot/main/vaccinibot.py --silent --output vaccinibot.py
curl https://raw.githubusercontent.com/Aldo97/VacciniBot/main/istat21.csv --silent --output istat21.csv
curl https://raw.githubusercontent.com/Aldo97/VacciniBot/main/start-vaccinibot.sh --silent --output start-vaccinibot.sh
curl https://raw.githubusercontent.com/Aldo97/VacciniBot/main/update-vaccinibot.sh --silent --output update-vaccinibot.sh

sed -i '27s/.*/TOKEN = "'$Token'"/' vaccinibot.py
sed -i '29s/.*/cid = '$cid'/' vaccinibot.py

# Installing python botenv
python3 -m venv botenv/
source botenv/bin/activate

pip3 install flask python-telegram-bot requests pandas

clear
echo "VacciniBot avviato"

python3 vaccinibot.py
