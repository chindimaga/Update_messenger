#importing required libraries
import datetime
import json
import requests
import logging
from bs4 import BeautifulSoup
from tabulate import tabulate
#importing slack client (another.py file from same folder)
from slack_client import slacker
#logging to check the status of each part of code regularly
FORMAT = '[%(asctime)-15s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, filename='bot.log', filemode='a')
#URL from which the data needs to be scraped
URL = 'https://www.mohfw.gov.in/'
#header for table
SHORT_HEADERS = ['Sno', 'State','Infected','Cured','Deaths']
FILE_NAME = 'corona_india_data.json'
#helper
extract_contents = lambda row: [x.text.replace('\n', '') for x in row]
#required functions
# 1.
def scrape():
    response = requests.get(URL).content
    soup = BeautifulSoup(response, 'html.parser')
    header = extract_contents(soup.tr.find_all('th'))

    stats = []
    all_rows = soup.find_all('tr')
    for row in all_rows:
        stat = extract_contents(row.find_all('td'))
        if stat:
            if len(stat) != len(header):
                # last row
                stat = ['', *stat]
                stats.append(stat)
            else: 
                stats.append(stat)
    return stats
# 2.
def save(x):
    with open(FILE_NAME, 'w') as f:
        json.dump(x, f)
# 3.
def load():
    res = {}
    try:
        with open(FILE_NAME, 'r') as f:
            res = json.load(f)
    except:
        #if the previous data is not found it automatically reinitialises and sends a slack message
        stats = scrape()
        res = {x[1]: {current_time: x[2:], 'latest': x[2:]} for x in stats}
        save(res)
        table = tabulate(stats, headers=SHORT_HEADERS, tablefmt='psql')
        slack_text = f'Database not found \nCoronaVirus Summary for India (New Database):\n```{table}```'
        slacker()(slack_text)
    return res
    
# actual code
if __name__ == '__main__':   
    # getting the current date and time 
    current_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    #initials the list info(to append the messages to be sent)
    info = []
    try:  
        changed = False
        # dataloaded from the database
        past_data = load()
        # data scraped from web
        stats = scrape()
        cur_data = {x[1]: {current_time: x[2:]} for x in stats}
        #checking if the data is changed
        for state in cur_data:
            if state not in past_data:
                # virus has been detected in a new state so add the new state and its info in database
                info.append(f'NEW_STATE {state} got corona virus: {cur_data[state][current_time]}')
                past_data[state] = {current_time: cur_data[state][current_time], 'latest': cur_data[state][current_time]}
                changed = True
            else:
                past = past_data[state]['latest']
                cur = cur_data[state][current_time]
                if past != cur:
                    #the parameters of the state has been changed so update your data base
                    changed = True
                    info.append(f'Change for {state}: {past}->{cur}')
                    past_data[state][current_time]=cur_data[state][current_time]
                    past_data[state]['latest']=cur_data[state][current_time]
        #final message to be sent to your slack channel
        events_info = ''
        for event in info:
            # logging.warning(event)
            events_info += '\n - ' + event.replace("'", "")

        if changed:
            #save your updated data and send a message to your slack channel using webhook
            save(past_data)
            table = tabulate(stats, headers=SHORT_HEADERS, tablefmt='psql')
            slack_text = f'CoronaVirus Summary for India:\n{events_info}\n```{table}```'
            slacker()(slack_text)
            
    except Exception as e:
        #if the script has failed log it and send a message to your slack channel that your script has bugs
        logging.exception('Your script has failed. Looks like a new bug xD')
        slacker()(f'Your script has failed. Looks like a new bug xD \n Exception occured: [{e}]')
