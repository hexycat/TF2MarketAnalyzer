# Class for requesting Backpack.TF price data
# DONE: spreadsheet pricelist
# TODO: Chemistry Set & Strangifier prices

import requests
from bs4 import BeautifulSoup, NavigableString

class bItem:
	def __init__(self, name='', itemtype='', craftable=True, tradable=True, quality='', metal=0.0):
		self.name = name
		self.itemtype = itemtype
		self.craftable = craftable
		self.tradable = tradable
		self.quality = quality
		self.metal = metal


class bSpreadsheet:
	def __init__(self):
		self.color2quality = {'#d2aa00': 'Unique', 
				  			  '#204728': 'Genuine',
				  		   	  '#1a3564': 'Vintage', 
				   		   	  '#a23d05': 'Strange',
				   		   	  '#0bc67e': 'Haunted', 
				   		   	  '#560000': 'Collectors'}
		self.link = "http://backpack.tf/pricelist/spreadsheet"
		#self.link = "http://backpack.tf/spreadsheet"
		self.init_page()
		self.init_items()

	def init_page(self):
	 	response = requests.get(self.link)
	 	if response.status_code == 200:
	 		self.page = response.text

	def init_items(self):
		try:
			self.parse_page_for_items(self.page)
		except Exception as e:
			print(e)
			self.items = []

	def is_item_row(self, tag):
		tr_check = tag.name == 'tr'
		craftable_check = tag.has_attr('data-craftable')
		tradable_check = tag.has_attr('data-tradable')
		return tr_check and craftable_check and tradable_check

	def select_items_rows(self, soup):
		return soup.find_all(self.is_item_row)

	def is_price_chunk(self, chunk):
		# Abbr defines the price table cell
		try:
			td_check = chunk.name == 'td'
			non_zero_price_check = chunk['abbr'] != '0'
			return td_check and non_zero_price_check
		except:
			return False

	def parse_style(self, style):
		color = style.split()[-1] # Pick the last one, background color
		return self.color2quality[color]

	def parse_page_for_items(self, page):
		self.items = []
		soup = BeautifulSoup(page, 'lxml')
		items_rows = self.select_items_rows(soup)
		for item_row in items_rows:
			name = ''
			itemtype = ''
			craftable = bool(int(item_row['data-craftable']))
			tradable = bool(int(item_row['data-tradable']))
			quality = [] # Same item name can have multiple prices & qualities
			metal = [] # Same item name can have multiple prices & qualities
			parse_name = False # Boolean for names, name has same TD as itemtype
			for chunk in item_row.children:
				# Empty spaces inside nodes = NavigableString obj
				# Skipping over them to avoid errors (wrong type)
				if (isinstance(chunk, NavigableString)): 
					continue

				if self.is_price_chunk(chunk):
					metal.append(float(chunk['abbr']))
					quality.append(self.parse_style(chunk['style']))
				else: # Either name or item type
					if not parse_name:
						name = chunk.contents[0]
						parse_name = True
					else:
						# Check if chunk is not empty, occasionally there are empty strings
						if len(chunk) > 0:
							itemtype = chunk.contents[0]

			for i in range(len(metal)):
				item = bItem(name, itemtype, craftable, tradable, quality[i], metal[i])
				self.items.append(item)