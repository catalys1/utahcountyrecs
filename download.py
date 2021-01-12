import json
import time
import urllib

from bs4 import BeautifulSoup
from pathlib import Path
import requests
import tqdm


headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}

base = 'http://www.utahcounty.gov/'
search = 'LandRecords/AddressSearch.asp?av_valid=...&Submit=++++Search++++'
prop = 'LandRecords/property.asp?av_serial={}'

def search_query(opts=None, **kwargs):
    '''
    av_house
    av_dir
    av_street
    street_type
    av_location
    '''
    op = {}
    if opts: op.update(opts)
    if kwargs: op.update(kwargs)
    qs = urllib.parse.urlencode(op, doseq=True)
    return qs

def search_street(street, city='PROVO'):
    url = urllib.parse.urljoin(base, search)
    url = '&'.join((url, search_query(av_street=street, av_location=city)))

    def extract(soup):
        rows = soup.select('td table tr')[1:]
        links = []
        for r in rows:
            try:
                link = r.select_one('td a').attrs['href']
                if link.startswith('SerialVersion'):
                    links.append(link)
            except Exception as e:
                pass
        return links

    links = []
    next_url = url
    while True:
        response = requests.get(next_url, headers=headers)
        soup = BeautifulSoup(response.text, features='html.parser')

        links.extend(extract(soup))

        add_pages = soup.select('table table')[1].select('a')
        next_url = [x.attrs['href'] for x in add_pages if x.text=='Next']

        if next_url:
            next_url = urllib.parse.urljoin(base, next_url[0])
        else:
            break
    
    return links

def get_property_info(serial):
    url = urllib.parse.urljoin(base, prop.format(serial.replace(':','')))
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, features='html.parser')
    address = soup.select('table table table')[0].select('tr')[2].select('td')[0]
    address = list(address.children)[1].strip()
    panels = soup.select('.TabbedPanelsContent') 
    owner = panels[0].select('tr')[1].select('td')[2].text.strip()
    rows = panels[5].select('tr')[1:]
    rows = [[a.text for a in x.select('td')] for x in rows]
    data = {'address': address, 'owner': owner, 'url': url, 'docs': rows}
    return data
    
def properties_by_street(street, city='PROVO', delay=0.5):
    links = search_street(street, city.upper())
    serials = [x.split('=')[1] for x in links]

    data = []
    it = tqdm.tqdm(serials, desc=street)
    for serial in it:
        try:
            info = get_property_info(serial)
            it.write(info['address'])
            data.append(info)
        except Exception as e:
            m = f'{serial} (error): {type(e)}'
            it.write(m)
        time.sleep(delay)
    
    return data

def streets_from_file(filepath):
    with open(filepath, 'r') as fp:
        streets = fp.read().strip().split('\n')
    return streets

def search_street_list(streets, city='PROVO', outfile=None):
    data = []
    for street in streets:
        props = properties_by_street(street, city)
        data.extend(props)
        if outfile:
            json.dump(data, open(outfile, 'w'))
    return data

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=str,
        help='Street name or path to file with street names (one per row)')
    parser.add_argument('--city', type=str, default='PROVO',
        help='Name of city to search in. Default: PROVO')
    parser.add_argument('--output', type=str, default='property-data.json',
        help='Path to output file. Default: property-data.json')
    
    args = parser.parse_args()

    if Path(args.source).is_file():
        streets = streets_from_file(args.source)
    else:
        streets = [args.source]

    start_time = time.time()
    data = search_street_list(streets, args.city)
    with open(args.output, 'w') as fp:
        json.dump(data, fp, indent=2)
    elapsed = time.time() - start_time
    hours = int(divmod(elapsed, 3600)[0])
    minutes = int(divmod(elapsed - hours*3600, 60)[0])
    seconds = round(elapsed - hours*3600 - minutes*60, 2)

    print(f'Searched {len(streets)} streets in {hours}:{minutes}:{seconds}')
