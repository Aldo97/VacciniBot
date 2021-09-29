#    <VacciniBot: a telegram bot interpreting Italian vaccination data>
#    Copyright (C) 2021 Aldo Tarquilio

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>
    
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import telegram
import pandas as pd
import datetime as date
import locale
import time
import threading
import requests

# IMPORTANTE: inserire il token fornito dal BotFather nella seguente s>
TOKEN = ""
# Chat id dell'amministratore del bot
cid =

def help(update,context):
	if len(update.message.text.split()) == 2:
		if extract(update.message.text,1) == "vaccinati":
			update.message.reply_text("Funzione sperimentale, due modalità di utilizzo:\n-Senza argomento viene proposto un messaggio interattivo in cui è possibile variare fra le varie regioni, fasce di età e tipo di vaccino somministrato.\n-Come sopra ma con una o due date inserite come argomento (il funzionamento è il medesimo di /somministrazioni)")
		elif extract(update.message.text,1) == "istat21":
			update.message.reply_text("Tre modalità di utilizzo:\n-Senza argomenti restituisce la popolazione residente in Italia secondo i dati ISTAT21 divisi in fasce di età\n-Con argomento il nome di una regione(seguendo le regole del comando somministrazioni) vengono restituite le fasce di età secondo ISTAT21 relative alla regione immessa\nCon argomento 'download' il bot invierà il file csv con i dati ISTAT21 divisi in fasce di età usati dallo stesso.")
	elif len(update.message.text.split()) > 2:
		update.message.reply_text("Troppi argomenti! Scrivere inviare solo /help per maggiori informazioni")
	else:
		update.message.reply_text("Aggiungere al comando /help come argomento il comando interessato: vaccinati, istat21\nSi ringraziano la Struttura Commissariale e l'ISTAT per i dati sui vaccini e la situazione demografica 2021\nHelp fatto di fretta, bot nelle fasi iniziali (ho poco tempo per migliorarlo, se volete dare suggerimenti usate il comando /segnalazione, ricordate che dovete avere un username!)")

def convert_data(data):
	return date.datetime.strptime(data, '%Y%m%d').strftime('%d %B %Y')
    
def segnalazione(update, context):
	user = update.message.from_user
	if user['username'] == None:
		update.message.reply_text("Si prega di impostare un username, segnalazione non inviata")
		raise Exception("Segnalazione senza username")
	if len(update.message.text.split()) == 1:
		update.message.reply_text("Si prega di immettere il messaggio della segnalazione come argomento del comando /segnalazione")
		telegram.Bot(token=TOKEN).send_message(chat_id=cid, text="Segnalazione vuota da: @" + user['username'])
	else:
		telegram.Bot(token=TOKEN).send_message(chat_id=cid, text=update.message.text[14:] + "\n\nSegnalazione da: @" + user['username'])
		
def consegne(dis,**kwargs):
	data=kwargs.get('data',False)
	reg=kwargs.get('reg',False)
	forn=kwargs.get('forn',False)
		
	if data:
		dis = dis[pd.to_datetime(dis['data_consegna'], format='%Y-%m-%d') <= date.datetime.strptime(data,'%Y%m%d')]
	if reg:
		dis = dis[dis.area == reg]
	if forn:
		dis = dis[dis.fornitore == forn]
		sumJ = 0
	else:
		sumJ = 0
		disJ = dis[dis.fornitore == "Janssen"]
		for i in disJ.numero_dosi.tolist():
			sumJ += i

	sum=0
	for i in dis.numero_dosi.tolist():
		sum += i
		
	if sumJ != 0:
		sum-=sumJ

	return sum,sumJ
	
