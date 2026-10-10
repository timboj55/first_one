import json, sys
d = json.load(open(sys.argv[1])); body = d['tabs'][0]['documentTab']['body']['content']
pt=lambda p:''.join(e.get('textRun',{}).get('content','') for e in p.get('elements',[]))
ct=lambda c:''.join(pt(x['paragraph']) for x in c['content'] if 'paragraph' in x).strip()
full=[]
def walk(content):
    for el in content:
        if 'paragraph' in el: full.append(pt(el['paragraph']))
        elif 'table' in el:
            for r in el['table']['tableRows']:
                for c in r['tableCells']: walk(c['content'])
walk(body); T=''.join(full)
print('Anchor 1C "Not sure which one it is? Leave it and ask Tim.":', T.count("Not sure which one it is? Leave it and ask Tim."))
print('Part 4 "(add your own)":', T.count('(add your own)'))
print('Heading "Sending a superbill" exists already:', T.count('Sending a superbill'))
print('Calls that aren\'t a fit already present:', T.count("Calls that aren"), '| Problem already solved present:', T.count('Problem already solved'), '| insurance heading present:', T.count('Do you take insurance'))
print('CHECKED ☑ total:', T.count('☑'), ' UNCHECKED ☐ total:', T.count('☐'))
# Date cells: tables whose header has "Date"
dates=0; prev=''
for el in body:
    if 'paragraph' in el: prev=pt(el['paragraph']).strip()
    if 'table' in el:
        rows=el['table']['tableRows']; hdr=[ct(c) for c in rows[0]['tableCells']]
        if 'Date' in hdr:
            j=hdr.index('Date'); filled=[ct(r['tableCells'][j]) for r in rows[1:] if ct(r['tableCells'][j])]
            dates+=len(filled)
        if prev.startswith('Phase 0'):
            for r in rows:
                cells=[ct(c) for c in r['tableCells']]
                if cells[1].startswith('Gmail'): print('Phase 0 Gmail row:', cells)
print('Filled Date cells total:', dates)
