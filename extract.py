import datetime
import json
import csv


def load_properties(filepath):
    properties = json.load(open(filepath))
    return properties


def save_spreadsheet(data, fp='properties.tsv'):
    with open(fp, 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        keys = 'address owner doc type date'.split()
        writer.writerow(keys)
        for row in data:
            for d in row['docs']:
                r = [row['address'], row['owner'], d[0], d[3], d[2]]
                writer.writerow(r)


def get_recent(properties, back_delta=30, doc_types=None):
    if doc_types:
        doc_types = [x.lower() for x in doc_types]
    recent = []
    today = datetime.date.today()
    for prop in properties:
        docs = prop['docs']
        rdocs = []
        for d in docs:
            date = list(map(int, d[2].split('/')))
            date = datetime.date(date[2],date[0],date[1])
            delta = (today - date).days
            keep = delta <= back_delta
            keep = keep and (not doc_types or d[3].lower() in doc_types)
            if keep:
                rdocs.append(d)
        if len(rdocs) > 0:
            p = {}
            p.update(prop)
            p['docs'] = rdocs
            recent.append(p)

    return recent


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f','--file', type=str, default='property-data.json',
                        help='Path to file with downloaded data')
    parser.add_argument('-r','--range', type=int, default=30,
                        help='Number of days back to keep. Default: 30')
    parser.add_argument('-o','--output', type=str, default='properties.tsv',
                        help='Path to output file. Default: properties.tsv')
    parser.add_argument('--filter', nargs='*', 
                        help='Filter for specific document types')
    args = parser.parse_args()

    props = load_properties(args.file)
    recent = get_recent(props, args.range, args.filter)
    save_spreadsheet(recent, args.output)
