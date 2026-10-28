import re,glob,statistics as st,collections
sets={'tu-tien-4 (Ngắn,6ch)':'2026-10-21-run-tu-tien-4','ky-ao-3 (Vừa,10ch)':'2026-10-22-run-ky-ao-vua-3','bakeoff-luna (Ngắn,6ch)':'2026-10-22-run-bakeoff-luna'}
PHR={'Không ai':r'\bKhông ai\b','ngón tay (gõ|miết|ghì|khẽ)':r'ngón tay','ánh mắt':r'[Áá]nh mắt','khẽ':r'\bkhẽ\b','nhếch môi/cười nhạt':r'nhếch môi|cười nhạt|cười ngắn','khô khốc':r'khô khốc','lạnh ngắt/lạnh buốt':r'lạnh ngắt|lạnh buốt','nặng hơn/nặng trịch':r'nặng hơn','vẫn':r'\bvẫn\b','chưa':r'\bchưa\b','một thoáng/một nhịp/một lúc':r'một thoáng|một nhịp|một lúc|một chặp','giữa (bàn|án)':r'giữa (?:bàn|án)','không ... mà là/chứ không':r'chứ không|không phải [^.]{1,40}, mà|không chỉ [^.]{1,40}, mà'}
def split(t):
    body=t.split('## Lựa chọn cuối chương')[0]
    lines=[l.strip() for l in body.split('\n') if l.strip()]
    lines=[l for l in lines if not l.startswith('#') and not l.startswith('_Lựa chọn dẫn') ]
    return lines
for name,d in sets.items():
    fs=sorted(glob.glob(d+'/chapters/ch*.md'))
    dia=nar=0; sl=[]; dl=[]; words=0; text_all=''
    scenes_close=[]; tail_noone=0; scenes=0; choice_stall=0
    openers=collections.Counter()
    for f in fs:
        t=open(f,encoding='utf-8').read()
        L=split(t); body='\n'.join(L); text_all+=body+'\n'
        parts=body.split('* * *')
        for p in parts:
            scenes+=1
            ps=[x.strip() for x in p.split('\n') if x.strip()]
            last=ps[-1]
            # closing paragraph classified
            if re.search(r'\b(Không ai|không ai|vẫn (?:chưa|còn|đứng|nằm|ở)|chưa (?:ai|được|có)|chờ)\b',last): tail_noone+=1
        for l in L:
            if l=='* * *' or l.startswith('_Hết'): continue
            if l.startswith('- '):
                dia+=1; dl.append(len(l.split()))
            else:
                nar+=1
                for s in re.split(r'(?<=[.!?…])\s+',l):
                    n=len(s.split())
                    if n: sl.append(n)
                openers[l.split()[0]]+=1
    w=len(text_all.split())
    print('=====',name,'| chương',len(fs),'| từ',w,'| cảnh',scenes)
    print(' dòng thoại',dia,'dòng kể',nar,'-> thoại %.0f%%'%(100*dia/(dia+nar)))
    print(' câu kể: TB %.1f từ, độ lệch %.1f, <=6 từ: %.0f%%, >=25 từ: %.0f%%'%(st.mean(sl),st.pstdev(sl),100*sum(x<=6 for x in sl)/len(sl),100*sum(x>=25 for x in sl)/len(sl)))
    print(' dòng thoại: TB %.1f từ, <=6 từ: %.0f%%'%(st.mean(dl),100*sum(x<=6 for x in dl)/len(dl)))
    tot=sum(openers.values())
    print(' đoạn kể mở bằng "Tôi": %.0f%%; top mở đoạn:'%(100*openers['Tôi']/tot),openers.most_common(6))
    print(' cuối cảnh có kiểu treo/đứng yên/"Không ai": %d/%d'%(tail_noone,scenes))
    for k,p in PHR.items():
        c=len(re.findall(p,text_all)); print('   %-34s %3d  (%.1f/1000 từ)'%(k,c,1000*c/w))
    # top content words
    toks=re.findall(r'[^\W\d_]+',text_all.lower())
    syl=collections.Counter(toks)
    bi=collections.Counter(zip(toks,toks[1:]))
    stop=set('và là của có không một những được cho với tôi ta đã để các này thì khi như trong ra rồi còn nhưng cũng mà lại vào nó hắn nàng ông bà người đó ở lên xuống chỉ cả hay nếu sẽ đang theo về từ thể bị ai gì sao đây nào hơn bên lời hai ba'.split())
    print(' bigram lặp nhiều nhất:',[(' '.join(b),c) for b,c in bi.most_common(60) if not (b[0] in stop or b[1] in stop)][:14])
