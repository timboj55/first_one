import json, sys
d = json.load(open(sys.argv[1]))
body = d['tabs'][0]['documentTab']['body']['content']
inl = d['tabs'][0]['documentTab'].get('inlineObjects', {})
def ptext(p):
    out=''
    for e in p.get('elements',[]):
        if 'textRun' in e: out+=e['textRun']['content']
        elif 'inlineObjectElement' in e: out+='[IMG:%s]'%e['inlineObjectElement']['inlineObjectId']
    return out
def cell_text(c):
    return ''.join(ptext(x['paragraph']) for x in c['content'] if 'paragraph' in x).strip()
for el in body:
    if 'paragraph' in el:
        p=el['paragraph']; st=p.get('paragraphStyle',{}).get('namedStyleType','')
        t=ptext(p).strip()
        if st.startswith('HEADING') or st=='TITLE' or '[IMG' in t:
            print(el['startIndex'], st, t[:90])
    elif 'table' in el:
        tb=el['table']; rows=tb['tableRows']
        print(el['startIndex'], 'TABLE %dx%d'%(len(rows),tb['columns']), '|', ' || '.join(cell_text(c)[:30] for c in rows[0]['tableCells']), '| last:', ' || '.join(cell_text(c)[:30] for c in rows[-1]['tableCells']))
print('inline objects:', {k: v['inlineObjectProperties']['embeddedObject'].get('size') for k,v in inl.items()})
