import requests
import re
import logging
from bs4 import BeautifulSoup
from pprint import pprint

# ### Uncomment to log http requests results
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

class IdentifierUnusedError (Exception):
	pass

class BlockedRequestError (Exception):
	pass

"""
### Retrieve the forecast page for a location given it's id.
	The location id is just an unsigned integer. It's unknown which is the maximum of this id, but it is know that there are missing ids.

	There are 2 possibl errors:
		- BlockedRequestError: The webserver may block your request if they are too fast. In this case, you need to wait a minute or two.
		- IdentifierUnusedError: If the given ID is not related to a Location, then this error is raised. In this case, you need to change the ID.

	TODO: The two errors are returned with a 403 code. Convert the check for safety and future-proofing
"""
def retrieve_location_page (id):
	url = "http://www.meteoam.it/ta/previsione/{}".format(id)
	raw_page = requests.get(url)

	# ### Checks if your request has been blocked
	if raw_page.content == b"<html><body>\n<h2>\n<p>\n   Non disponi dei permessi necessari per accedere all'oggetto\n   richiesto, oppure l'oggetto non pu&ograve; essere letto dal server.\n</p>\n<p>\nBuona navigazione! <BR>\n#Metweb Staff#\n</p>\n</h2>\n</body></html>\n":
		raise BlockedRequestError( "Your request has been blocked. Please try again in a minute or two. ID: {}".format(id) )

	soup = BeautifulSoup(raw_page.content, "html.parser")
	
	if list( soup.findAll('h1', class_="page-header") )[0] == '<h1 class="page-header">Previsioni per localita</h1>':
		raise IdentifierUnusedError( "The requested ID is not used. ID: {}".format(id) )

	return soup

"""
### Parse the a forecast table in an list dictionary, one per hour.
	Each of the tree available days are placed in a simple table.
	Available days are:
		- today: id='oggi'
		- tomorrow: id='domani'
		- after tomorrow: id='tregiorni'


	- time = The hour in 24H format, located in a TH tag at the start of the row
	- weather = An IMG tag inside a TD tag, with the weather condition as alt and as 'title' attribute
	- precipitation = Inside a TD tag, the precipitation probability. When it's not available, this is converted from '-' to None
	- temperature = Inside a TG tag
	- humidity = Inside a TG tag
	- wind_speed = It's inside a SPAN tag, which is inside another SPAN tag (which contains the direction), which is inside a TD tag. Contains the wind speed in km/h
	- wind_direction = Located as an attribute inside the SPAN tag containing the wind_speed span.It's the direction in either a 2 letter cardinal direction or None for when there is no data or it's variable
	- gusts = Inside a SPAN tag which is inside a TH tag. gusts speed in km/h
"""
def parse_table (table):
	rows = table.tbody.findAll('tr')
	
	results = []

	for row in rows:
		data = row.findAll('td')

		results.append(
			{
				'time': row.findAll('th')[0].text,
				'weather': data[0].img['title'] if data[0].img['title'] != '-' else None,
				'precipitation': data[1].text,
				'temperature': data[2].text,
				'humidity': data[3].text,
				'wind_speed': data[4].span.span.text,
				'wind_direction': data[4].span['class'][0].replace('vento', '') if data[4].span['class'][0].replace('vento', '') != 'Variabile' else None,
				'gusts': data[4].span.text
			}
		)

	return results

"""
### Get location name and region from title
	The region name is located at the end of a h1 tag with the page-header, as a 2 letter code between parentesis.
"""
def get_location_name_and_region (page):
	try:
		location_name = list( page.findAll('h1', class_="page-header") )[0].text.replace("Previsioni Meteorologiche per ", "")
		region = location_name[location_name.find("(")+1:location_name.find(")")]
	except:
		raise Exception("There has been an error with retrieving the right page.")

	return {
		'name_with_region': location_name,
		'region': 'region',
		'name': location_name.replace( "({})".format(region), "" )
	}

"""
### Return the formatted data for a location given it's id.
	It returns a dictionary:
	- requested_id_location = The supplied id
	- location:
		- name_with_region: The name with the region, unmodified from the page
		- region: The region, has a 2 letter code
		- name: The name of the location, withouth the region at the end
	- forecast:
		- today: the result of parse_table on the table of id="oggi"
		- tomorrow: the result of parse_table on the table of id="domani"
		- after_tomorrow: the result of parse_table on the table of id="tregiorni"
"""
def get_location_data (id):
	page = retrieve_location_page(id)

	names = get_location_name_and_region( page )

	today = parse_table( page.find(id="oggi") )
	tomorrow = parse_table( page.find(id="domani") )
	after_tomorrow = parse_table( page.find(id="tregiorni") )

	return {
		'requested_id_location': id,
		'location': names,
		'forecast': {
			'today': today,
			'tomorrow': tomorrow,
			'after_tomorrow': after_tomorrow
		}
	}