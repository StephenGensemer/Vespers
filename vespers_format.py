import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import subprocess, re, fnmatch, os, time, pyphen
import unicodedata
from datetime import datetime


def parse_universalis_ebook(filename,n_parts=14):
    sections = {}
    toc_end_marker = "Copyrights & acknowledgements"
    ebook_end_marker = "Your current e-book ends on"        
    head_marker = 'Table of Contents'

    
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Step 1: Extract the Table of Contents
    toc_start = content.find("Table of Contents")
    toc_end = content.find(toc_end_marker, toc_start)
    if toc_start == -1 or toc_end == -1:
        print("Table of Contents not found or incomplete.")
        return sections
    
    # Extract and clean the Table of Contents lines
    toc_content = content[toc_start:toc_end]
    dates = []
    format_string = '%A %d %B %Y'
    for date_string in toc_content.splitlines():
        try:
            parsed_date = datetime.strptime(date_string, format_string)
            dates.append(date_string)
        except ValueError:
            None
    
    # Step 2: Extract sections based on dates
    content_after_toc = content[toc_end:]
    part_marker = r'\* \* \*'  # Pattern to match "* * *" markers
    
    for i, date in enumerate(dates):
        # Find start of this date's section
        start_index = content_after_toc.find(date)
        if start_index == -1:
            continue  # Skip if date not found in remaining content
        
        # Define the start of the section after the date
        section_start = start_index + len(date)
        
        # Define end of the section based on the next date or the end of content
        next_date_index = (
            content_after_toc.find(dates[i + 1], section_start) if i + 1 < len(dates) else -1
        )
        
        # If "Your current e-book ends on" appears, ignore content after it
        ebook_end_index = content_after_toc.find(ebook_end_marker, section_start)
        section_end = min(
            next_date_index if next_date_index != -1 else len(content_after_toc),
            ebook_end_index if ebook_end_index != -1 else len(content_after_toc)
        )
        
        # Extract section text
        section_text = content_after_toc[section_start:section_end].strip()
        
        # Split the section text into parts based on "* * *"
        parts = re.split(part_marker, section_text)
        parts = [part.strip() for part in parts if part.strip()]  # Remove empty parts
        # extract the name
        head = parts[0].split('\n')
        for line in head:
            if head_marker in line:
                name = line.split(head_marker)[1].strip()
        # if it is a solemnity or a feast, reformat
        if '–' in name:
            n,s = name.split('–')
            name = ' '.join(['The',s.strip(),'of',n.strip()])
            
        sections[name] = [date] + parts[:n_parts-1]
        # if there are two options, split them apart
        
        if len(parts) > n_parts:
            # Store the parts list under each date key
            sections[name] = [date] + parts[:n_parts-1]
            
            # extract the name for the second option
            head = parts[n_parts-1].split('\n')
            for line in head:
                if head_marker in line and line != head_marker:
                    name = line.split(head_marker)[1].strip()
            name = parts[n_parts-1].split('\n')[0].split(head_marker)[1].strip()
            # Store the parts list under each date key
            sections[name] = [date] + parts[:n_parts-1]
    
    return sections


def get_nonempty_lines(text,n=100):
    verses = []
    lines = text.split('\n')
    for line in lines:
        if len(line)>1:
            verses.append(line)
        if len(verses)>n:
            break
    return verses


def parse_psalm_universalis(ps,part):
    d = {}
    #separate into parts
    if ps == 'can':
        sep = 'Canticle'
    else:
        sep = 'Psalm'
    latin_part = part.split(sep)[0]
    english_part = part.split(sep)[1]
    
    #parse the latin part
    lines = get_nonempty_lines(latin_part)
    d[ps] = lines[0].strip('Canticum').strip('cf. ') #get the name of the psalm or canticle
    d[ps+' ant_lat'] = lines[-1]
    d[ps+' ant'] = ' '.join(d[ps+' ant_lat'].split()[:3]).strip(',')
    ps_name = ' '.join(lines[3].split()[:3])
    d[ps +' name'] = re.sub(r'^\d+\s*', '', ps_name)
    
    #parse the english part
    lines = get_nonempty_lines(english_part)
    if ps == 'can':
        d[ps+' title'] = lines[0].strip()
    else:
        d[ps+' title'] = sep + ' ' + lines[0].strip()
    
    d[ps+' ant_eng'] = lines[-1]
    
    if d[ps+' title']=='(Apocalypse 19)':
        d[ps +' name'] = 'Salus et glória'
    return d


