import sys
import time
import datetime
import xlsxwriter
import modules.SCMrequest as SCMrequest

class Item:
	"Subclass for adding to the database"
	def __init__(self, name='', quality='', itemtype='', metal=0.0, sale_price=0.0,
			 normal_price=0.0, quantity=0):
		self.name = name
		self.quality = quality
		self.itemtype = itemtype
		self.metal = metal
		self.sale_price = sale_price
		self.normal_price = normal_price
		self.quantity = quantity


class Merger():
	"Class for merging BP & SCM lists for TF2"
	def __init__(self, filterSCM, filterBP, dataSCM, dataBP, currency):
		self.filterSCM = filterSCM
		self.filterBP = filterBP
		self.dataSCM = dataSCM 
		self.dataBP = dataBP 
		self.currency = currency 
		self.now = datetime.datetime.now() 
		self.log = []
		self.itembase = []
		self.exchange_rate = 0.0
		self.benchmark = 'Mann Co. Supply Crate Key'
		self.benchprice = 0.0
		self.benchmetal = 0.0
		
	def process_datasets(self):
		print('TF2 items merger')
		print('Filtering SCM dataset...')
		self.filter_market_data()
		print('Filtering BP dataset...')
		self.filter_backpack_data()
		print('Merging SCM & BP datasets...')
		self.merge_datasets()
		print('Start normalizing process...')
		self.normalize_price()
		print()
		print('Filling the spreadsheet...')
		self.write_itembase()
		print('Finished!')

	def get_current_time(self):
		return datetime.datetime.now().time().isoformat()

	def time_prefix(self):
		return '[' + self.get_current_time() + ']: '

	def get_file_name(self):
		date = self.now.date().isoformat().replace('-', '').lstrip('20')
		time = self.now.time().isoformat().replace(':', '')[0:4]
		return date + '-' + time

	def filter_market_data(self):
		filtered_items = []
		self.log.append([self.time_prefix() + 'Start filtering market data'])
		for item in self.dataSCM:
			if all(banned_name not in item.name for banned_name in self.filterSCM):
				filtered_items.append(item)
		self.log.append([self.time_prefix() + 'Original data cut from {0} to {1} entries'\
			 	.format(len(self.dataSCM), len(filtered_items))])
		self.log.append(self.time_prefix() + 'Finish filtering market data')
		self.dataSCM = filtered_items
		
	def is_unique_weapon(self, itemBP):
		itemtype_names = ['Melee', 'Secondary', 'Primary']
		if (itemBP.itemtype in itemtype_names) and (itemBP.quality == 'Unique'):
			return True
		else:
			return False

	def is_benchmark_item(self, itemBP):
		if (itemBP.name == self.benchmark) and (itemBP.quality == 'Unique'):
			self.benchmetal = itemBP.metal
			return True
		else:
			return False

	def filter_backpack_data(self):
		filtered_items = []
		self.log.append([self.time_prefix() + 'Start filtering backpack data'])
		for item in self.dataBP:
			if self.is_unique_weapon(item): continue
			if self.is_benchmark_item(item): continue
			if all(banned_name not in item.name for banned_name in self.filterBP):
				filtered_items.append(item)
		self.log.append([self.time_prefix() + 'Original data cut from {0} to {1} entries'\
			 	.format(len(self.dataBP), len(filtered_items))])
		self.log.append([self.time_prefix() + 'Finish filtering backpack data'])
		self.dataBP = filtered_items


	def is_unique_cosmetic(self, itemBP):
		if (itemBP.quality == 'Unique') and (itemBP.itemtype == 'Cosmetic'):
			return True
		else:
			return False

	def get_match_condition(self, itemBP, itemSCM, is_unique_cosmetic):
		if is_unique_cosmetic:
			return ((itemBP.name == 'The ' + itemSCM.name) or (
				itemBP.name == itemSCM.name)) and (itemBP.quality == itemSCM.quality)
		else:
			return (itemBP.name == itemSCM.name) and (itemBP.quality == itemSCM.quality)

	def merge_datasets(self):
		self.log.append([self.time_prefix() + 'Start merging SCM and BP data'])
		for itemBP in self.dataBP:
			is_unique_cosmetic = self.is_unique_cosmetic(itemBP)
			itemSCM_position = [i for i, itemSCM in enumerate(self.dataSCM) 
								if self.get_match_condition(itemBP, itemSCM, is_unique_cosmetic)]
			if len(itemSCM_position) > 0:
				position = itemSCM_position[0]
				item = Item(self.dataSCM[position].name, self.dataSCM[position].quality,
							itemBP.itemtype, itemBP.metal,
							self.dataSCM[position].sale_price, self.dataSCM[position].normal_price, 
							self.dataSCM[position].quantity)
				self.itembase.append(item)
		self.log.append([self.time_prefix() + 'From {0} SCM entries and'.format(len(self.dataSCM)) +
		 		'{0} BP entries we get {1} joint ones.'.format(len(self.dataBP), len(self.itembase))])

	def print_progress(self, current_step):
		sys.stdout.write('\r\tStep: %i' % current_step)
		sys.stdout.flush()


	def normalize_price(self):
		mSpreadsheet = SCMrequest.mSpreadsheet() # Init a SCM Spreadsheet
		print('\tGrabbing benchmark exchange rate...') # Get exchange rate and benchprice
		self.exchange_rate = mSpreadsheet.get_exchange_rate(self.currency, self.benchmark)
		time.sleep(mSpreadsheet.request_delay) # Pause, now benchprice
		print('\tGrabbing benchpark market price...')
		if mSpreadsheet.get_single_item_stats('', self.benchmark, self.currency):
			self.benchprice = mSpreadsheet.request_result.sale_price
		time.sleep(mSpreadsheet.request_delay)
		deviation = [1.0] * 9 # Fill deviation array with 9 1s avoids the script stopping after the 1st item
		final_position = 0 # Final position, for iteration of the rest
		print('\tNormalizing prices...')
		self.log.append([self.time_prefix() + 'Start normalizing prices'])
		for i in range(0, len(self.itembase)): # Iterate through merge array
			if (len(deviation) >= 10): deviation.pop(0) # If array is full, pop out the first item
			self.print_progress(i)
			approx = self.itembase[i].sale_price * self.exchange_rate # Approximate price, from merge
			self.log.append(['Step: {}'.format(i)])
			self.log.append(['Original sale price: {}'.format(self.itembase[i].sale_price)])
			self.log.append(['Approximate sale price: {}'.format(approx)])
			if mSpreadsheet.get_single_item_stats(self.itembase[i].quality, self.itembase[i].name, self.currency):
				actual = mSpreadsheet.request_result.sale_price # Actual market price
				self.log.append(['Actual sale price: {}'.format(actual)])
			else:
				self.log.append(['Error fetching on step {}'.format(i)])
				continue
			# Change prices to true ones
			self.itembase[i].sale_price = mSpreadsheet.request_result.sale_price
			self.itembase[i].normal_price = mSpreadsheet.request_result.normal_price	
			numerical_deviation = abs(approx - actual) # Absolute difference between approximate and actual
			relative_deviation = numerical_deviation / actual
			deviation.append(relative_deviation)
			average = sum(deviation) / float(len(deviation))
			self.log.append(['Numerical deviation: {}'.format(numerical_deviation)])
			self.log.append(['Relative deviation: {}'.format(relative_deviation)])			
			self.log.append(['Median of deviation: {}'.format(average)])
			if (sum(deviation) > 0.0) and  (average < 0.10): # If non-zero median and less than percentage 
				final_position = i # Establish final position
				break # Success, breaking out
			else:
				time.sleep(mSpreadsheet.request_delay) # Single request delay before the next	
		# Calculating the rest according to merge array data
		# Checking if final position is not the end of the array
		if not ((final_position+1) == len(self.itembase)):
			for j in range(final_position+1, len(self.itembase)):
				new_sale_price = self.itembase[j].sale_price * self.exchange_rate
				new_normal_price = self.itembase[j].normal_price * self.exchange_rate
				self.itembase[j].sale_price = round(new_sale_price, 2)
				self.itembase[j].normal_price = round(new_normal_price, 2)
			self.log.append(['Positions {0} through {1} filled as normal'.format(final_position, len(self.itembase))])

	def write_itembase(self):
		workbook_name = self.get_file_name() + '.xlsx'
		workbook = xlsxwriter.Workbook(workbook_name)
		datasheet = workbook.add_worksheet('Data')
		ratesheet = workbook.add_worksheet('Rate')
		# Styles:
		bold_style = workbook.add_format({'bold': True})
		profit_style = workbook.add_format({'num_format': '[Green]+0.00; [Red]-0.00; [Blue]0.00'})
		rates_style = workbook.add_format({'num_format': '[Green]+0.000#; [Red]-0.000#; [Blue]0.000#'})
		quality_style = workbook.add_format({'bold': True, 'italic': True})
		# Fill out rates
		ratesheet.write(0, 0, 'Benchmark', bold_style)
		ratesheet.write(1, 0, self.benchmark)
		ratesheet.write(0, 1, 'Metal', bold_style)
		ratesheet.write(1, 1, self.benchmetal)
		ratesheet.write(0, 2, 'Currency', bold_style)
		ratesheet.write(1, 2, self.benchprice)
		# Datasheet headers
		datasheet.write(0, 0, 'Quality', bold_style)
		datasheet.write(0, 1, 'Name', bold_style)
		datasheet.write(0, 2, 'Type', bold_style)
		datasheet.write(0, 3, 'Quantity', bold_style)
		datasheet.write(0, 4, 'Normal', bold_style)
		datasheet.write(0, 5, 'Value', bold_style)
		datasheet.write(0, 6, 'Metal', bold_style)
		datasheet.write(0, 7, 'Buy Rate', bold_style)
		datasheet.write(0, 8, 'Sell Rate', bold_style)
		datasheet.write(0, 9, 'Buy Profit', bold_style)
		datasheet.write(0, 10, 'Sell Profit', bold_style)
		# Fill out data
		bench_money2metal = self.benchprice / self.benchmetal
		bench_metal2money = 1 / bench_money2metal
		for i in range(0, len(self.itembase)):
			# Calculating rates and profits
			item_money2metal = self.itembase[i].sale_price / self.itembase[i].metal
			item_metal2money = 1 / item_money2metal
			buyrate = bench_money2metal - item_money2metal 			
			sellrate = bench_metal2money - item_metal2money 
			buyprofit = self.itembase[i].metal - (self.itembase[i].sale_price * bench_metal2money)
			sellprofit = self.itembase[i].sale_price - (self.itembase[i].metal * bench_money2metal)
			
			datasheet.write(i + 1, 0, self.itembase[i].quality, quality_style)
			datasheet.write(i + 1, 1, self.itembase[i].name, quality_style)
			datasheet.write(i + 1, 2, self.itembase[i].itemtype)
			datasheet.write(i + 1, 3, self.itembase[i].quantity)
			datasheet.write(i + 1, 4, self.itembase[i].normal_price)
			datasheet.write(i + 1, 5, self.itembase[i].sale_price)
			datasheet.write(i + 1, 6, self.itembase[i].metal)
			datasheet.write(i + 1, 7, buyrate, rates_style)
			datasheet.write(i + 1, 8, sellrate, rates_style)
			datasheet.write(i + 1, 9, round(buyprofit, 2), profit_style)
			datasheet.write(i + 1, 10, round(sellprofit, 2), profit_style)
		workbook.close()