def bar(valore,tot,**kwargs):	
	nextended = kwargs.get("nextended", False)
	perc = round(valore*100/tot,2)
	progresso = int(27 * valore // tot)
	if valore / tot <= 1 or nextended:
		bar = '█' * progresso + '░' * (27 - progresso)
		return f'\r|{bar}| \n{perc}%     (`{valore}`/`{tot}`)'
	else:
		bar1 = '█' * 27
		bar2 = '█' * (progresso - 27) + '░' * (54 - progresso)
		return f'\r|{bar1}|\n\r|{bar2}| \n{perc}%     (`{valore}`/`{tot}`)'
	
def somministrazioni(som,**kwargs):
	data1=kwargs.get('data1',False)
	data2=kwargs.get('data2',False)
	reg=kwargs.get('reg',False)
	forn=kwargs.get('forn',False)
	fascia=kwargs.get('fascia',False)
	
	if data1:
		som = som[pd.to_datetime(som['data_somministrazione'], format='%Y-%m-%d') >= date.datetime.strptime(data1,'%Y%m%d')]
	if data2:
		som = som[pd.to_datetime(som['data_somministrazione'], format='%Y-%m-%d') <= date.datetime.strptime(data2,'%Y%m%d')]
	if reg:
		som = som[som.area == reg]
	if forn:
		som = som[som.fornitore == forn]
	
	if fascia:
		if fascia == "80+":
			som = som[som.fascia_anagrafica == "80-89"].append(som[som.fascia_anagrafica == "90+"])
		else:
			som = som[som.fascia_anagrafica == fascia]
		
	sum=0
	for i in som.prima_dose.tolist():
		sum += i

	sumpreJ=0
	if forn == False:
		sumJ = 0
		for i in som[som.fornitore == "Janssen"].prima_dose.tolist():
			sumJ += i
		for i in som[som.fornitore == "Janssen"].pregressa_infezione.tolist():
			sumJ += i
			sumpreJ += i
		sum = sum - sumJ
	sum2=0
	for i in som.seconda_dose.tolist():
		sum2 +=i
	
	sumpre = 0	
	for i in som.pregressa_infezione.tolist():
		sumpre += i
	sum += sumpre
	if forn != "Janssen":
		sum2 += sumpre
	
	if forn == False:
		return sum,sum2,sumJ,sumpre,sumpreJ
	else:
		return sum,sum2,0,sumpre,sumpreJ
		
def pop(plat,**kwargs):
	fascia=kwargs.get('fascia',"tot")
	reg=kwargs.get('reg',"IT")
		
	if fascia == False:
		fascia = "tot"
	if reg == False:
		reg = "IT"
	if plat == "1":
		return platea(file_platea,fascia,reg)
	else:
		return istat21(dati_istat21,fascia,reg)
	
def istat21(dati_istat21,fascia,reg):
	dati_istat21 = dati_istat21[dati_istat21.area == reg]
	
	sum = dati_istat21.loc[dati_istat21.fascia == fascia, "value"].tolist()[0]
	
	if fascia == "tot":
		sumN = 0
		sumV = sum - dati_istat21.loc[dati_istat21.fascia == "0-11", "value"].tolist()[0]
	else:
		sumV = 0
		
	return sum,sumV

def platea(file_platea,fascia,reg):
	if reg != "IT":
		file_platea = file_platea[file_platea.area == reg]
	
	if fascia != "tot":
		file_platea = file_platea[file_platea.fascia_anagrafica == fascia]
	
	sum = 0
	for i in file_platea.totale_popolazione:
		sum += i
		
	return sum,sum

def somm_d_a(som, **kwargs):
	data1=kwargs.get('data1',False)
	data2=kwargs.get('data2',False)
	reg=kwargs.get('reg',False)
	forn=kwargs.get('forn',False)

	if data1:
		som = som[pd.to_datetime(som['data_somministrazione'], format='%Y-%m-%d') >= date.datetime.strptime(data1,'%Y%m%d')]
	if data2:
		som = som[pd.to_datetime(som['data_somministrazione'], format='%Y-%m-%d') <= date.datetime.strptime(data2,'%Y%m%d')]
	if reg:
		som = som[som.area == reg]
	if forn:
		som = som[som.fornitore == forn]
	
	sum = 0
	for i in som.dose_aggiuntiva.tolist():
		sum += i
	
	return sum
		
def platea_d_a(platea,**kwargs):
	reg=kwargs.get('reg',False)
	
	if not reg:
		popolazione = 0
		for i in platea.totale_popolazione.tolist():
			popolazione += i
	else:
		popolazione = int(platea.loc[platea.area == reg, "totale_popolazione"])
	
	
	return popolazione

def istat21_show(reg):
	if reg == "0" or reg == "IT":
		reg = "IT"
		reg_name = "Italia"
	else:
		reg_name = file_platea.loc[file_platea.area == reg].nome_area.tolist()[0]

	fascia = ["0-11","12-19","20-29","30-39","40-49","50-59","60-69","70-79","80-89","90+"]
	
	pop = dati_istat21[dati_istat21.area == reg]
	tot = pop.loc[pop.fascia == "tot", "value"].tolist()[0]
	string = reg_name + "\nPopolazione di riferimento (ISTAT21)\n"
	
	for i in fascia:
		string += "\nFascia " + str(i) + ": " + bar(pop.loc[pop.fascia == i, "value"].tolist()[0],tot)
	
	string += "\n\nPopolazione totale: " + str(tot)
	
	return string

def vaccinati(update,CallbackContext):
	if len(update.message.text.split()) == 3:
		data1 = extract(update.message.text,1)
		data2 = extract(update.message.text,2)
		if data1 == "0" and data2 != data1:
			update.message.reply_text("Il primo campo data non può essere 0 se il secondo non è 0")
			return
		
	elif len(update.message.text.split()) == 2:
		data1 = extract(update.message.text,1)
		data2 = data1
		
	elif len(update.message.text.split()) == 1:
		data1 = "0"
		data2 = "0"
	
	else:
		update.message.reply_text("Inserire una regione soltanto o nessun argomento")
		raise Exception("Opzione non contemplata")
	
	forn = "0"
		
	inf = "0," + "0" + "," + forn + "," + data1 + "," + data2 + ",0"
	
	if data2 != "0" and data2 != data1:
		string = "Somministrazioni dal " + convert_data(data1) + " al " + convert_data(data2)
	elif data1 != "0":
		string = "Somministrazioni del " + convert_data(data1)
	else:
		string = ""

	keyboard = [
	[
		telegram.InlineKeyboardButton("Fascia", callback_data='F' + inf),
		telegram.InlineKeyboardButton("Vaccino", callback_data='V' + inf),
		telegram.InlineKeyboardButton("Regione", callback_data='R' + inf),
	],
	[
		telegram.InlineKeyboardButton("Data", callback_data='D' + inf),
		telegram.InlineKeyboardButton("Ieri", callback_data=change(inf,3,(date.datetime.today() - date.timedelta(days=1)).strftime('%Y%m%d'),False)),
	],
	[
		telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
	],
	]
	
	reply_markup = telegram.InlineKeyboardMarkup(keyboard)
	
	update.message.reply_text(string + "\nSelezionare una fascia di età, un tipo di vaccino, una regione o delle date", reply_markup=reply_markup)
	
def fascia(info):
	fascia = info.split(",")[0]
	reg = info.split(",")[1]
	forn = info.split(",")[2]
	data1 = info.split(",")[3]
	data2 = info.split(",")[4]
	plat = info.split(",")[5]

	mancanti = False
	if fascia[:1] == "-":
		fascia = fascia[1:]
		mancanti = True
		
	sommafascia = False
	fasciaavaccini = False
	vacciniafascia = False
	if fascia[:1] == "+":
		fascia = fascia[1:]
		sommafascia = True
	elif fascia[:1] == "*":
		fascia = fascia[1:]
		fasciaavaccini = True
	elif fascia[:1] == "%" or fascia[:1] == "&":
		if fascia[:1] == "%":
			prime = True
		else:
			prime = False
		fascia = fascia[1:]
		vacciniafascia = True
	elif fascia[:1] == "?":
		fascia = fascia[1:]
		
	if fascia == "1":
		fascia = "0"
		vac = True
	else:
		vac = False
		
	if plat == "1" and fascia == "0":
		vac = True
		
	if forn == "J&J":
		forn = "Janssen"
	elif forn == "Pfizer" or forn == "Biontech" or forn == "BioNTech":
		forn = "Pfizer/BioNTech"
	elif forn == "Astrazeneca" or forn == "Vaxzevria" or forn == "Az":
		forn = "Vaxzevria (AstraZeneca)"
	
	if mancanti:
		forn = False
		data1 = False
		data2 = False
		
	if reg == "0" or reg == "False" or reg == "Italia":
		reg = False
	
	if reg:
		string = file_platea.loc[file_platea.area == reg].nome_area.tolist()[0]
	else:
		string = "Italia"
		
	if forn == "0" or forn == "False":
		forn = False
	
	if forn and fasciaavaccini == False:
		string += "\n" + forn

	if data1 == "0" or data1 == "False" or data1 == False:
		data1 = False

	if data2 == "0" or data2 == "False":
		data2 = data1
		
	if data2 and data2 != data1:
		string += "\ndal " + convert_data(data1) + " al " + convert_data(data2)
	elif data1:
		string += "\ndel " + convert_data(data1)
		
	if plat == "0":
		string += "\nDati ISTAT21"
	else:
		string += "\nFile PLATEA"

	if fascia == "50" and sommafascia == False:
		if plat == "0":
			fascia = "50-59 60-69 70-79 80-89 90+"
		else:
			fascia = "50-59 60-69 70-79 80+"
		string += "\nOver 50"
	elif fascia == "49" and sommafascia == False:
		fascia = "12-19 20-29 30-39 40-49"
		string += "\nUnder 50"
	elif fascia == "30" and sommafascia == False:
		fascia = "12-19 20-29"
		string += "\nUnder 30"
	
	if sommafascia:
		return sommfascia(string,reg,forn,data1,data2,plat)
	elif fasciaavaccini:
		if len(fascia.split()) == 1 and fascia != "0":
			string += "\nFascia " + fascia
		elif fascia == "0" and vac == False:
			string += "\nPopolazione generale"
		elif vac == True:
			string += "\nPopolazione vaccinabile"
		return fasciavaccini(string,reg,fascia,data1,data2,vac,plat)
	elif vacciniafascia:
		return vaccinifascia(string,reg,forn,data1,data2,prime,plat)
		
	som1=0
	som2=0
	somJ=0
	sompre=0
	sompreJ=0
	po=0
	pov=0
	for i in fascia.split():
		if i == "0":
			i = False
			fascia = False
		u,d,g,p,k = somministrazioni(somministrate,reg=reg,fascia=i,forn=forn,data1=data1,data2=data2)
		t,tv = pop(plat,reg=reg,fascia=i)
		som1 += u
		som2 += d
		somJ += g
		sompre += p
		sompreJ += k
		po += t
		pov += tv
			
	cons,consJ = consegne(distribuite,reg=reg,forn=forn)

	if forn == "Janssen":
		somJ = som1
	
	if fascia:
		if len(fascia.split()) == 1:
			string += "\nFascia " + fascia
	else:
		if vac:
			string += "\nPopolazione vaccinabile"
			po = pov
		else:
			string += "\nPopolazione generale"
	string += "\n"
	
	if mancanti:
		string += "\nNon vaccinati\n" + bar(po-som1-somJ,po)
		string += "\nNon immunizzati completamente\n" + bar(po-som2-somJ+sompreJ,po)
		return string
		
	
	if forn == False or forn != "Janssen":
		string += "\nVaccinati con almeno 1 dose\n" + bar(som1+somJ,po,nextended=True)	
	string += "\nCompletamente immunizzati\n" + bar(som2+somJ-sompreJ,po,nextended=True)
	if sompre != 0:
		string += "\nGuariti completamente immunizzati\n" + bar(sompre,po)

	if not fascia:
		somm_dosi_aggiuntive = somm_d_a(somministrate,reg=reg,forn=forn,data1=data1,data2=data2)
		if somm_dosi_aggiuntive != 0:
			string += "\nDose aggiuntiva su platea immunocompromessi\n" + bar(somm_dosi_aggiuntive,platea_d_a(platea_dose_aggiuntiva,reg=reg))
	else:
		somm_dosi_aggiuntive = 0
		
	if forn != "Janssen":
		if data1 == False:
			string += "\nCompletamente immunizzati su almeno 1 dose\n" + bar(som2+somJ-sompreJ,som1+somJ)
		if forn == False:
			string += "\nCompletamente vaccinati con J&J\n" + bar(somJ,po)
		if data1:
			string += "\nSomministrazioni totali su popolazione\n" + bar(som1+som2+somJ+somm_dosi_aggiuntive,po)
	
	if fascia == False and data1 == False:	
		if forn == "Janssen":
			somJ = sompre
		string += "\nDosi somministrate su consegnate\n" + bar(som1+som2+somJ-sompre+somm_dosi_aggiuntive,cons+consJ)
	
	return string
	
def vaccinifascia(string,reg,forn,data1,data2,prime,plat):
	if plat == "0":
		fascia = "12-19 20-29 30-39 40-49 50-59 60-69 70-79 80-89 90+"
	else:
		fascia = "12-19 20-29 30-39 40-49 50-59 60-69 70-79 80+"
	string += "\n"
	for i in fascia.split():
		som1,som2,somJ,sompre,sompreJ = somministrazioni(somministrate,reg=reg,fascia=i,forn=forn,data1=data1,data2=data2)
		po, _ = pop(plat,reg=reg,fascia=i)
		if prime:
			string += "\nVaccinati con almeno 1 dose fascia " + i + "\n" + bar(som1+somJ,po,nextended=True)
		else:
			if forn == "Janssen":
				somJ = som1
			string += "\nCompletamente immunizzati fascia " + i + "\n" + bar(som2+somJ-sompreJ,po,nextended=True)
	return string

def sommfascia(string,reg,forn,data1,data2,plat):
	if plat == "0":
		fascia = "12-19 20-29 30-39 40-49 50-59 60-69 70-79 80-89 90+"
	else:
		fascia = "12-19 20-29 30-39 40-49 50-59 60-69 70-79 80+"
	s=[]
	for i in fascia.split():
		som1,som2,somJ,sompre,sompreJ = somministrazioni(somministrate,reg=reg,fascia=i,forn=forn,data1=data1,data2=data2)
		s.append(som1+som2+somJ-sompre)
		
	string += "\n"
	k=0
	for i in fascia.split():
		string += "\nSomministrazioni fascia " + i + " su totale\n" + bar(s[k],sum(s))
		k+=1
		
	return string
	
def fasciavaccini(string,reg,fascia,data1,data2,vac,plat):
	forn =["Pfizer/BioNTech","Moderna","Vaxzevria (AstraZeneca)","Janssen"]
	string +="\n"
	
	if fascia == "0":
		po,pov = pop(plat,reg=reg)
		if vac:
			po = pov
		for i in forn:
			som1,_,_,_,_=somministrazioni(somministrate,reg=reg,fascia=False,forn=i,data1=data1,data2=data2)
			string += "\nQuota di vaccinati con " + i + "\n" + bar(som1,po)
		return string
	data=[]
	popol=[]
	
	for i in forn:
		s=[]
		for k in fascia.split():
			som1,_,_,_,_=somministrazioni(somministrate,reg=reg,fascia=k,forn=i,data1=data1,data2=data2)
			s.append(som1)
		data.append(s)
		
	for k in fascia.split():	
		po,_ = pop(plat,reg=reg,fascia=k)
		popol.append(po)
	po=sum(popol)
	tot=0
	k=0
	for i in forn:
		string += "\nQuota di vaccinati con " + i + "\n" + bar(sum(data[k]),po)
		k+=1

	return string
	
def button(update,_: CallbackContext):
	query = update.callback_query
	
	if len(query.data.split(",")[1]) > 3 or len(query.data.split(",")) != 6:
		try:
			query.edit_message_text(text="Questa finestra è stata chiusa a causa di un aggiornamento del bot, richiamare /vaccinati per poter continuare ad usarlo.")
			return
		except telegram.error.BadRequest:
			return
			
	if query.data[:1] != "V" and query.data[:1] != "F" and query.data[:1] != "R" and query.data[:1] != "D" and query.data[:1] != "A" and query.data != "Chiudi":
		if query.data[:1] != "v" and query.data[:1] != "f" and query.data[:1] != "r" and query.data[:1] != "d" and query.data[:1] != "t" and query.data[:1] != "l" and query.data[:1] != "a" and query.data[:1] != "p":
			inf = query.data
		else:
			if query.data[:1] == "a":
				forceupd()
			inf = query.data[1:]
		if len(query.data.split(",")[3]) != 4 and len(query.data.split(",")[3]) != 6 and len(query.data.split(",")[4]) != 4 and len(query.data.split(",")[4]) != 6:
			try:
				float(inf[:1])
			except ValueError:
				segno = inf[:1]
				inf = inf[1:]
				
			if inf.split(",")[5] == "0" and inf.split(",")[0] == "80+":
				inf = change(inf,0,"80-89",False)
			elif inf.split(",")[5] == "1" and ( inf.split(",")[0] == "80-89" or inf.split(",")[0] == "90+" ):
				inf = change(inf,0,"80+",False)
			
			if 'segno' in locals():
				inf = segno + inf

			if query.data[:1] != "a" and query.data[:1] != "p":
				string = fascia(inf)
			elif query.data[:1] == "p":
				string = istat21_show(query.data.split(",")[1])
		else:
			if len(query.data.split(",")[3]) == 4:
				string = "Selezione Mese Data1"
			if len(query.data.split(",")[3]) == 6:
				string = "Selezione Giorno Data1"
			if len(query.data.split(",")[4]) == 4:
				string = "Selezione Mese Data2"
			if len(query.data.split(",")[4]) == 6:
				string = "Selezione Giorno Data2"
		if inf[:1] == "-" or inf[:1] == "+" or inf[:1] == "*" or inf[:1] == "%" or inf[:1] == "&" or inf[:1] == "?":
			inf = inf[1:]

	else:
		if query.data[:1] != "D" and query.data != "Chiudi" and query.data[:1] != "A":
			string = fascia(query.data[1:])
		if query.data[1:2] == "-" or query.data[1:2] == "*" or query.data[1:2] == "+" or query.data[1:2] == "%" or query.data[1:2] == "&" or query.data[1:2] == "?":
			inf = query.data[2:]
		else:
			inf = query.data[1:]
	
	if query.data[:1] == "A" or query.data[:1] == "a":
		string = "Aggiornato al " + agg

	if query.data[1:2] == "-" or query.data[:1] == "-":
		infR1 = "r-"
		segno = "-"
	elif query.data[1:2] == "*" or query.data[:1] == "*":
		infR1 = "r*"
		segno = "*"
	elif query.data[1:2] == "+" or query.data[:1] == "+":
		infR1 = "r+"
		segno = "+"
	elif query.data[1:2] == "%" or query.data[:1] == "%":
		infR1 = "r%"
		segno = "%"
	elif query.data[1:2] == "&" or query.data[:1] == "&":
		infR1 = "r&"
		segno = "&"
	elif query.data[1:2] == "?" or query.data[:1] == "?":
		infR1 = "r?"
		segno = "?"
	else:
		infR1="r"
		segno = ""
	
	if segno == "?" and query.data[:1] != "r":
		segno = ""
		
	if query.data[:1] == "D":
		string = "Selezionando solo Data1 si visualizzeranno solo i dati del giorno selezionato.\nInserendo anche Data2 si visualizzeranno i dati fra i due giorni.\nData2 può essere selezionato solo dopo Data1."

	query.answer()
	
	
	
	if query.data[:1] == "F" or query.data[:1] == "f":
		if query.data.split(",")[3] == "0":
			if segno != "*" and segno != "-":
				segno = ""
		if segno != "*":
			if segno != "-":
				if query.data.split(",")[3] == "0":
					sufascia = [
					telegram.InlineKeyboardButton("Indietro", callback_data=inf),
					telegram.InlineKeyboardButton("Non immunizzati", callback_data="f-" + inf),
					telegram.InlineKeyboardButton("Vaccini usati su fascia", callback_data='f*' + inf),
					]
				else:
					sufascia = [
					telegram.InlineKeyboardButton("Indietro", callback_data=inf),
					telegram.InlineKeyboardButton("Vaccini usati su fascia", callback_data='f*' + inf),
					]
			else:
				sufascia = [
				telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
				telegram.InlineKeyboardButton("Immunizzati", callback_data="f" + inf),
				]
		else:
			sufascia = [
			telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data='f' + inf),
			]
		if query.data.split(",")[5] == "0":
			over70 = [
			telegram.InlineKeyboardButton("70-79", callback_data='f' + segno + change(inf,0,"70-79",False)),
			telegram.InlineKeyboardButton("80-89", callback_data='f' + segno + change(inf,0,"80-89",False)),
			telegram.InlineKeyboardButton("90+", callback_data='f' + segno + change(inf,0,"90+",False)),
			]
			
			plat = [
			telegram.InlineKeyboardButton("Popolazione generale", callback_data='f' + segno + change(inf,0,"0",False)), 
			telegram.InlineKeyboardButton("Popolazione vaccinabile", callback_data='f' + segno + change(inf,0,"1",False)),
			]
		else:
			over70 =[
			telegram.InlineKeyboardButton("70-79", callback_data='f' + segno + change(inf,0,"70-79",False)),
			telegram.InlineKeyboardButton("80+", callback_data='f' + segno + change(inf,0,"80+",False)),
			telegram.InlineKeyboardButton("Over 12", callback_data='f' + segno + change(inf,0,"1",False))
			]
			
			plat = []

		keyboard = [
		[
			telegram.InlineKeyboardButton("12-19", callback_data='f' + segno + change(inf,0,"12-19",False)),
			telegram.InlineKeyboardButton("20-29", callback_data='f' + segno + change(inf,0,"20-29",False)),
			telegram.InlineKeyboardButton("30-39", callback_data='f' + segno + change(inf,0,"30-39",False)),
		],
		[
			telegram.InlineKeyboardButton("40-49", callback_data='f' + segno + change(inf,0,"40-49",False)),
			telegram.InlineKeyboardButton("50-59", callback_data='f' + segno + change(inf,0,"50-59",False)),
			telegram.InlineKeyboardButton("60-69", callback_data='f' + segno + change(inf,0,"60-69",False)),
		],
			over70,
		[
			telegram.InlineKeyboardButton("Over 50", callback_data='f' + segno + change(inf,0,"50",False)),
			telegram.InlineKeyboardButton("Under 50", callback_data='f' + segno + change(inf,0,"49",False)),
			telegram.InlineKeyboardButton("Under 30", callback_data='f' + segno + change(inf,0,"30",False)),
		],
			plat,
			sufascia,
		[
			telegram.InlineKeyboardButton("Chiudi", callback_data="Chiudi"),
		],
		]
	
	elif query.data[:1] == "V" or query.data[:1] == "v":
		if segno == "+":
			sommfascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data="v" + inf),
			]
		elif segno == "%":
			sommfascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data="v" + inf),
			telegram.InlineKeyboardButton("Completamente immunizzati", callback_data="v&" + inf),
			]
		elif segno == "&":
			sommfascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data="v" + inf),
			telegram.InlineKeyboardButton("Almeno una dose", callback_data="v%" + inf),
			]
		else:
			sommfascia = [
			telegram.InlineKeyboardButton("Somministrazioni per fascia", callback_data="v+" + inf),
			telegram.InlineKeyboardButton("Vaccini per fascia", callback_data="v%" + inf),
			]
			
		keyboard = [
		[
			telegram.InlineKeyboardButton("Pfizer", callback_data="v" + segno + change(inf,2,"Pfizer",False)),
			telegram.InlineKeyboardButton("Moderna", callback_data="v" + segno + change(inf,2,"Moderna",False)),
		],
		[
			telegram.InlineKeyboardButton("Astrazeneca", callback_data="v" + segno + change(inf,2,"Az",False)),
			telegram.InlineKeyboardButton("Janssen", callback_data="v" + segno + change(inf,2,"J&J",False)),
		],
		[
			telegram.InlineKeyboardButton("Tutti i vaccini", callback_data="v" + segno + change(inf,2,"0",False)),
		],
			sommfascia,
		[
			telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
			telegram.InlineKeyboardButton("Chiudi", callback_data="Chiudi"),
		],
		]
		
	elif query.data[:1] == "R" or query.data[:1] == "r" or query.data[:1] == "p":
	
		if segno == "*" or segno == "+":
			sufascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data='r' + inf),
			]
			sufascia2 = []
		elif segno == "-":
			sufascia = [
			telegram.InlineKeyboardButton("Immunizzati", callback_data="r" + inf),
			]
			sufascia2 = []
		elif segno == "%":
			sufascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data="r" + inf),
			telegram.InlineKeyboardButton("Completamente immunizzati", callback_data="r&" + inf),
			]
			sufascia2 = []
		elif segno == "&":
			sufascia = [
			telegram.InlineKeyboardButton("Visualizzazione normale", callback_data="r" + inf),
			telegram.InlineKeyboardButton("Almeno una dose", callback_data="r%" + inf),
			]
			sufascia2 = []
		elif segno == "?":
			sufascia = [
			telegram.InlineKeyboardButton("Somministrazioni per fascia", callback_data="r+" + inf),
			telegram.InlineKeyboardButton("Vaccini per fascia", callback_data="r%" + inf),
			]
			sufascia2 = [
			telegram.InlineKeyboardButton("Non immunizzati", callback_data="r-" + inf),
			telegram.InlineKeyboardButton("Vaccini usati su fascia", callback_data='r*' + inf),
			]
		else:
			sufascia = []
			sufascia2 = []
		
		if query.data[:1] == "p":
			istat = [
			telegram.InlineKeyboardButton("Emilia Romagna", callback_data=infR1 + change(inf,1,"EMR",False)),
			telegram.InlineKeyboardButton("Italia", callback_data=infR1 + change(inf,1,"0",False)),
			]
		else:
			istat = [
			telegram.InlineKeyboardButton("Emilia Romagna", callback_data=infR1 + change(inf,1,"EMR",False)),
			telegram.InlineKeyboardButton("Dati ISTAT21", callback_data="p" + inf),
			telegram.InlineKeyboardButton("Italia", callback_data=infR1 + change(inf,1,"0",False)),
			]
			
		if segno == "":
			end = [
				telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
				telegram.InlineKeyboardButton("Funzioni", callback_data="r?" + inf),
				telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),		
			]
		else:				
			end = [
				telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
				telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),		
			]
			
		keyboard = [
		[
			telegram.InlineKeyboardButton("Abruzzo", callback_data=infR1 + change(inf,1,"ABR",False)),
			telegram.InlineKeyboardButton("Basilicata", callback_data=infR1 + change(inf,1,"BAS",False)),
			telegram.InlineKeyboardButton("Calabria", callback_data=infR1 + change(inf,1,"CAL",False)),
			telegram.InlineKeyboardButton("Campania", callback_data=infR1 + change(inf,1,"CAM",False)),
		],
		[
			telegram.InlineKeyboardButton("Friuli", callback_data=infR1 + change(inf,1,"FVG",False)),
			telegram.InlineKeyboardButton("Lazio", callback_data=infR1 + change(inf,1,"LAZ",False)),
			telegram.InlineKeyboardButton("Liguria", callback_data=infR1 + change(inf,1,"LIG",False)),
			telegram.InlineKeyboardButton("Lombardia", callback_data=infR1 + change(inf,1,"LOM",False)),
		],
		[
			telegram.InlineKeyboardButton("Marche", callback_data=infR1 + change(inf,1,"MAR",False)),
			telegram.InlineKeyboardButton("Molise", callback_data=infR1 + change(inf,1,"MOL",False)),
			telegram.InlineKeyboardButton("Bolzano", callback_data=infR1 + change(inf,1,"PAB",False)),
			telegram.InlineKeyboardButton("Trento", callback_data=infR1 + change(inf,1,"PAT",False)),
		],
		[
			telegram.InlineKeyboardButton("Piemonte", callback_data=infR1 + change(inf,1,"PIE",False)),
			telegram.InlineKeyboardButton("Puglia", callback_data=infR1 + change(inf,1,"PUG",False)),
			telegram.InlineKeyboardButton("Sardegna", callback_data=infR1 + change(inf,1,"SAR",False)),
			telegram.InlineKeyboardButton("Sicilia", callback_data=infR1 + change(inf,1,"SIC",False)),
		],
		[
			telegram.InlineKeyboardButton("Toscana", callback_data=infR1 + change(inf,1,"TOS",False)),
			telegram.InlineKeyboardButton("Umbria", callback_data=infR1 + change(inf,1,"UMB",False)),
			telegram.InlineKeyboardButton("Aosta", callback_data=infR1 + change(inf,1,"VDA",False)),
			telegram.InlineKeyboardButton("Veneto", callback_data=infR1 + change(inf,1,"VEN",False)),
		],
		istat,
		sufascia,
		sufascia2,
		end,
		]
	elif query.data[:1] == "D" or query.data[:1] == "l":
		if query.data.split(",")[3] == "0":
			dat1 = [
				telegram.InlineKeyboardButton("Data1", callback_data='d' + segno + inf),
				]
			dat2 = []	
		else:
			dat1 = [
				telegram.InlineKeyboardButton("Data1", callback_data='d' + segno + inf),
				telegram.InlineKeyboardButton("Data2", callback_data='t' + segno + inf),
				]
			if query.data.split(",")[4] == "0":
				dat2 = [
					telegram.InlineKeyboardButton("Rimuovi Data1", callback_data=segno + change(inf,3,"0",False)),
					]
			else:
				dat2 = [
					telegram.InlineKeyboardButton("Rimuovi Data2", callback_data=segno + change(inf,4,"0",False)),
					telegram.InlineKeyboardButton("Rimuovi Data1 e Data2", callback_data=segno + change(change(inf,3,"0",False),4,"0",False)),	
					]
		
		keyboard = [
		dat1,
		dat2,	
		[
			telegram.InlineKeyboardButton("Indietro", callback_data=segno + inf),
			telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
		],
		]
	elif query.data[:1] == "d" or query.data[:1] == "t":
		if len(query.data.split(",")[3]) == 4 or len(query.data.split(",")[4]) == 4:
			if len(query.data.split(",")[3]) == 4:
				pos = 3
			else:
				pos = 4
			if query.data.split(",")[pos] == "2020":
				keyboard = [
				[
					telegram.InlineKeyboardButton("Dicembre", callback_data='d' + segno + change(inf,pos,"12",True)),
				],
				[
					telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
				],
				]
			else:
				keyboard = [
				[
					telegram.InlineKeyboardButton("Gennaio", callback_data='d' + segno + change(inf,pos,"01",True)),
					telegram.InlineKeyboardButton("Febbraio", callback_data='d' + segno + change(inf,pos,"02",True)),
					telegram.InlineKeyboardButton("Marzo", callback_data='d' + segno + change(inf,pos,"03",True)),
					telegram.InlineKeyboardButton("Aprile", callback_data='d' + segno + change(inf,pos,"04",True)),
				],	
				[
					telegram.InlineKeyboardButton("Maggio", callback_data='d' + segno + change(inf,pos,"05",True)),
					telegram.InlineKeyboardButton("Giugno", callback_data='d' + segno + change(inf,pos,"06",True)),
					telegram.InlineKeyboardButton("Luglio", callback_data='d' + segno + change(inf,pos,"07",True)),
					telegram.InlineKeyboardButton("Agosto", callback_data='d' + segno + change(inf,pos,"08",True)),
				],
				[
					telegram.InlineKeyboardButton("Settembre", callback_data='d' + segno + change(inf,pos,"09",True)),
					telegram.InlineKeyboardButton("Ottobre", callback_data='d' + segno + change(inf,pos,"10",True)),
					telegram.InlineKeyboardButton("Novembre", callback_data='d' + segno + change(inf,pos,"11",True)),
					telegram.InlineKeyboardButton("Dicembre", callback_data='d' + segno + change(inf,pos,"12",True)),
				],
				[
					telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
				],
				]
		elif len(query.data.split(",")[3]) == 6 or len(query.data.split(",")[4]) == 6:
			if len(query.data.split(",")[3]) == 6:
				pos = 3
			else:
				pos = 4
			if query.data.split(",")[pos] == "202012":
				keyboard = [
				[
					telegram.InlineKeyboardButton("27", callback_data='l' + segno + change(inf,pos,"27",True)),
					telegram.InlineKeyboardButton("28", callback_data='l' + segno + change(inf,pos,"28",True)),
					telegram.InlineKeyboardButton("29", callback_data='l' + segno + change(inf,pos,"29",True)),
					telegram.InlineKeyboardButton("30", callback_data='l' + segno + change(inf,pos,"30",True)),
					telegram.InlineKeyboardButton("31", callback_data='l' + segno + change(inf,pos,"31",True)),
				],
				[
					telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
				],
				]
			else:
				if query.data.split(",")[pos][-2:] == "01" and query.data.split(",")[pos][-2:] == "03" and query.data.split(",")[pos][-2:] == "05" and query.data.split(",")[pos][-2:] == "07" and query.data.split(",")[pos][-2:] == "08" and query.data.split(",")[pos][-2:] == "10" and query.data.split(",")[pos][-2:] == "12":
					giorni1 = [
						telegram.InlineKeyboardButton("26", callback_data='l' + segno + change(inf,pos,"26",True)),
						telegram.InlineKeyboardButton("27", callback_data='l' + segno + change(inf,pos,"27",True)),
						telegram.InlineKeyboardButton("28", callback_data='l' + segno + change(inf,pos,"28",True)),
						telegram.InlineKeyboardButton("29", callback_data='l' + segno + change(inf,pos,"29",True)),
						telegram.InlineKeyboardButton("30", callback_data='l' + segno + change(inf,pos,"30",True)),
						]
					giorni2 = [
						telegram.InlineKeyboardButton("31", callback_data='l' + segno + change(inf,pos,"31",True)),
						telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
						]
				if query.data.split(",")[pos][-2:] == "02" and query.data.split(",")[pos][:2] == 2020:
					giorni1 = [
						telegram.InlineKeyboardButton("26", callback_data='l' + segno + change(inf,pos,"26",True)),
						telegram.InlineKeyboardButton("27", callback_data='l' + segno + change(inf,pos,"27",True)),
						telegram.InlineKeyboardButton("28", callback_data='l' + segno + change(inf,pos,"28",True)),
						telegram.InlineKeyboardButton("29", callback_data='l' + segno + change(inf,pos,"29",True)),
						]
					giorni2 = [
						telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
						]
				if query.data.split(",")[pos][-2:] == "02":
					giorni1 = [
						telegram.InlineKeyboardButton("26", callback_data='l' + segno + change(inf,pos,"26",True)),
						telegram.InlineKeyboardButton("27", callback_data='l' + segno + change(inf,pos,"27",True)),
						telegram.InlineKeyboardButton("28", callback_data='l' + segno + change(inf,pos,"28",True)),
						]
					giorni2 = [
						telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
						]
				else:
					giorni1 = [
						telegram.InlineKeyboardButton("26", callback_data='l' + segno + change(inf,pos,"26",True)),
						telegram.InlineKeyboardButton("27", callback_data='l' + segno + change(inf,pos,"27",True)),
						telegram.InlineKeyboardButton("28", callback_data='l' + segno + change(inf,pos,"28",True)),
						telegram.InlineKeyboardButton("29", callback_data='l' + segno + change(inf,pos,"29",True)),
						telegram.InlineKeyboardButton("30", callback_data='l' + segno + change(inf,pos,"30",True)),
						]
					giorni2 = [
						telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
						]
				
				keyboard = [
				[
					telegram.InlineKeyboardButton("1", callback_data='l' + segno + change(inf,pos,"01",True)),
					telegram.InlineKeyboardButton("2", callback_data='l' + segno + change(inf,pos,"02",True)),
					telegram.InlineKeyboardButton("3", callback_data='l' + segno + change(inf,pos,"03",True)),
					telegram.InlineKeyboardButton("4", callback_data='l' + segno + change(inf,pos,"04",True)),
					telegram.InlineKeyboardButton("5", callback_data='l' + segno + change(inf,pos,"05",True)),
				],
				[
					telegram.InlineKeyboardButton("6", callback_data='l' + segno + change(inf,pos,"06",True)),
					telegram.InlineKeyboardButton("7", callback_data='l' + segno + change(inf,pos,"07",True)),
					telegram.InlineKeyboardButton("8", callback_data='l' + segno + change(inf,pos,"08",True)),
					telegram.InlineKeyboardButton("9", callback_data='l' + segno + change(inf,pos,"09",True)),
					telegram.InlineKeyboardButton("10", callback_data='l' + segno + change(inf,pos,"10",True)),
				],
				[
					telegram.InlineKeyboardButton("11", callback_data='l' + segno + change(inf,pos,"11",True)),
					telegram.InlineKeyboardButton("12", callback_data='l' + segno + change(inf,pos,"12",True)),
					telegram.InlineKeyboardButton("13", callback_data='l' + segno + change(inf,pos,"13",True)),
					telegram.InlineKeyboardButton("14", callback_data='l' + segno + change(inf,pos,"14",True)),
					telegram.InlineKeyboardButton("15", callback_data='l' + segno + change(inf,pos,"15",True)),
				],
				[
					telegram.InlineKeyboardButton("16", callback_data='l' + segno + change(inf,pos,"16",True)),
					telegram.InlineKeyboardButton("17", callback_data='l' + segno + change(inf,pos,"17",True)),
					telegram.InlineKeyboardButton("18", callback_data='l' + segno + change(inf,pos,"18",True)),
					telegram.InlineKeyboardButton("19", callback_data='l' + segno + change(inf,pos,"19",True)),
					telegram.InlineKeyboardButton("20", callback_data='l' + segno + change(inf,pos,"20",True)),
				],
				[
					telegram.InlineKeyboardButton("21", callback_data='l' + segno + change(inf,pos,"21",True)),
					telegram.InlineKeyboardButton("22", callback_data='l' + segno + change(inf,pos,"22",True)),
					telegram.InlineKeyboardButton("23", callback_data='l' + segno + change(inf,pos,"23",True)),
					telegram.InlineKeyboardButton("24", callback_data='l' + segno + change(inf,pos,"24",True)),
					telegram.InlineKeyboardButton("25", callback_data='l' + segno + change(inf,pos,"25",True)),
				],
				giorni1,
				giorni2,
				]

		else:
			if query.data[:1] == "d":
				prefix = "d"
				pos = 3
			else:
				prefix = "t"
				pos = 4
			keyboard = [
			[
				telegram.InlineKeyboardButton("2020", callback_data=prefix + segno + change(inf,pos,"2020",False)),
				telegram.InlineKeyboardButton("2021", callback_data=prefix + segno + change(inf,pos,"2021",False)),
			],	
			[
				telegram.InlineKeyboardButton("Annulla", callback_data="D" + inf),
				telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
			],
			]
	elif query.data[:1] == "A" or query.data[:1] == "a":
		if cid != query.message.chat.id:
			keyboard = [
			[
					telegram.InlineKeyboardButton("Indietro", callback_data=query.data[1:]),
			],
			]
		else:
			keyboard = [
			[
					telegram.InlineKeyboardButton("Indietro", callback_data=query.data[1:]),
					telegram.InlineKeyboardButton("Aggiorna", callback_data="a" + query.data[1:]),
			],
			]
		
	elif query.data != "Chiudi":
		if query.data[:1] == "*" or query.data[:1] == "-":
			tastiera = [
				telegram.InlineKeyboardButton("Fascia", callback_data='F' + segno + inf),
				telegram.InlineKeyboardButton("Regione", callback_data='R' + segno + inf),
			]
		elif query.data[:1] == "+" or query.data[:1] == "&" or query.data[:1] == "%":
			tastiera = [
				telegram.InlineKeyboardButton("Vaccino", callback_data='V' + segno + inf),
				telegram.InlineKeyboardButton("Regione", callback_data='R' + segno + inf),
			]
		else:
			tastiera = [
				telegram.InlineKeyboardButton("Fascia", callback_data='F' + segno + inf),
				telegram.InlineKeyboardButton("Vaccino", callback_data='V' + segno + inf),
				telegram.InlineKeyboardButton("Regione", callback_data='R' + segno + inf),
			]
		if query.data[:1] != "-":
			if inf.split(",")[3] == (date.datetime.today() - date.timedelta(days=1)).strftime('%Y%m%d'):
				dat = [
				telegram.InlineKeyboardButton("Data", callback_data='D' + segno + inf),
				]
			else:
				dat = [
				telegram.InlineKeyboardButton("Data", callback_data='D' + segno + inf),
				telegram.InlineKeyboardButton("Ieri", callback_data=segno + change(change(inf,3,(date.datetime.today() - date.timedelta(days=1)).strftime('%Y%m%d'),False),4,"0",False)),
				]
		else:
			dat = []
		
		if query.data.split(",")[5] == "0":
			plat = telegram.InlineKeyboardButton("Usa PLATEA", callback_data=segno + change(inf,5,"1",False))
		else:
			plat = telegram.InlineKeyboardButton("Usa ISTAT21", callback_data=segno + change(inf,5,"0",False))
			
		keyboard = [
		tastiera,
		[
			telegram.InlineKeyboardButton("Reset popolazione vaccinabile", callback_data=change(change(change(inf,0,"1",False),1,"0",False),2,"0",False)),
			plat,
		],	
		dat,
		[
			telegram.InlineKeyboardButton("Ultimo aggiornamento", callback_data='A' + inf),
			telegram.InlineKeyboardButton("Chiudi", callback_data='Chiudi'),
		],
		]

	if query.data[:1] != "D" and query.data != "Chiudi" and query.data[:1] != "p":
		string += "\nUltimo controllo alle: " + agg2

	try:
		if query.data == "Chiudi":
			query.edit_message_text(text=query.message.text)
		else:
			reply_markup = telegram.InlineKeyboardMarkup(keyboard)
			query.edit_message_text(text=f"{string}", reply_markup=reply_markup, parse_mode='Markdown')
	except telegram.error.BadRequest:
		return
		