def get_2nd_reading(parts):
    d = {}
    i = np.where(['Second Reading' in part for part in parts])[0][0]
    d['2read'] = get_nonempty_lines(parts[i].split('Second Reading')[1].split('Responsorium')[0])
    if 'Responsory' in parts[i]:
        d['2resp'] = get_nonempty_lines(parts[i].split('Responsory')[1])
    return d


def _norm_text(s):
    return unicodedata.normalize("NFC", s).strip().casefold()


def retrieve_hymn_text(d,hymn_dir):
    target = _norm_text(d['hymn'])
    files = os.listdir(hymn_dir)

    match = None
    for fn in files:
        stem, _ = os.path.splitext(fn)
        if _norm_text(stem) == target:
            match = fn
            break

    if match is None:
        for fn in files:
            if _norm_text(fn).startswith(target):
                match = fn
                break

    if match:
        with open(os.path.join(hymn_dir,match), 'r', encoding='utf-8') as file:
            d['hymn_text'] = [line.rstrip('\n') for line in file]
    else:
        print('hymn',d['hymn'],'not found')
    return d

def format_dropcap(line):
    words = line.split()
    #if the first word is markup, delete it
    if words[0].find('left')>=0:
        words.pop(0)
    if len(words[0]) == 1:
        cap = words[0]
        rest = words[1]
        words.pop(1)
    else:
        cap = words[0][0]
        rest = words[0][1:]
    words[0] = r'\lettrine[lines=3,nindent=0.5em,loversize=0.3]{' + cap + r'}{\uppercase{' + rest + r'}}'
    line = ' '.join(words)
    return line

def format_bigcap(line):
    words = line.split()
    #if the first word is markup, delete it
    if words[0].find('left')>=0:
        words.pop(0)
    if len(words[0]) == 1:
        cap = words[0]
        rest = words[1]
        words.pop(1)
    else:
        cap = words[0][0]
        rest = words[0][1:]
    words[0] = r'{\fontsize{43}{43}\selectfont ' + cap + r'}{\uppercase{' + rest + r'}}'
    line = ' '.join(words)
    return line


def format_pandi(pandi):
    for line in pandi:
        if line[:2]=='– ':
            resp = line.strip('– ')
            break
    
    prayers_and_intercessions = []
    prayers_and_intercessions.append(r"PRAYERS AND INTERCESSIONS\\")
    prayers_and_intercessions.append(r"The response is ...  \\")
    prayers_and_intercessions.append(r"\gresetinitiallines{0}")
    prayers_and_intercessions.append(r"{\justifying\gregorioscore[a]{antiphons/preces_response.gabc}}")
    prayers_and_intercessions.append(r'\textbf{{\fontspec{EBGaramond} ℟ }' + fr"{resp}"+r'}\\')
    
    # Process each line and add LaTeX formatting
    for line in pandi:  # Skip the first line as it's already used as the response
        if line.startswith('– '):
            prayers_and_intercessions.append(r'\textbf{{\fontspec{EBGaramond} ℟ }' + fr"{resp}"+r'}\\')
        elif '– ' in line:
            line1,line2 = line.split('– ')
            prayers_and_intercessions.append(fr"{line1}\\")
            prayers_and_intercessions.append(r'\textbf{{\fontspec{EBGaramond} ℟ }' + fr"{resp}"+r'}\\')
        else:
            prayers_and_intercessions.append(fr"{line}\\")
    return prayers_and_intercessions


def get_vespers_data_universalis(name,parts):
    d = {}
    d['name'] = name
    d['date_string'] = parts[0]
    text = parts[3].split('Hymn')[-2]
    d['hymn_text'] = get_nonempty_lines(text)[1:]
    d['hymn'] = ' '.join(d['hymn_text'][0].split()[:3])
    text = parts[3].split('Hymn')[-1]
    d['hymn_text_eng'] = get_nonempty_lines(text)
    
    #psalm A
    d.update(parse_psalm_universalis('ps A',parts[4]))
    d.update(parse_psalm_universalis('ps B',parts[5]))
    #remove name if part B is a continuation of the same psalm
    ps_num_A = d['ps A'].split(':')[0]
    ps_num_B = d['ps B'].split(':')[0]
    if ps_num_B == ps_num_A:
        d['ps B name'] = ''
    d.update(parse_psalm_universalis('can',parts[6]))
    
    text = parts[7].split('Scripture Reading')[1]
    d['chap'] = get_nonempty_lines(text)
    d['chap'].insert(1,'') #to fix formatting later on
    
    text = parts[8].split('Short Responsory')[1]
    d['response'] = get_nonempty_lines(text)
    
    text = parts[9]
    d['mag antiphon'] = get_nonempty_lines(text,3)[2]
    d['mag ant'] = ' '.join(d['mag antiphon'].split()[:3])
    
    text = parts[9].split('Canticle')[1]
    d['mag ant_eng'] = get_nonempty_lines(text,3)[2]
    
    text = parts[10].split('Prayers and intercessions')[1]
    d['pandi'] = get_nonempty_lines(text)
    
    text = parts[12].split('Amen.')[1]
    d['conc'] = get_nonempty_lines(text)+['Amen.']

    return d

