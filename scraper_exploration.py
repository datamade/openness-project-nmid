import os
from io import StringIO
import csv
import time
from collections import OrderedDict
from urllib.parse import urlencode

from lxml import etree, html
import requests
import scrapelib

class NMIDScraper(object):
    def __init__(self):

        self.session = requests.Session()
        self.base_url = 'https://www.cfis.state.nm.us/media'
     
    def getTableGuts(self, table, filing_period=None):
        header_row = [h.text for h in table.xpath('./tr/th')]
        
        rows = []
        
        for entry in table.xpath('./tr'):
            if not entry.xpath('./th'):
                row = OrderedDict()

                for index, cell in enumerate(entry.xpath('./td')):
                    if cell.xpath('./a'):
                        row[header_row[index]] = {
                            'text': cell.xpath('./a/text()')[0].strip(),
                        }
                        if cell.xpath('./a')[0].attrib.get('href'):
                            row[header_row[index]]['link'] = cell.xpath('./a')[0].attrib.get('href').strip()
                    elif cell.xpath('./text()'):
                        row[header_row[index]] = {'text': cell.xpath('./text()')[0].strip()}
                    else:
                        row[header_row[index]] = {'text': None}
                
                if filing_period:
                    row['filing_period'] = {'text': filing_period}
                
                rows.append(row)

        return rows

    def getLastPage(self, document):
        page_link = document.xpath('//a[contains(@href, "javascript:__doPostBack(\'ctl00$ContentPlaceHolder1$grd\'")]')
        try:
            href = page_link[-1].attrib['href']
            page_index = href.rfind('$') + 1
            last_quote_index = href.rfind("'")
            last_page = int(href[page_index:last_quote_index])
        except IndexError:
            last_page = 1
        
        return last_page

    def iterPages(self, document, url):
        
        yield document
        
        page = 2
        
        while True:
            payload = self.sessionSecrets(document, page)
            page_content = self.session.post(url, data=payload)
            document = html.fromstring(page_content.content)
            page += 1
            yield document

    def parseTransactions(self, url, filing_period):
        page = self.session.get(url)
        document = html.fromstring(page.content)
        document.make_links_absolute(url)
        
        table = document.xpath('//table[@id="ctl00_ContentPlaceHolder1_grd"]')
        
        all_transactions = []

        if table:
            
            if self.getLastPage(document) > 1:

                for page in self.iterPages(document, url):
                    
                    try:
                        page_table = page.xpath('//table[@id="ctl00_ContentPlaceHolder1_grd"]')[0]
                        time.sleep(1)
                    except IndexError:
                        break
                    
                    all_transactions.extend(self.getTableGuts(page_table, 
                                                              filing_period=filing_period))
            else:
                all_transactions.extend(self.getTableGuts(table[0], 
                                                          filing_period=filing_period))

        return all_transactions

    def sessionSecrets(self, page, page_num):

        payload = {}
        payload['__EVENTARGUMENT'] = 'Page${}'.format(page_num)
        payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$grd'
        payload['__VIEWSTATE'] = page.xpath("//input[@name='__VIEWSTATE']/@value")[0]
        try :
            payload['__EVENTVALIDATION'] = page.xpath("//input[@name='__EVENTVALIDATION']/@value")[0]
        except IndexError :
            pass

        return(payload)
    
    def iterCampaignInfo(self):
        with open('data/Cam_CampaignOfficeType.csv') as f:
            reader = csv.DictReader(f)
            
            yield from reader

    def scrapeCandidates(self):

        all_candidates = []

        for row in self.iterCampaignInfo():
            # Just looking at newer election seasons so there are contributions
            
            if int(row['ElectionSeasonId']) >= 17:
                params = {
                    'es': row['ElectionSeasonId'],
                    'o': row['ElectionOfficeId'],
                    'c': row['CandidateId'],
                    'ot': row['OfficeTypeId'],
                    'p': 0,
                    'd': '',
                    'ct': row['CountyId'],
                }
                
                url = '{0}/CandidateReportH.aspx?{1}'.format(self.base_url, urlencode(params))
                
                candidate_page = self.session.get(url)
                document = html.fromstring(candidate_page.content)
                
                candidate_info = OrderedDict()
                
                selector_fmt = '//td[b/text()[. = "{}"]]/following-sibling::td'

                try:
                    candidate_name = document.xpath(selector_fmt.format('Candidate Name:'))[0].text
                    candidate_phone = document.xpath(selector_fmt.format("Phone:"))[0].text
                    election_year = document.xpath(selector_fmt.format("Election Year:"))[0].text
                    office_sought = document.xpath(selector_fmt.format("Office Sought"))[0].text
                    address = document.xpath(selector_fmt.format("Address:"))[0].text
                except IndexError:
                    print('URL does not exist', candidate_page.history[0].url)
                    continue
                
                document.make_links_absolute(candidate_page.url)

                candidate_info['candidate_id'] = row['CandidateId']
                candidate_info['candidate_name'] = candidate_name
                candidate_info['candidate_phone'] = candidate_phone
                candidate_info['election_year'] = election_year
                candidate_info['office_sought'] = office_sought
                candidate_info['address'] = address
                
                all_candidates.append(candidate_info)
                
                print('Found {}'.format(candidate_info['candidate_name']))

                time.sleep(1)

        if all_candidates:
            
            with open('candidates.csv', 'w') as f:
                writer = csv.writer(f)
                writer.writerow(all_candidates[0].keys())
                writer.writerows([f.values() for f in all_candidates])

    def scrapeTransactions(self):
        for row in self.iterCampaignInfo():
            if int(row['ElectionSeasonId']) >= 17:
                params = {
                    'es': row['ElectionSeasonId'],
                    'o': row['ElectionOfficeId'],
                    'c': row['CandidateId'],
                    'ot': row['OfficeTypeId'],
                    'p': 0,
                    'd': '',
                    'ct': row['CountyId'],
                }
                
                url = '{0}/CandidateReportH.aspx?{1}'.format(self.base_url, urlencode(params))
                
                candidate_page = self.session.get(url)
                document = html.fromstring(candidate_page.content)
                document.make_links_absolute(candidate_page.url)

                filings_table = document.xpath('//table[@id="ctl00_ContentPlaceHolder1_grd"]')[0]
                
                filings = self.getTableGuts(filings_table)
                
                all_contributions = []
                all_expenditures = []

                for filing in filings:
                    contributions_page_url = filing['Total Contributions']['link']
                    expenditures_page_url = filing['Total Expenditures']['link']
                    filing_period = filing['Filing Period']['text']
                    print('working on {filing} for {cand}'.format(filing=filing_period,cand=row['CandidateId']))

                    all_contributions.extend(self.parseTransactions(contributions_page_url, filing_period))
                    all_expenditures.extend(self.parseTransactions(expenditures_page_url, filing_period))

                if all_contributions:
                    print('got {0} contributions from {1}'.format(len(all_contributions), row['CandidateId']))
                    

                    contributions_file = '{cand_id}-contributions.csv'.format(cand_id=row['CandidateId'])
                    
                    with open(contributions_file, 'w') as f:
                        writer = csv.writer(f)
                        header = ['candidate_id'] + list(all_contributions[0].keys())
                        writer.writerow(header)
                        
                        for contribution in all_contributions:
                            c_row = [row['CandidateId']] + \
                                  [r['text'] for r in contribution.values()]
                            writer.writerow(c_row)
                
                if all_expenditures:
                    
                    print('got {0} expenditures from {1}'.format(len(all_expenditures), expenditures_page_url))
                    
                    expenditures_file = '{cand_id}-expenditures.csv'.format(cand_id=row['CandidateId'])
                    with open(expenditures_file, 'w') as f:
                        writer = csv.writer(f)
                        header = ['candidate_id'] + list(all_expenditures[0].keys())
                        writer.writerow(header)
                        
                        for expenditure in all_expenditures:
                            c_row = [row['CandidateId']] + \
                                  [r['text'] for r in expenditure.values()]
                            writer.writerow(c_row)

                    time.sleep(1)
                time.sleep(1)
    
    def scrapePACs(self):
        pacs_listing = self.session.get('{}/Pacmain.aspx'.format(self.base_url))
        document = html.fromstring(pacs_listing.content)
        document.make_links_absolute(pacs_listing.url)
        
        for page in self.iterPages(document, pacs_listing.url):

            pacs_table = page.xpath('//table[@id="ctl00_ContentPlaceHolder1_grd"]')[0]
            
            print(pacs_table)

            pacs = self.getTableGuts(pacs_table)

            for pac in pacs:
                print(pac)

            time.sleep(0)

if __name__ == "__main__":
    import sys

    scraper = NMIDScraper()
    
    if sys.argv[1] == 'candidates':
        scraper.scrapeCandidates()
    elif sys.argv[1] == 'transactions':
        scraper.scrapeTransactions()
    elif sys.argv[1] == 'pacs':
        scraper.scrapePACs()