def change(inf,pos,campo,add):
	k=0
	info=""
	for i in inf.split(","):
		if k == pos and add:
			info += inf.split(",")[k]
		if k == pos:
			info += campo
		else:
			info += inf.split(",")[k]
		if k != 5:
			info += ","
		k += 1
	return info
	
def extract(text, p):
	return text.split()[p].strip()
	
def main():
	upd = Updater(TOKEN, use_context=True)
	disp = upd.dispatcher

	locale.setlocale(locale.LC_ALL, "it_IT.utf8")

	disp.add_handler(CommandHandler("help", help))
	disp.add_handler(CommandHandler("segnalazione", segnalazione))
	disp.add_handler(CommandHandler("vaccinati", vaccinati))
	disp.add_handler(CommandHandler("start", vaccinati))
	disp.add_handler(CallbackQueryHandler(button))

	upd.start_polling()

	upd.idle()
   
def tab():
	global somministrate
	global distribuite
	global file_platea
	global dati_istat21
	global platea_dose_aggiuntiva
	global agg
	global agg2
	agg = ""
	agg2 = ""
	dati_istat21 = pd.read_csv('https://raw.githubusercontent.com/Aldo97/VacciniBot/main/istat21.csv')
	while True:
		if agg != lastupd():
			somministrate = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/somministrazioni-vaccini-latest.csv')
			distribuite = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/consegne-vaccini-latest.csv')
			file_platea = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/platea.csv')
			platea_dose_aggiuntiva = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/platea-dose-aggiuntiva.csv')
			agg = lastupd()
		agg2 = date.datetime.now().strftime("%H:%M:%S")
		time.sleep(90*60)
		
def forceupd():
	global somministrate
	global distribuite
	global file_platea
	global platea_dose_aggiuntiva
	global agg
	global agg2	

	somministrate = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/somministrazioni-vaccini-latest.csv')
	distribuite = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/consegne-vaccini-latest.csv')
	file_platea = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/platea.csv')
	platea_dose_aggiuntiva = pd.read_csv('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/platea-dose-aggiuntiva.csv')
	agg = lastupd()
	agg2 = date.datetime.now().strftime("%H:%M:%S")
		
def lastupd():
	ultimo = requests.get('https://raw.githubusercontent.com/italia/covid19-opendata-vaccini/master/dati/last-update-dataset.json').json()["ultimo_aggiornamento"]
	return ultimo[8:10] + "/" + ultimo[5:7] + "/" + ultimo[:4] + " alle " + ultimo[11:19]
    
if __name__ == '__main__':
	b = threading.Thread(name='backgroud', target=tab)
	b.start()

	main()