def fix_filenames(antiphon_dir):
    replacements_dict = {
        "á": "á",
        "í": "í",
        "é": "é",
        "ó": "ó",
        "ú": "ú",
        " ": "_",
        ",": "",
        "8g": "8G"
    }
    fns = fnmatch.filter(os.listdir(antiphon_dir), '*.gabc')
    for i, fn in zip(range(len(fns)),fns):
        fn_new = replace_text_simple(fn, replacements_dict)
        if fn != fn_new:
            os.rename(os.path.join(antiphon_dir,fn), os.path.join(antiphon_dir,fn_new))
            print('renaming ',fn)
    return None

def replace_text_simple(original_text, replacements):
    modified_text = original_text
    for old, new in replacements.items():
        modified_text = modified_text.replace(old, new)
    return modified_text


def format_hymn_tex(hymn_text):
    print(hymn_text)
    verses = split_list(hymn_text, '')
    nv = int(len(verses)/2)
    if nv*2!= len(verses): print('found',len(verses),'wrong number of verses!')
    verses_latin = [r'\newline '.join(verse) for verse in verses[:nv]]
    verses_english = [r'\newline '.join(verse) for verse in verses[nv:]]
    ht = []
    ht.append(r'\begin{longtable}{>{\raggedright\arraybackslash}p{0.45\textwidth} >{\raggedright\arraybackslash}p{0.5\textwidth}}')
    for i in range(nv):
        ht.append(r'{\textsc{'+str(i+1)+'} ' + verses_latin[i] + r' \newline '\
                  + r'} & ' \
                  + r'{\textsc{'+str(i+1)+r'} '+ verses_english[i] + r'}\\')
    ht.append(r'\end{longtable}')
    return ht

  
    
def split_list(input_list, separator):
    result = []
    current_sublist = []

    for item in input_list:
        if item == separator:
            # Add the current sublist to the result list
            result.append(current_sublist)
            # Start a new sublist
            current_sublist = []
        else:
            # Add the item to the current sublist
            current_sublist.append(item)

    # Add the last sublist (after the last separator, if any)
    result.append(current_sublist)

    return result

def _normalize_for_match(text):
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    no_marks = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    lowered = no_marks.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
    return re.sub(r"_+", "_", cleaned).strip("_")

def _first_phrase(antiphon_name):
    match = re.match(r"([^,\.]+?)(?:[,\.]|$)", antiphon_name.strip())
    if match:
        return match.group(1).strip()
    return antiphon_name.strip()

