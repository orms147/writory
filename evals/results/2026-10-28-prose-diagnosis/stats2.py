import re,glob,collections
sets={'tu-tien-4':'2026-10-21-run-tu-tien-4','ky-ao-3':'2026-10-22-run-ky-ao-vua-3','bakeoff-luna':'2026-10-22-run-bakeoff-luna'}
def toks(s): return set(re.findall(r'[^\W\d_]+',s.lower()))
def jac(a,b):
    a,b=toks(a),toks(b); return len(a&b)/max(1,len(a|b))
FORMAL=r'xác nhận|đối chiếu|căn cứ|điều khoản|chứng cứ|thủ tục|ghi nhận|ghi rõ|bảo lưu|quyền|trách nhiệm|biên nghị|phán nghị|kiểm tra|xác minh|hồ sơ|bản ghi|thẩm quyền|lời thề'
SENS={'mùi':r'\bmùi\b','vị (nếm)':r'\bvị (?:mặn|đắng|ngọt|chua|tanh)','nóng/ấm':r'\b(?:nóng|ấm|hơi ấm|hơi nóng)\b','gió':r'\bgió\b','mưa/sương':r'\b(?:mưa|sương)\b','tiếng (âm thanh)':r'\btiếng\b','đau/nhói/run':r'\b(?:đau|nhói|run|rát|buốt|tê)\b'}
EMO=r'\b(?:sợ|giận|buồn|lo lắng|hoảng|run rẩy|nghẹn|tim|hồi hộp|căm|thương|nhớ|xấu hổ|tức|bối rối|bất an)\b'
tot=collections.Counter()
for name,d in sets.items():
    fs=sorted(glob.glob(d+'/chapters/ch*.md'))
    print('=====',name)
    allt='';dial='';narr=''
    echo=0;rest=[];openJ=[]
    prev_open=None;chosen_types=collections.Counter();tones=collections.Counter();optlen=[];chosen_pos=collections.Counter()
    stall_choice=0;nchoice=0
    for f in fs:
        t=open(f,encoding='utf-8').read()
        body,_,ch=t.partition('## Lựa chọn cuối chương')
        L=[l.strip() for l in body.split('\n') if l.strip() and not l.startswith('#')]
        intro=[l for l in L if l.startswith('_Lựa chọn dẫn')]
        L=[l for l in L if not l.startswith('_Lựa chọn dẫn')]
        # echo check: first dialogue line vs intro option text
        if intro:
            opt=re.sub(r'^_Lựa chọn dẫn tới chương này: \[[^\]]*\]\s*','',intro[0]).strip('_ .')
            first=[l for l in L if l!='* * *'][0]
            if first.startswith('- ') and jac(first,opt)>0.6: echo+=1
        sc=[]; cur=[]
        for l in L:
            if l=='* * *': sc.append(cur);cur=[]
            else: cur.append(l)
        sc.append(cur)
        if len(sc)>1:
            a=[x for x in sc[0] if not x.startswith('- ')]
            b=[x for x in sc[1] if not x.startswith('- ')]
            # similarity of scene2 first narration para vs scene1 last 2 narration paras and vs scene1 first
            rest.append((jac(' '.join(sc[0][-2:]),' '.join(sc[1][:2])), jac(' '.join(sc[0][:3]),' '.join(sc[1][:3]))))
            # beat overlap: dialogue lines of scene 2 that also (jaccard>.6) appear in scene 1
        s1=' '.join(sc[0]);s2=' '.join(sc[-1])
        for l in L:
            allt+=l+'\n'
        dial+=' '.join(l for l in L if l.startswith('- '))+'\n'
        narr+=' '.join(l for l in L if not l.startswith('- ') and l!='* * *')+'\n'
        o=[x for x in L if x!='* * *'][0]
        first_sent=re.split(r'(?<=[.!?])\s',o)[0]
        if prev_open is not None: openJ.append(jac(prev_open,first_sent))
        prev_open=first_sent
        # dialogue repeated within chapter across scenes
        d1=[x for x in sc[0] if x.startswith('- ')];d2=[x for x in sc[-1] if x.startswith('- ')] if len(sc)>1 else []
        dup=sum(1 for x in d2 if any(jac(x,y)>0.7 for y in d1))
        tot['dupdial']+=dup;tot['dial2']+=len(d2)
        # choices
        for m in re.finditer(r'^(\d)\. \[([^\]]*)\] (.*?)(  ← đã chọn)?$',ch,re.M):
            nchoice+=1
            typ=m.group(2);chosen_types[typ]+=1
            optlen.append(len(m.group(3).split()))
            if m.group(4): chosen_pos[m.group(1)]+=1
    w=len(allt.split())
    print(' lặp-đồ-thị: ch có lời thoại đầu = chép lại lựa chọn người chơi:',echo,'/',len(fs))
    print(' độ giống (Jaccard từ) 2 đoạn cuối cảnh 1 ↔ 2 đoạn đầu cảnh 2: TB %.2f; max %.2f; giống đầu cảnh 1↔đầu cảnh 2: TB %.2f'%(sum(r[0] for r in rest)/len(rest),max(r[0] for r in rest),sum(r[1] for r in rest)/len(rest)))
    print(' độ giống câu mở chương liền kề: TB %.2f, max %.2f, số cặp >=0.5: %d/%d'%(sum(openJ)/len(openJ),max(openJ),sum(x>=.5 for x in openJ),len(openJ)))
    dl=len(dial.split())
    dl_lines=[x for x in dial.split('\n') if x]
    # approximate per line: re-split on ' - '
    lines=re.split(r'\s-\s',' '+dial); lines=[x for x in lines if x.strip()]
    frm=sum(1 for x in lines if re.search(FORMAL,x.lower()))
    print('\r lời thoại chứa từ thủ tục/pháp lý: %d/%d = %.0f%%'%(frm,len(lines),100*frm/len(lines)))
    nw=len(narr.split())
    print(' giác quan trong lời kể (/1000 từ kể):',{k:round(1000*len(re.findall(p,narr.lower()))/nw,1) for k,p in SENS.items()})
    print(' từ cảm xúc trực tiếp (/1000 từ):',round(1000*len(re.findall(EMO,allt.lower()))/w,2),'; số lần:',len(re.findall(EMO,allt.lower())))
    print(' lựa chọn: loại',dict(chosen_types),'; chọn vị trí',dict(chosen_pos),'; độ dài chữ TB %.1f từ'%(sum(optlen)/len(optlen)))
print('lời thoại cảnh 2 trùng lời thoại cảnh 1 (J>0.7):',tot['dupdial'],'/',tot['dial2'])
