#!/usr/bin/env python
#Written for python 2.x using google drive REST api v3 (https://developers.google.com/drive/v3/web/about-sdk)
#This program gets your public and private ip address and compares them everytime it is run. If they have changed since the last time it was run, it creats/updates a file with the new info and uploads it to Google drive
import httplib2
import os
import time
import subprocess
import sys
import re

from apiclient import discovery
from httplib2 import Http
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.discovery import build
from oauth2client import file, client, tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

#global variables
IP_WEBSITE = "http://myip.xname.org" #this is the url i am using to get the public IP
FILENAME = 'IP-Log.txt' #name or path of log file if not in current directory
NUMLOGS = 100 #number of logs to keep before deleting file (to conserve space/prevent the file from getting too big)
SCOPES = 'https://www.googleapis.com/auth/drive.file' #the scope of google drive permissions to grant this application. (https://developers.google.com/drive/v3/web/about-auth)
MANUAL = "FALSE" #switch var to enable manual running regardless if there is a change in ip address. Defualt: "FALSE" set to "TRUE" if you want to run manually

#authorize with REST OAuth 2.0 (If this is the first time running the application should open a google sign in page in your defualt browser)
creds = store.get()
if not creds or creds.invalid:
	flow = client.flow_from_clientsecrets('client_secret.json', scope = SCOPES)
	creds = tools.run_flow(flow, store, flags) \
			if flags else tools.run(flow, store)
DRIVE = build('drive', 'v3', http = creds.authorize(Http())) #create drive api object

def getDriveInfo(): #this method gets the files named 'IP-Log.txt' not in the trash and gets the ID of the newest one by creation date 
	query = "name = 'IP-Log.txt' and trashed = false" #var for easy query input
	res = DRIVE.files().list(q=query, fields = "files(id, name, createdTime)", orderBy = 'createdTime').execute() #request files named 'IP-Log.txt' not in the trash based on query input
	items = res.get('files')#store info in list called items. Make note that API returns lists when searching. 
    	if not items:
		ident = "null" #if no items found id is set to null
   	else:
        	for item in items[0:1]: #get the id, name, and created time of the newest created file. Name and created time are for debugging. 
			name = item['name']
			ident = item['id'] #id var
			createdTime = item['createdTime']
	return ident #return the id of the newest created file named 'IP-Log.txt'

def driveManip(): #either updates an existing file in google drive or or creates a new file if no file exists. 
		ident = getDriveInfo()#get the id of the newest file
		if (ident != "null"): #a file already exists. update it.
			print("A log file already exisits in drive. Updating the log file...")
			metadata = {'name': FILENAME} 
			res = DRIVE.files().update(body=metadata, media_body=FILENAME, fileId = ident).execute()#api call to update file
			if res:
				print('Updated "%s" (%s)' % (FILENAME, res['id'])) #print update success
		else:	
			print("No exsisting log files found in Drive. Creating new file and uploading...") #no existing file was found. create new one
			metadata = {'name': FILENAME}
			res = DRIVE.files().create(body=metadata, media_body=FILENAME).execute() #api call to create new file
			if res:
				print('Uploaded "%s" (%s)' % (FILENAME, res['id'])) #print creation success.



def getip(): #Gets the local IP using the hostname -I method
	command = "hostname -I"
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
	output = proc.stdout.read()
	output = output.replace("\n","")
	return output

def getpubip(): #Gets the public IP by doing a get of the webpage below
	url = "myip.xname.org:80"
	import httplib, urllib
	headers = {"Content-type": "HTML"}
	params = ''
	conn = httplib.HTTPConnection(url)
	conn.request("GET", "/")
	response = conn.getresponse()
	message = response.status, response.reason
	message = str(message) 
	ip = response.read()
	ip = ip.replace("\n","") #get rid of new line character
	return ip

def getOldInfo(filename): #gets the info from the last time the program was run from the log file
	with open (filename, 'a+') as f: #reads file
		lineList = f.readlines()
		f.close

		if (lineList != []): #reads the last line to get the info from the last update logged
			last = lineList[len(lineList)-1]
			numLines = len(lineList)
		else:
			last = "null" #if file is empty set last to null
			numLines = 0
		
		searchStart = last.find("Public IP: ")+11 #search the last log for old public ip
		searchStop = last.find(" | ")
		
		if (searchStart == -1 or searchStop == -1): #if no old public ip from an empty file say no existing logs.
			relevant1 = "No existing logs"
		else:
			relevant1 = last[searchStart:searchStop] #return the old ip address and the number of lines in the file.
	
	return relevant1, numLines

def getNewInfo():
	publicip=getpubip() #get the current public ip
	localip=getip()	#get the current local ip 

	proc = subprocess.Popen("uptime -s", stdout=subprocess.PIPE, shell=True) #get when the last time the computer was turned on
	output1 = proc.stdout.read()
	upSince = output1.replace("\n","")

	command2 = "uptime -p"	#get the current uptime in hours and minutes
	proc = subprocess.Popen(command2, stdout=subprocess.PIPE, shell=True)
	output2 = proc.stdout.read()
	output3 = output2.replace("\n","")
	uptime = output3.replace("up","")

	date = time.strftime('%d/%m/%Y') #get current date and time
	currentTime = time.strftime('%I:%M:%S%p')

	myString = date+" @ "+currentTime+"--Computer has been up since: "+upSince+" which means an uptime of:"+uptime+" [ Public IP: "+publicip+" | Local IP "+localip+"]" #put all the above info into nicely #formatted string
	relevant2 = publicip

	return relevant2, myString #return the full string and the current ip address

def main():
	relevant1, numLines = getOldInfo(FILENAME) #get old info from file
	relevant2, myString = getNewInfo() #get current info

	if(MANUAL == "TRUE"):  #check if the user wants to run manually
		print("'MANUAL' has been set to TRUE so the program will run manually:")
		if (numLines > NUMLOGS): #check if the number of lines in the file is greater than the number of logs to keep. If it is, delete the file on google drive and locally
			ident = getDriveInfo() 
			os.remove(FILENAME)
			DRIVE.files().delete(fileId = ident).execute()
		file = open(FILENAME, 'a+') #create a new local log file or update the existing one if it exists
		file.write(myString + "\n") #write the current info in 'my string' to the file
		print(myString)	#print current info
		print("Saving above info...")
		file.close() #close the file
		driveManip() #run drive manip to either upload new file or update the existing one in drive
		print("-----------------------------------------------------------------------------------------") #print spacer
		option = raw_input("Operation completed, run again? Type 'y' for yes or anything else to quit: ") #ask if user wants to continue manually running.
		if (option != "y"):
			quit() #if they don't want to continue manually running quit
	else:
		if (relevant1 != relevant2): #defualt operation with 'MANUAL' var set to defualt of "FALSE". Will only update logs if there is a change of public ip
			if (numLines > NUMLOGS): #check if the number of lines in the file is greater than the number of logs to keep. If it is, delete the file on google drive and locally
				ident = getDriveInfo()
				os.remove(FILENAME)
				DRIVE.files().delete(fileId = ident).execute()
			file = open(FILENAME, 'a+') #create a new local log file or update the existing one if it exists
			file.write(myString + "\n") #write the current info in 'my string' to the file
			print(myString)	#print current info
			print("Saving above info...")
			file.close() #close the file
			driveManip() #run drive manip to either upload new file or update the existing one in drive
			print("-----------------------------------------------------------------------------------------")
if __name__ == '__main__':
	 while True:
			try:
				main()
				time.sleep(1)
			except:
				print("You canceled the program or an unknown error occured")
				quit()
	
