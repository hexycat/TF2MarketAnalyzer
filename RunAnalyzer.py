import modules.BPrequest as bpr
import modules.SCMrequest as scmr
import modules.Merger as merger

querySCM = ["category_440_Type[]=any", 
    "category_440_Quality[]=tag_strange",
    "category_440_Quality[]=tag_vintage",
    "category_440_Quality[]=tag_Unique",
    "category_440_Quality[]=tag_rarity1",
    "category_440_Quality[]=tag_haunted",
    "category_440_Quality[]=tag_collectors"]
filterSCM = ['Killstreak', '(Factory New)', '(Minimal Wear)', '(Well-Worn)',
    '(Field-Tested)', '(Battle Scarred)', 'Chemistry Kit',
    'Strangifier', 'Crate Series', 'Crate 2012 Series',
    'Crate 2013 Series', 'Crate 2014 Series', 'Crate 2015 Series',
    'Munition Series', 'Cooler Series']
filterBP = ['Crate Series', 'Crate 2012 Series', 'Crate 2013 Series',
    'Crate 2014 Series', 'Crate 2015 Series', 'Munition Series',
    'Cooler Series']
appid = 440
currency = '5' # Rubbles

# Load data from backpack.tf
sheetBP = bpr.bSpreadsheet()
dataBP = sheetBP.items
# Load data from Steam community market
sheetSCM = scmr.mSpreadsheet(appid, querySCM)
if sheetSCM.get_items_from_search():
    dataSCM = sheetSCM.search_results
# Process datasets and write results to .xlsx file
mergerObject = merger.Merger(filterSCM, filterBP, dataSCM, dataBP, currency)
mergerObject.process_datasets()