def get_antiphon_tex(antiphon_dir,antiphon_name,handout=False,mag=False,determine_tone=False,hymn=False):
    raw_name = antiphon_name
    antiphon_name = antiphon_name.replace(' ','_')
    antiphon_name = antiphon_name.replace(',','')
    antiphon_name = antiphon_name.replace(':','')
    fns = sorted(fnmatch.filter(os.listdir(antiphon_dir), antiphon_name+'*.gabc'))

    # Fallback: normalized robust matching for Unicode composition / punctuation differences
    if len(fns) == 0:
        phrase = _first_phrase(raw_name)
        phrase_norm = _normalize_for_match(phrase)
        words = [w for w in phrase_norm.split('_') if w]
        first_words = words[:4]

        all_gabc = [fn for fn in os.listdir(antiphon_dir) if fn.endswith('.gabc')]
        best_file = None
        best_score = -1
        for fn in all_gabc:
            stem_norm = _normalize_for_match(os.path.splitext(fn)[0])
            score = 0
            if phrase_norm and phrase_norm in stem_norm:
                score += 10
            for w in first_words:
                if w in stem_norm:
                    score += 1
            if score > best_score:
                best_score = score
                best_file = fn

        if best_file and best_score >= max(2, len(first_words) // 2):
            fns = [best_file]

    if len(fns)>0:
        ant_tone = fns[0].split('-')[-1].split('.')[0]
        if handout:
            fn = os.path.join(antiphon_dir,fns[0].split('-')[-1])
            ant_tex = r'{\justifying\gregorioscore[a]{' + fn + '}}'
            #ant_tex = r'{\justifying\begin{minipage}[t]{0.48\linewidth}\gregorioscore[a]{' + fn + r'}\end{minipage}}\\'
        else:
            fn = os.path.join(antiphon_dir,fns[0])
            ant_tex = r'{\justifying\gregorioscore[a]{' + fn + '}}'
    else:
        if mag:
            print('missing magnificat antiphon: ',antiphon_name)
        elif hymn:
            print('missing hymn: ',antiphon_name)
        else:
            print('missing antiphon: ',antiphon_name)
        ant_tex = ''
        ant_tone = ''
    if determine_tone:
        return ant_tex, ant_tone
    else:
        return ant_tex

def get_psalm_file(psalm_dir,psalm,fix_lord=True,tex=False):
    pd = os.path.join(psalm_dir,'psalm_texts')
    ptx = []
    psalm = psalm.replace('-','*')+'*'
    psalm = psalm.replace(':',';')
    fns = fnmatch.filter(os.listdir(pd),psalm)
    if len(fns)>0:
        default_tone = fns[0].split('_')[-1].split('.')[0]
        with open(os.path.join(pd,fns[0]), 'r') as file:
            ptx = [line.rstrip() for line in file]
    if fix_lord:
        ptx = format_lord(ptx,tex = tex)
    if len(ptx)==0:
        print('cant find psalm',psalm)
        default_tone = '1a'
    return ptx, default_tone


def format_lord(lines,tex=False):
    if tex:
        for i in range(len(lines)):
            lines[i] = lines[i].replace('LORD', r'\textsc{Lord}')
            lines[i] = lines[i].replace('LÓRD', r'\textsc{Lórd}')
            lines[i] = lines[i].replace('Lᴏʀᴅ', r'\textsc{Lord}')
            lines[i] = lines[i].replace('Lóʀᴅ', r'\textsc{Lórd}')
    else:
        for i in range(len(lines)):
            lines[i] = lines[i].replace('LÓRD', '<span class="small-caps">Lórd</span>')
            lines[i] = lines[i].replace('LORD', '<span class="small-caps">Lord</span>')
    return lines    


def replace_character(string, p, c):
    if p < 0 or p >= len(string):
        raise IndexError("Position is out of the string's range")
    # Create a new string with the character replaced
    new_string = string[:p] + c + string[p+1:]
    return new_string

def format_psalm_tex(psalm_text,tone_num,drop_cap=False,handout=False):
    accents_in_tone = {'1':(2,1),'2':(1,1),'3':(2,1),'4':(1,1),'5':(1,2),'6':(2,1),'7':(2,2),'8':(1,1),'D':(1,1),'2*a':(1,1)}
    prec_in_tone = {'1':(0,2),'2':(0,1),'3':(0,1),'4':(2,3),'5':(0,0),'6':(0,2),'7':(0,0),'8':(0,2),'D':(3,1),'2*a':(2,3)}
    n_accents = accents_in_tone[tone_num]
    n_preceding = prec_in_tone[tone_num]
    psalm_tex = []
    n = len(psalm_text)
    if drop_cap:
        words = typeset_verse(psalm_text[0],accents=n_accents,prec=n_preceding,handout=handout).split()
        if words[0].find('\\')>=0:
            words.pop(0)
        if len(words[0]) == 1:
            cap = words[0]
            rest = words[1]
            words.pop(1)
        else:
            cap = words[0][0]
            rest = words[0][1:]
        words[0] = r'\lettrine[lines=3,nindent=0.5em,loversize=0.3]{' + cap + r'}{\uppercase{' + rest + r'}}'
        psalm_tex.append(' '.join(words) + r'\\')
    else:
        line = typeset_verse(psalm_text[0],accents=n_accents,prec=n_preceding,handout=handout) + r'\\'
        psalm_tex.append(line)
    for i in range(n)[1:-1]:
        line = typeset_verse(psalm_text[i],accents=n_accents,prec=n_preceding,handout=handout) + r'\\'
        #make sure we are indented far enough to avoid the drop. cap
        #if line == r'\\': line =r''
        psalm_tex.append(line)
    line = typeset_verse(psalm_text[-1],accents=n_accents,prec=n_preceding,handout=handout)
    if line == r'\\': line =r''
    psalm_tex.append(line)
    return psalm_tex


def remove_first_accent(string,pattern):
    accents_dict = {
        "á": "a",
        "á": "a",
        "í": "i",
        "í": "i",
        "é": "e",
        "é": "e",
        "ó": "o",
        "ó": "o",
        "ú": "u",
        "ú": "u"}
    matches = re.finditer(pattern, string)
    positions = [match.start() for match in matches]
    if len(positions)>0:
        pos = positions[0]
        c = accents_dict[string[pos]] #find the replacement character
        return replace_character(string, pos, c)
    else:
        #print('cant find any accented syllables in string',string)
        return string


def reduce_psalm_accents(psalm_text,tone_num,bf=False,handout=False):
    accents_in_tone = {'1':(2,1),'2':(1,1),'3':(2,1),'4':(1,1),'5':(1,2),'6':(2,1),'7':(2,2),'8':(1,1),'D':(1,1),'2*a':(1,1)}
    prec_in_tone = {'1':(0,2),'2':(0,1),'3':(0,1),'4':(2,3),'5':(0,0),'6':(0,2),'7':(0,0),'8':(0,2),'D':(3,1),'2*a':(2,3)}
    s,e = accents_in_tone[tone_num]
    rem_start_acc = s==1
    rem_end_acc = e==1
    
    # The list of characters to search for
    characters = "áéíóú"
    # Create a regex pattern to match any of these characters
    pattern = f"[{characters}]"
    new_psalm_text = []
    for line in psalm_text:
        start,end = line.split("*")
        if rem_start_acc:
            start = remove_first_accent(start,pattern)
        if rem_end_acc:
            end = remove_first_accent(end,pattern)
        if bf:
            new_line = typeset_verse(line,accents_in_tone[tone_num],prec_in_tone[tone_num],handout=handout)
        else:
            new_line = '*'.join([start,end])
        new_psalm_text.append(new_line)
    return new_psalm_text

def make_vespers_script_latex(d,header,fn_script,psalm_dir,antiphon_dir):
    #hymn_tone = get_antiphon_tex(hymn_dir,d['hymn_text'][0].strip().replace(',',''),handout=False)

    psalms = []
    for ps in ['ps A','ps B','can']:
        psalm_text_raw,default_tone = get_psalm_file(psalm_dir,d[ps],tex=True)
        # if there is an antiphon file, use the tone from that
        psalm_antiphon,ant_tone = get_antiphon_tex(antiphon_dir,d[ps+' ant'],determine_tone=True)
        if psalm_antiphon == '':
            #see if there is a tone for the script (with beginng notes)
            script_tone = default_tone+'_script'
            fns = fnmatch.filter(os.listdir(antiphon_dir), script_tone+'.gabc')
            if len(fns)>0:
                default_tone = script_tone
            else:
                print('cant find script tone, using handout tone instead for',default_tone)
            tone_img = get_antiphon_tex(os.path.join(antiphon_dir,'full_tone'),default_tone,handout=False)
            psalm_antiphon = tone_img + format_bigcap(d[ps +' ant_lat'])
        #reduce accents according to the tone:
        if ant_tone == '':
            tone_num = default_tone[0]
        else:
            tone_num = ant_tone[0]
            if ant_tone == '2*a':
                tone_num = ant_tone
        #psalm_text = reduce_psalm_accents(psalm_text_raw,tone_num)
        psalm_tex = format_psalm_tex(psalm_text_raw,tone_num,drop_cap=False)
        
        psalms.append([r'\newpage',r'\textbf{' + d[ps] + r'} \hfill \textit{' + d[ps + ' name'] + r'}\\',\
                       r'\vspace{6pt}', psalm_antiphon,r'\vspace{12pt}'] + psalm_tex + [r'\leftskip=0pt'])
        '''psalms.append([r'\textbf{'+d[ps]+r'}\\',\
                   r'\emph{'+d[ps +' name']+r'}\vspace{12pt}\\', \
                   psalm_antiphon]\
                  + psalm_tex)'''
    
    chapter = []
    chapter.append(r'SCRIPTURE READING\\')
    chapter.append(r'\emph{' + d['chap'][0].strip() + r'}\\')
    chapter.append(format_dropcap(d['chap'][2])+ r'\\')
    for i in range(len(d['chap']))[3:]:
        chapter.append(d['chap'][i]+ r'\\')

    lines = d['response'][:]
    response_text = lines[0].replace('–','').replace('—','').strip()
    response = []
    # Start with the heading
    response = [r"SHORT RESPONSORY\\"]
    # Step 1: Add the line at the top
    #response.append(f"The response is: {response_text}\\\\")
    for line in lines:
        if line != '':
            if '– ' in line or '— ' in line:
                response.append(r'\textbf{{\fontspec{EBGaramond} ℟ }'+ response_text + r'}\\')
                response.append(r"\vspace{12pt}")

            else:
                response.append(line + r'\\')
    
    second_reading = []
    second_reading.append(r'SECOND READING\\')
    second_reading.append(r'\emph{' + d['2read'][0] + r'}\\')
    #second_reading.append(r'\emph{' + d['2read'][1].strip() + '}')
    second_reading.append(r'\begin{multicols}{2}')
    drop_cap = True #drop cap the first line only
    for i in range(len(d['2read']))[2:]:#ignore the description
        second_reading.append('')
        if drop_cap and len(d['2read'][i])>1:
            drop_cap = False
            second_reading.append(format_dropcap(d['2read'][i]))
        else:
            second_reading.append(d['2read'][i])
    second_reading.append(r'\end{multicols}')

    second_response = [r'{\fontspec{EBGaramond} ℣ }In nomine Patris, et Filii, et Spiritus Sancti.\\',r'\textbf{{\fontspec{EBGaramond} ℟ }Amen.}']

    ant = get_antiphon_tex(antiphon_dir,d['mag ant'],mag=True)

    if ant == '':
        magnificat_antiphon = [r'MAGNIFICAT ANTIPHON','',r'\vspace{12pt}{\justifying\gregorioscore[a]{'+antiphon_dir+r'/Mag_tone.gabc}}',d['mag antiphon']+r'\\']
    else:
        magnificat_antiphon = [r'MAGNIFICAT ANTIPHON\\',r'\vspace{12pt}'+ant]

    lines = d['pandi'][:]
    # Define the response as the first line of text
    resp = lines[-2]

    # LaTeX formatted output
    prayers_and_intercessions = format_pandi(d['pandi'])
        
    conclusion = d['conc']
    for i,line in enumerate(d['conc']):
        if 'Or:' in line:
            conclusion = d['conc'][:i]
            break
    conclusion = [line+r'\\' for line in conclusion]
    

    dismissal = [r'DISMISSAL\\',r'\vspace{12pt}',r'{\justifying\gregorioscore[a]{'+antiphon_dir+'/dismissal}}']
    footer = [r'\end{document}']

    script = header + [r'\pagestyle{fancy}',r'\fancyhf{}',r'\renewcommand{\headrulewidth}{0pt}',r'\fancyfoot[C]{'+d['name']+'}',r'{\fontsize{18}{20}\selectfont']\
        + psalms[0] + [r'\newpage'] + psalms[1] + [r'\newpage'] + psalms[2] + [r'\newpage']\
        + chapter +[r'\vspace{24pt}'] + response + [r'\vspace{24pt}'] + second_reading + [r'\vspace{24pt}'] + second_response + [r'\newpage']\
        + magnificat_antiphon + [r'\vspace{24pt}'] + prayers_and_intercessions +[r'\newpage'] \
        + [r'CONCLUSION',''] + conclusion +[r'\vspace{24pt}']+ dismissal + footer
    
    with open(fn_script, 'w') as file:
        [file.write(line + '\n') for line in script]
    return




def make_vespers_handout_latex(d,header,fn_handout,psalm_dir,antiphon_dir):
    hymn = format_hymn_tex(d['hymn_text'])
    hymn_tone = get_antiphon_tex(antiphon_dir,d['hymn_text'][0].strip().replace(',',''),handout=True,hymn=True)

    psalms = []
    for ps in ['ps A','ps B','can']:
        psalm_text_raw,default_tone = get_psalm_file(psalm_dir,d[ps],tex=True)
        
        # if there is an antiphon gabc file, use the mode from that one instead of the default
        psalm_antiphon,ant_tone = get_antiphon_tex(antiphon_dir,d[ps+' ant'],determine_tone=True)
        if psalm_antiphon == '':
            tone = get_antiphon_tex(antiphon_dir,default_tone,handout=True)
        else:
            tone = get_antiphon_tex(antiphon_dir,ant_tone,handout=True)
        
        #reduce accents according to the tone:
        if ant_tone == '':
            tone_num = default_tone[0]
        else:
            tone_num = ant_tone[0]
            if ant_tone == '2*a':
                tone_num = ant_tone
        #psalm_text = reduce_psalm_accents(psalm_text_raw,tone_num)
        psalm_tex = format_psalm_tex(psalm_text_raw,tone_num,drop_cap=True,handout=True)
        
        psalms.append([r'\newpage',r'\textbf{' + d[ps] + r'} \hfill \textit{' + d[ps + ' name'] + r'}\\',\
                       r'\begin{multicols}{2}',\
                       d[ps + ' ant_lat'] + r'\\',\
                       tone,\
                       r'\newcolumn',\
                       d[ps + ' ant_eng'] + r'\\',\
                       r'\end{multicols}'\
                       r'\begin{multicols}{2}',\
                      ] + psalm_tex + [r'\\',r'\leftskip=0pt', r'\end{multicols}'])
    
    lines = d['response'][:]
    response_text = lines[0].replace('–','').replace('—','').strip()
    lines = d['pandi'][:]
    # Define the response as the first line of text
    resp_pandi = lines[-2]

    responses = [
            r'\begin{multicols}{2}',
            r'\textbf{RESPONSES} \\',
            r'\textit{First reading}\\',
            r'\textbf{\Responsorium ' + response_text + r'}\\',
            r'\newcolumn', r'\textit{Prayers and Intercessions}\\',
            r'\textbf{\Responsorium ' + resp_pandi + '}',
            r'\end{multicols}'
        ]

    mag_ant = [
            r'\begin{multicols}{2}',
            r'\textbf{MAGNIFICAT ANTIPHON} \\',
            d['mag antiphon'],
            r'\newcolumn',
            d['mag ant_eng'],
            r'\end{multicols}'
        ]
    footer = [r'\vfill',r'\begin{center}',r'\textit{\small '+d['name']+'}',r'\end{center}','}',r'\end{document}']

    handout =  header + [r'\setcounter{page}{3}',r'{\fontsize{18}{20}\selectfont']\
        + [hymn_tone] + hymn + ['}',r'\grechangedim{spacelinestext}{8mm}{scalable}',r'{\fontsize{20}{22}\selectfont']\
        + psalms[0] + psalms[1]  +  psalms[2] + responses + mag_ant + ['']\
        + footer
    with open(fn_handout, 'w') as file:
        [file.write(line + '\n') for line in handout]
    return


import re

def has_accented_vowel(s):
    # Covers acute, grave, circumflex, diaeresis, tilde, macron vowels
    accented_vowels = "áéíóúàèìòùâêîôûäëïöüãõāēīōūýÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÃÕĀĒĪŌŪ"
    return any(ch in accented_vowels for ch in s)


def replace_character(string, p, c):
    if p < 0 or p >= len(string):
        raise IndexError("Position is out of the string's range")
    # Create a new string with the character replaced
    new_string = string[:p] + c + string[p+1:]
    return new_string

def replace_vowels_with_precomposed(text):
    replacements = {
        'á': 'á', 'é': 'é', 'í': 'í', 'ó': 'ó', 'ú': 'ú', 'ý': 'ý',
        'Á': 'Á', 'É': 'É', 'Í': 'Í', 'Ó': 'Ó', 'Ú': 'Ú', 'Ý': 'Ý'
    }

    pattern = "|".join(replacements.keys())
    
    def replace(match):
        return replacements[match.group(0)]

    return re.sub(pattern, replace, text)

def remove_accents(rawstring):
    string = replace_vowels_with_precomposed(rawstring)
    accents_dict = {
        "á": "a",
        "á": "a",
        "í": "i",
        "Í": "I",
        "Í": "I",
        "í": "i",
        "É": "E",
        "é": "e",
        "é": "e",
        "ó": "o",
        "ó": "o",
        "ú": "u",
        "ú": "u",
        "ý": "y"}
    characters = 'áéíóúýÁÉÍÓÚÝ'
    pattern = f"[{characters}]"
    matches = re.finditer(pattern, string)
    positions = [match.start() for match in matches]
    for pos in positions:
        c = accents_dict[string[pos]] #find the replacement character
        string = replace_character(string, pos, c)
    return string, positions

import bisect

def bounds(data, x):
    index = bisect.bisect(data, x)
    if index == 0:
        return (None, data[0])
    elif index == len(data):
        return len(data)
    else:
        return index

import pronouncing
import pyphen
import re

# Initialize Pyphen fallback
dic = pyphen.Pyphen(lang='en_US')

# Set of vowel phonemes in CMU dictionary (stress digits stripped)
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
          "IH", "IY", "OW", "OY", "UH", "UW"}

