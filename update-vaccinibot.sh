sed '27q;d' vaccinibot.py > Token
sed '29q;d' vaccinibot.py > cid

curl https://raw.githubusercontent.com/Aldo97/VacciniBot/main/vaccinibot.py --silent --output vaccinibot.py

sed -i '27d;26r Token' vaccinibot.py
sed -i '29d;28r cid' vaccinibot.py

rm Token
rm cid
