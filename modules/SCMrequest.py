import time
import sys
import re

import requests
from bs4 import BeautifulSoup

class mItem:
	"Individual item data from SCM"
	def __init__(self, name='', quality='', quantity=0, normal_price=0.0, sale_price=0.0):
		self.name = name
		self.quality = quality
		self.quantity = quantity
		self.normal_price = normal_price
		self.sale_price = sale_price

	def contain_full_information(self):
		if ((self.name != '') and (self.quality != '') and (self.quantity != 0) and
			 (self.normal_price != 0.0) and (self.sale_price != 0.0)):
			return True
		else:
			return False

	def __str__(self):
		return 'name: {0}\nquantity: {1}\nquality: {2}\nnormal_price: {3}\nsale_price: {4}'.format(
			self.name, self.quality, self.quantity, self.normal_price, self.sale_price)



class mSpreadsheet():
	"Handles search & individual get requests & processing"
	def __init__(self, appid=440, parameters=[]):
		# Tags class names for data lookup in results_html
		self.class_names = {'name':['market_listing_item_name',],
						'quantity': ['market_listing_num_listings_qty',],
						'normal_price': ['normal_price',],
						'sale_price': ['sale_price',]}
		self.color2quality = {'#b2b2b2;': 'Normal', 
							'#7d6d00;': 'Unique',
							'#476291;': 'Vintage', 
							'#4d7455;': 'Genuine',
							'#cf6a32;': 'Strange', 
							'#8650ac;': 'Unusual',
							'#38f3ab;': 'Haunted', 
							'#aa0000;': 'Collectors',
							'#fafafa;': 'Decorated', 
							'#70b04a;': 'Community',
							'#a50f79;': 'Valve'}
		self.page_size = 100 # How many items for one page of a render
		self.price_template = re.compile(r'\d+\W+\d{1,2}') # Regex for single request price 
		self.appid = appid # App ID
		self.search_base = 'http://steamcommunity.com/market/search/render/?'
		self.search_delay = 10.0 # Delay for search requests
		self.search_timeout_delay = 61.0 # Delay for search timeout
		self.search_parameters = parameters # Search parameters
		self.search_results = [] # Search results
		self.request_base = 'http://steamcommunity.com/market/priceoverview/?'
		self.request_delay = 2.0 # Delay for single request
		self.request_result = mItem() # Single request result

	def compose_search_address(self, start, count):
		quality_parameters = '&'.join(self.search_parameters)
		address = '{0}start={1}&count={2}&q=&{3}&appid={4}'.format(self.search_base, start,\
														 count, quality_parameters, self.appid)
		return address

	def send_request(self, link):
		response = requests.get(link)
		if response.status_code == 200:
			json_response = response.json()
			if (json_response['success']) and (json_response != []):
				return json_response
			else:
				return {'success': False}
		elif response.status_code == 429: # Timeout
			print('\nTimeout occured. Waiting about 60sec...')
			time.sleep(self.search_timeout_delay)
			return self.send_request(link)
		else:
			return {'success': False}
	
	def print_progress(self, start, total_count):
		sys.stdout.write('\r%i out of %i items processed...' % (min(start, total_count), total_count))
		sys.stdout.flush()
	# def print_progress(self, start, total_count):
	# 	print('%i out of %i items processed...' % (start, total_count), end='\r')


	def get_items_from_search(self):
		"Compose link for a request, get response as JSON, parse response, "
		print('Starting search request cycle...')
		address = self.compose_search_address(0, self.page_size)
		json = self.send_request(address)
		if json['success']:
			total_count = json['total_count']
		for start in range(0, total_count + self.page_size, self.page_size):
			address = self.compose_search_address(start, self.page_size)
			json = self.send_request(address)
			if not json['success']:
				print ("Error sending receiving list data from SCM...")
				self.search_results = []
				return False
			page = json['results_html']
			self.parse_page_for_items(page)
			self.print_progress(start, total_count)
			time.sleep(self.search_delay)
			#print('') # Neutralizing printProgress' \r syscall
		# When all is done, sort search_results by item name (for backpack.tf list)
		if (self.search_results != []):
			self.search_results.sort(key=lambda mItem: mItem.name)
			return True
		else:
			return False

	def parse_page_for_items(self, page):
		"Parses the HTML body of a request and appends mItems to search_results attribute"
		soup = BeautifulSoup(page, 'lxml')
		links = soup.find_all('a') # Find all hyperlinks
		# Parse span tags in hyperlinks which contain item information
		for link in links:
			spans = link.find_all('span')
			item = mItem()
			for span in spans:
				# Get item's name and quality
				if span['class'] == self.class_names['name']: 
					# Get item's quality from cell color
					color = span['style'].split()[1].lower()
					item.quality = self.color2quality[color]
					# Get item's name
					if not ((item.quality == 'Unique') or (item.quality == 'Decorated')):
						tmp = span.string.split()
						item.name = " ".join(tmp[1:])
					else:
						item.name = span.string
				# Get item's quantity
				elif span['class'] == self.class_names['quantity']:
					item.quantity = int(span.string.replace(',', ''))
				# Get item's normal price
				elif span['class'] == self.class_names['normal_price']:
					tmp = span.string.split()[0].replace('$', '').replace(',', '')
					item.normal_price = float(tmp)
				# Get item's sale price
				elif span['class'] == self.class_names['sale_price']:
					tmp = span.string.split()[0].replace('$', '').replace(',', '')
					item.sale_price = float(tmp)
				else:
					continue
			if item.contain_full_information():
				self.search_results.append(item)


	# Obtain currency exchange rate
	# '1' - Dollar
	# '5' - Rubbles
	def get_exchange_rate(self, currency, name):
		quality = ''
		if currency != '1':
			if (self.get_single_item_stats(quality, name, '1')):
				dollar_price = float(self.request_result.sale_price)
				time.sleep(self.request_delay)
			if (self.get_single_item_stats(quality, name, currency)):
				currency_price = float(self.request_result.sale_price)
		try:
			exchange_rate = currency_price / dollar_price
			return exchange_rate
		except:
			return 0

	# Make an individual request to SCM
	def get_single_item_stats(self, quality, name, currency):
		self.request_result = mItem()
		if (quality == ''): # If there is no quality, assume Normal or Unique
			hash_name = name
		else: # Add quality to name
			hash_name = quality + ' ' + name
		address = '{0}currency={1}&appid={2}&market_hash_name={3}'.format(self.request_base,\
																currency, self.appid, hash_name)
		json = self.send_request(address)
		if not json['success']:
			return False
		else:
			quantity = 0
			normal_price = 0.0
			sale_price = 0.0
			if 'lowest_price' in json.keys():
				matches = re.search(self.price_template, json['lowest_price'])
				if matches != None:
					tmp = matches.group(0).replace(',', '.')
					sale_price = float(tmp)
			if 'median_price' in json.keys(): # Median price exists
				matches = re.search(self.price_template, json['median_price'])
				if matches != None:
					tmp = matches.group(0).replace(',', '.')	
					normal_price = float(tmp)
				if sale_price == 0.0:
					sale_price = normal_price
			if 'volume' in json.keys(): # Volume exists
				quantity = int(json['volume'].replace(',', ''))
			self.request_result = mItem(name, quality, quantity, normal_price, sale_price)
			return True

	def get_single_item_stats_(self, quality, name, currency):
		self.request_result = mItem()
		if (quality == ''): # If there is no quality, assume Normal or Unique
			hash_name = name
		else: # Add quality to name
			hash_name = quality + ' ' + name
		address = '{0}currency={1}&appid={2}&market_hash_name={3}'.format(self.request_base,\
																currency, self.appid, hash_name)
		json = self.send_request(address)
		if not json['success']:
			return False
		else:
			try:
				matches = re.search(self.price_template, json['lowest_price'])
				tmp = matches.group(0).replace(',', '.')
				sale_price = float(tmp)
			except:
				sale_price = 0.0
			try:
				matches = re.search(self.price_template, json['median_price'])
				tmp = matches.group(0).replace(',', '.')	
				normal_price = float(tmp)
				if sale_price == 0.0:
					sale_price = normal_price
			except:
				normal_price = 0.0
			try:
				quantity = int(json['volume'].replace(',', ''))
			except:
				quantity = 0
			self.request_result = mItem(name, quality, quantity, normal_price, sale_price)
			return True