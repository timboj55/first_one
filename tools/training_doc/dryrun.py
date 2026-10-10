import json, sys
sys.path.insert(0, sys.argv[2]); from spec import R
d = json.load(open(sys.argv[1]))
body = d['tabs'][0]['documentTab']['body']['content']
paras=[]  # (startIndex, text, location)
def walk(content, loc):
    head=loc
    for el in content:
        if 'paragraph' in el:
            t=''.join(e.get('textRun',{}).get('content','') for e in el['paragraph'].get('elements',[]))
            paras.append((el['startIndex'], t, loc))
        elif 'table' in el:
            for ri,row in enumerate(el['table']['tableRows']):
                for ci,c in enumerate(row['tableCells']):
                    walk(c['content'], '%s/table@%d r%dc%d'%(loc, el['startIndex'], ri, ci))
heading=['']
def walk_top():
    for el in body:
        if 'paragraph' in el and el['paragraph'].get('paragraphStyle',{}).get('namedStyleType','').startswith('HEADING'):
            heading[0]=''.join(e.get('textRun',{}).get('content','') for e in el['paragraph']['elements']).strip()[:40]
        walk([el], heading[0])
walk_top()
norm=lambda s: s.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')
for n,f,r,exp in R:
    hits=[(i,l) for i,t,l in paras if f in t]
    nh=sum(t.count(f) for i,t,l in paras)
    nn=sum(norm(t).count(f) for i,t,l in paras)
    done=sum(t.count(r) for i,t,l in paras)+sum(norm(t).count(r) for i,t,l in paras if r not in t)
    flag='OK' if nh==exp else ('ALREADY DONE?' if nh==0 and done else 'MISMATCH')
    print(f'#{n}: exact={nh} curly-normalized={nn} expected={exp} replace-present={done} -> {flag}')
    for i,l in hits: print('     @',i,l)