def clean_word(word):
    # Remove leading/trailing punctuation but keep internal hyphens/apostrophes
    return re.sub(r"(^[^\w']+|[^\w']+$)", "", word)


def syllabify_pronouncing(rawword):
    word = clean_word(rawword.lower().strip())
    """Try to syllabify using pronouncing with vowel phoneme grouping."""
    phones = pronouncing.phones_for_word(word)
    if not phones:
        return None  # Not in CMU dictionary

    # Take first pronunciation
    phonemes = phones[0].split()
    syllables_phonetic = []
    current = []

    for ph in phonemes:
        current.append(ph)
        # When we hit a vowel phoneme, end of syllable
        if re.sub(r"\d", "", ph) in VOWELS:
            syllables_phonetic.append(current)
            current = []
    if current:
        syllables_phonetic[-1].extend(current)

    # Approximate mapping back to characters
    syllable_lengths = [len(s) for s in syllables_phonetic]
    total_len = sum(syllable_lengths)
    letter_counts = [round(len(word) * l / total_len) for l in syllable_lengths]

    # Adjust to make sure total matches
    while sum(letter_counts) < len(rawword):
        letter_counts[-1] += 1
    while sum(letter_counts) > len(rawword):
        letter_counts[-1] -= 1

    syllables = []
    start = 0
    for count in letter_counts:
        end = start + count
        syllables.append(rawword[start:end])
        start = end
    return syllables



def split_syllables(word):
    """Combined syllabifier using pyphen + pronouncing (phonetic) fallback."""
    if not word:
        return []
    result = dic.inserted(word).split('-')
    rphone = syllabify_pronouncing(word)
    if len(result)==1 and rphone:
        if len(rphone)>1:
            result = rphone
    return result


def typeset_pointed_psalm(verse,n_accents,n_preceding):
    dic = pyphen.Pyphen(lang='en_UK')
    verse,accent_positions = remove_accents(verse)
    accent_positions = accent_positions[-n_accents:] #remove extra accents not being used and list them in reverse order
    
    words = verse.split(' ')
    syllables = []
    syllable_positions = []
    pos = 0
    i = 0
    for word in words:
        #word_syl = dic.inserted(word).split('-')
        word_syl = split_syllables(word)
        for syllable in word_syl:
            pos += len(syllable)
            syllables.append(syllable)
            syllable_positions.append(pos)
        pos += 1
    
    for accent_position in accent_positions[::-1]:
        i = bisect.bisect(syllable_positions, accent_position)
        verse = verse[:syllable_positions[i]] + '}' + verse[syllable_positions[i]:]   
        if i!=0:
            verse = verse[:syllable_positions[i-1]] + r'\textbf{' + verse[syllable_positions[i-1]:]
        else:
            verse = r'\textbf{' + verse
        
    if n_preceding>0:
        end = i-1
        start = end-n_preceding
        verse = verse[:syllable_positions[end]] + '}' + verse[syllable_positions[end]:]
        verse = verse[:syllable_positions[start]] + r'\textit{' + verse[syllable_positions[start]:]
    return verse

def typeset_verse(verse,accents=(1,1),prec=(0,0),handout=False):
    firstpart,secondpart = verse.split('*')
    typeset_first = typeset_pointed_psalm(firstpart.strip(),accents[0],prec[0])
    if "†" in typeset_first and not handout:
        p = typeset_first.find("†")
        typeset_first = replace_character(typeset_first, p, r"† \\ \leftskip=0.5em ")
    typeset_second = typeset_pointed_psalm(secondpart.strip(),accents[1],prec[1])
    if handout:
        typeset_verse = typeset_first + r' * ' + typeset_second + r'\vspace{0.4em}'
    else:
        typeset_verse = r'\leftskip=0pt ' + typeset_first + r' *\\ \leftskip=1em ' + typeset_second + r'\vspace{0.3em}'
    return typeset_verse
