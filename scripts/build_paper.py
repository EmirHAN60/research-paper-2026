"""Build the illustrated manuscript and submission PDF from audited saved results."""
from __future__ import annotations
import argparse
import html
import json
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Image


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def number(x, signed=False):
    return 'not estimable' if x is None else format(x, '+.1f' if signed else '.1f')


def find(rows, provider, mode, origins=None):
    return next(r for r in rows if r['provider']==provider and r.get('mode',r.get('comparison'))==mode and (origins is None or r['origins']==origins))


def interval(row):
    return f"{number(row['median_delta_ms'],True)} [{number(row['ci95_low_ms'],True)}, {number(row['ci95_high_ms'],True)}]"


def mode_name(mode):
    return {'udp':'UDP','doh_fresh':'DoH fresh','doh_warm':'DoH established','doh_reused':'DoH established'}[mode]


def check_summary(summary, label):
    if summary.get('warnings'):
        raise ValueError(f'{label}: unresolved analysis warnings')
    for audit in summary.get('validation',{}).values():
        if isinstance(audit,dict) and (audit.get('validation_errors') or audit.get('transport_mismatches')):
            raise ValueError(f'{label}: saved-data audit failed')
    if summary['counts']['lookup_measurements']!=1800 or summary['counts']['pages']!=360:
        raise ValueError(f'{label}: the manuscript expects the complete 1800/360 collection')


def lookup_table(summary):
    lines=['Table 1. Original-session lookup latency and paired differences in milliseconds.',
           '', '| Provider | Transport | Success / attempts | Median | p95 | Paired difference [95% interval] |',
           '|---|---|---:|---:|---:|---|']
    for provider in ['cloudflare','google']:
        for mode in ['udp','doh_fresh','doh_warm']:
            row=find(summary['lookup_summary'],provider,mode)
            effect='Baseline' if mode=='udp' else interval(find(summary['lookup_paired'],provider,mode))
            lines.append(f"| {provider.title()} | {mode_name(mode)} | {row['succeeded']}/{row['attempted']} | {number(row['median_ms'])} | {number(row['p95_ms'])} | {effect} |")
    lines.extend(['','Note. Positive differences indicate slower DoH. Brackets give descriptive within-window paired-bootstrap intervals; they are not population guarantees.'])
    return '\n'.join(lines)


def make_tokens(root, original, repeat, robustness, refs, profile):
    env=load(root/'data/environment.json');renv=load(root/'data/replication-2026-11-19/environment.json')
    browser=load_jsonl(root/'data/page-environment.jsonl')[0]
    rbrowser=load_jsonl(root/'data/replication-2026-11-19/page-environment.jsonl')[0]
    D=lambda p,m:find(original['lookup_paired'],p,m)
    R=lambda p,m:find(repeat['lookup_paired'],p,m)
    P=lambda p,m,o:find(original['page_paired'],p,m,o)
    RP=lambda p,m,o:find(repeat['page_paired'],p,m,o)
    original_bad=sum(r['failed'] for r in original['lookup_summary']+original['page_summary'])
    repeat_bad=sum(r['failed'] for r in repeat['lookup_summary']+repeat['page_summary'])
    gw=[r['median_delta_ms'] for r in original['window_effects'] if r['experiment']=='lookup' and r['provider']=='google' and r['comparison']=='doh_warm']
    cf=[r['median_delta_ms'] for r in original['window_effects'] if r['experiment']=='lookup' and r['provider']=='cloudflare' and r['comparison']=='doh_warm']
    rgw=[r['median_delta_ms'] for r in repeat['window_effects'] if r['experiment']=='lookup' and r['provider']=='google' and r['comparison']=='doh_warm']
    clustered=next(r for r in robustness['comparisons'] if r['experiment']=='lookup' and r['provider']=='google' and r['comparison']=='doh_warm')
    all_fresh=[find(s['lookup_paired'],p,'doh_fresh')['median_delta_ms'] for s in [original,repeat] for p in ['cloudflare','google']]
    bibliography=[]
    for paragraph in (root/'docs/REFERENCES.md').read_text(encoding='utf-8').split('\n\n'):
        if re.search(r'\(\d{4}',paragraph) and ('https://doi.org/' in paragraph or 'https://www.w3.org/' in paragraph):
            bibliography.append(re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\2',paragraph.strip()))
    if len(bibliography)!=len(refs):raise ValueError('Structured and formatted bibliography counts differ')
    fresh_conclusion='Fresh HTTP/2 DoH was slower than UDP at the pooled paired median for both providers on both dates.' if all(x is not None and x>0 for x in all_fresh) else 'Fresh-session comparisons depended on the provider and collection date.'
    tokens={
        'IDENTITY':f"{profile['author_name']}\n\nStudent ID: {profile['student_id']}\n\n{profile['institution']}\n\n{profile['department']}\n\nArchitecture of Computers (CII3SE003CI), 2026/2027",
        'REPOSITORY_URL':profile['repository_url'],
        'REPLICATION_COUNTS':f"{repeat['counts']['lookup_measurements']:,} lookups and {repeat['counts']['pages']:,} navigations",
        'ABSTRACT_FRESH':f"{number(D('cloudflare','doh_fresh')['median_delta_ms'])} ms for Cloudflare and {number(D('google','doh_fresh')['median_delta_ms'])} ms for Google",
        'ABSTRACT_WARM':f"{number(D('cloudflare','doh_warm')['median_delta_ms'],True)} ms and {number(D('google','doh_warm')['median_delta_ms'],True)} ms, respectively",
        'ABSTRACT_REPLICATION':f"The repeat session yielded established lookup differences of {number(R('cloudflare','doh_warm')['median_delta_ms'],True)} and {number(R('google','doh_warm')['median_delta_ms'],True)} ms. Google's established contrast changed sign across windows on both dates.",
        'ENVIRONMENT':f"Both sessions ran on a Windows {env['release']} {env['arch']} host reporting {env['cpu_model'].strip()}, {env['logical_cpus']} logical processors and {number(env['total_memory_gib'])} GiB RAM. Node.js versions were {env['node']} and {renv['node']}; Chrome versions were {browser['browser']} and {rbrowser['browser']}, with Playwright {browser['playwright']}. Full session metadata is retained. Access medium, ISP, paths and background traffic were not characterized. No CPU counters or energy measurements were taken.",
        'COMPLETENESS':f"Each date contains 1,800 lookup attempts and 360 navigation attempts, plus separate priming records. The original and repeat sessions recorded {original_bad} and {repeat_bad} failed measured attempts, respectively. Together they contain 3,600 measured lookups and 720 navigations. Packet and connection-treatment audits passed for the retained results. Preparatory and screenshot-only runs are excluded.",
        'LOOKUP_TABLE':lookup_table(original),
        'PRIMARY_LOOKUP_RESULTS':f"Fresh-DoH median paired differences were {interval(D('cloudflare','doh_fresh'))} ms for Cloudflare and {interval(D('google','doh_fresh'))} ms for Google. Established differences were {interval(D('cloudflare','doh_warm'))} and {interval(D('google','doh_warm'))} ms. Fresh setup and established querying therefore give substantially different contrasts.",
        'WINDOW_RESULTS':f"Google's original established-session window differences were {', '.join(number(x,True) for x in gw)} ms. Cloudflare's were {', '.join(number(x,True) for x in cf)} ms. The Google contrast changed sign even though its pooled interval was positive. This is observed heterogeneity, not evidence identifying a cache or routing transition.",
        'REPLICATION_RESULTS':f"On 19 November, fresh-session differences were {interval(R('cloudflare','doh_fresh'))} ms for Cloudflare and {interval(R('google','doh_fresh'))} ms for Google. Established-session contrasts were {interval(R('cloudflare','doh_warm'))} and {interval(R('google','doh_warm'))} ms. Google's repeat-session window effects were {', '.join(number(x,True) for x in rgw)} ms, again changing sign. Figure 3 retains the dates separately instead of averaging their network contexts.",
        'ROBUSTNESS_RESULTS':f"For the original Google established contrast, whole-domain resampling gave [{number(clustered['domain_cluster_ci95_low_ms'],True)}, {number(clustered['domain_cluster_ci95_high_ms'],True)}] ms. This alternative interval remains narrow despite window medians ranging from {number(min(gw),True)} to {number(max(gw),True)} ms. Changing the resampling unit therefore does not remove the temporal sensitivity. All valid values remain included.",
        'PAGE_RESULTS':f"Original fresh-session page differences for one/eight hostnames were {number(P('cloudflare','doh_fresh',1)['median_delta_ms'])}/{number(P('cloudflare','doh_fresh',8)['median_delta_ms'])} ms for Cloudflare and {number(P('google','doh_fresh',1)['median_delta_ms'])}/{number(P('google','doh_fresh',8)['median_delta_ms'])} ms for Google. Established-session effects were {number(P('cloudflare','doh_reused',1)['median_delta_ms'],True)}/{number(P('cloudflare','doh_reused',8)['median_delta_ms'],True)} and {number(P('google','doh_reused',1)['median_delta_ms'],True)}/{number(P('google','doh_reused',8)['median_delta_ms'],True)} ms, respectively.",
        'REPLICATION_PAGE_RESULTS':f"On the repeat date, established-session page differences for one/eight hostnames were {number(RP('cloudflare','doh_reused',1)['median_delta_ms'],True)}/{number(RP('cloudflare','doh_reused',8)['median_delta_ms'],True)} ms for Cloudflare and {number(RP('google','doh_reused',1)['median_delta_ms'],True)}/{number(RP('google','doh_reused',8)['median_delta_ms'],True)} ms for Google. Each effect uses matched complete page pairs; all-attempt counts remain visible in the extended results.",
        'CONCLUSION_RESULTS':fresh_conclusion+' Established-session results were smaller and dependent on the sampled context.',
        'REFERENCES':'\n\n'.join(bibliography),
    }
    tokens.update(load(root/'docs/literature_tokens.json'))
    return tokens


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def extended_results(root, original, repeat):
    lines=['# Extended results and figure guide','',
           'All values below are generated from the saved, audited measurements. Dates are analyzed separately. Positive paired differences indicate slower DoH. A paired median is not the difference of marginal medians. Failures remain in attempt counts; successful-latency estimates condition on success.','',
           '| Date | Measured lookup attempts | Page attempts | Lookup priming records | Failed measured attempts |',
           '|---|---:|---:|---:|---:|']
    for date,s in [('2026-11-15',original),('2026-11-19',repeat)]:
        lines.append(f"| {date} | {s['counts']['lookup_measurements']} | {s['counts']['pages']} | {s['counts']['lookup_phase_counts']['prime']} | {sum(r['failed'] for r in s['lookup_summary']+s['page_summary'])} |")
    for date,s,folder in [('2026-11-15',original,'results'),('2026-11-19',repeat,'results/replication-2026-11-19')]:
        lines.extend(['',f'## Session {date}','','### Lookup distributions','',
                      '| Provider | Mode | Success / attempts | Median ms | IQR ms | p95 ms | Paired difference ms [95% interval] |',
                      '|---|---|---:|---:|---:|---:|---|'])
        for p in ['cloudflare','google']:
            for m in ['udp','doh_fresh','doh_warm']:
                r=find(s['lookup_summary'],p,m);effect='Baseline' if m=='udp' else interval(find(s['lookup_paired'],p,m))
                lines.append(f"| {p.title()} | {mode_name(m)} | {r['succeeded']}/{r['attempted']} | {number(r['median_ms'])} | {number(r['iqr_ms'])} | {number(r['p95_ms'])} | {effect} |")
        lines.extend(['','### Controlled page load distributions','',
                      '| Provider | Hostnames | Mode | Success / attempts | Median ms | p95 ms | Paired difference ms [95% interval] |',
                      '|---|---:|---|---:|---:|---:|---|'])
        for p in ['cloudflare','google']:
            for origins in [1,8]:
                for m in ['udp','doh_fresh','doh_reused']:
                    r=find(s['page_summary'],p,m,origins);effect='Baseline' if m=='udp' else interval(find(s['page_paired'],p,m,origins))
                    lines.append(f"| {p.title()} | {origins} | {mode_name(m)} | {r['succeeded']}/{r['attempted']} | {number(r['median_ms'])} | {number(r['p95_ms'])} | {effect} |")
        lines.extend(['','### Established lookup contrasts by window','',
                      '| Provider | Window | Matched pairs | Median paired difference ms |', '|---|---:|---:|---:|'])
        for r in s['window_effects']:
            if r['experiment']=='lookup' and r['comparison']=='doh_warm':lines.append(f"| {r['provider'].title()} | {r['window']} | {r['complete_pairs']} | {number(r['median_delta_ms'],True)} |")
        rb=load(root/folder/'robustness.json')
        lines.extend(['','### Dependence and sign sensitivity','',
                      '| Provider | Lookup contrast | Domain-cluster interval ms | Positive paired fraction | Window sign reversal |',
                      '|---|---|---|---:|---|'])
        for r in rb['comparisons']:
            if r['experiment']=='lookup':lines.append(f"| {r['provider'].title()} | {mode_name(r['comparison'])} | [{number(r['domain_cluster_ci95_low_ms'],True)}, {number(r['domain_cluster_ci95_high_ms'],True)}] | {100*r['positive_fraction']:.1f}% | {r['window_sign_reversal']} |")
        lines.extend(['','The cluster interval resamples ten observed hostname clusters. It is a secondary conditional sensitivity, not a solution to temporal dependence. Sign fractions describe matched samples and are not hypothesis-test p-values. All values are retained without trimming.','',
                      f'[Full primary summary](../{folder}/summary.json) · [Window effects](../{folder}/window_effects.csv) · [Leave-one-window-out](../{folder}/leave_one_window_out.csv) · [Domain effects](../{folder}/domain_effects.csv) · [Robustness details](../{folder}/robustness.json)'])
    lines.extend(['','## Figure guide',''])
    manifest=load(root/'figures/all_figures.json')
    for fig in manifest['figures']:
        # Both plot implementations expose the exported relative files in the manifest.
        name=fig.get('name',fig.get('stem',fig.get('title','Figure')))
        caption=fig.get('caption','')
        label=fig.get('date',fig.get('dataset',''))
        directory='../figures/' if fig.get('dataset') in ['original','cross-date','cross_date','comparison'] or fig.get('stem')=='cross_date_comparison' else '../figures/'+fig.get('dataset','')+'/'
        lines.extend([f'### {name} {label}','',caption,'',f"![{name} {label}]({directory}{name}.png)",'',f'[Vector PDF]({directory}{name}.pdf) · [SVG]({directory}{name}.svg)',''])
    lines.extend(['','## Reading the evidence','','The primary within-window intervals, per-domain intervals and window effects answer different questions. Neither a narrow pooled interval nor agreement between bootstrap choices establishes stability outside the observed network contexts. The strongest qualitative observation is the repeated change in sign of the Google established-session contrast across windows on both dates. It does not identify the cause.','',
                  'The browser fixture uses real DNS waiting and fixed local content. Its page metric is not native-browser or arbitrary-website performance. Runtime versions differ across dates; see [methods](METHODS.md) and [reproduction details](REPRODUCIBILITY.md).',''])
    (root/'docs/RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')


def inline(text):
    text=html.escape(text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'\*([^*]+)\*',r'<i>\1</i>',text)
    text=re.sub(r'`([^`]+)`',r'\1',text)
    def link(match):
        url=match[1];suffix=''
        while url and url[-1] in '.,;':suffix=url[-1]+suffix;url=url[:-1]
        return f'<link href="{url}" color="#183d5a">{url}</link>'+suffix
    text=re.sub(r'(https://[^\s<]+)',link,text)
    return text


def fonts():
    folder=Path('C:/Windows/Fonts')
    if (folder/'times.ttf').exists():
        for name,file in [('Paper','times.ttf'),('PaperBold','timesbd.ttf'),('PaperItalic','timesi.ttf'),('PaperBoldItalic','timesbi.ttf')]:pdfmetrics.registerFont(TTFont(name,str(folder/file)))
        pdfmetrics.registerFontFamily('Paper',normal='Paper',bold='PaperBold',italic='PaperItalic',boldItalic='PaperBoldItalic')
        return 'Paper','PaperBold'
    return 'Times-Roman','Times-Bold'


def render_pdf(markdown, root, profile):
    font,bold=fonts()
    body=ParagraphStyle('Body',fontName=font,fontSize=12,leading=24,firstLineIndent=36,allowWidows=0,allowOrphans=0)
    plain=ParagraphStyle('Plain',parent=body,firstLineIndent=0)
    heading=ParagraphStyle('Heading',fontName=bold,fontSize=12,leading=24,alignment=TA_CENTER,spaceBefore=10,keepWithNext=True)
    sub=ParagraphStyle('Subheading',parent=heading,alignment=0)
    title=ParagraphStyle('Title',parent=heading,fontSize=14,leading=20,spaceAfter=8)
    identity=ParagraphStyle('Identity',parent=plain,alignment=TA_CENTER,leading=20,spaceAfter=4)
    caption=ParagraphStyle('Caption',fontName=font,fontSize=10.5,leading=14,spaceBefore=5,spaceAfter=8)
    tablecap=ParagraphStyle('TableCaption',parent=caption,keepWithNext=True)
    cell=ParagraphStyle('Cell',fontName=font,fontSize=9.1,leading=12)
    cellhead=ParagraphStyle('CellHead',parent=cell,fontName=bold)
    reference=ParagraphStyle('Reference',parent=body,leftIndent=36,firstLineIndent=-36,spaceAfter=6)
    blocks=markdown.split('\n\n');story=[];abstract=False;refs=False;index=0
    while index<len(blocks):
        block=blocks[index].strip();index+=1
        if not block:continue
        if block.startswith('# '):story.append(Paragraph(inline(block[2:]),title));continue
        if block.startswith('## Evaluating'):story.append(Paragraph(inline(block[3:]),heading));continue
        if block.startswith('## '):
            name=block[3:];abstract=False
            if name=='References':refs=True;story.append(PageBreak())
            story.append(Paragraph(inline(name),heading));continue
        if block.startswith('### '):
            name=block[4:];abstract=name=='Abstract'
            if abstract:story.append(PageBreak())
            story.append(Paragraph(inline(name),heading if abstract else sub));continue
        image=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',block)
        if image:
            path=(root/image[2]).resolve()
            if not path.is_file() or not path.is_relative_to(root):raise ValueError('Missing or external figure '+str(path))
            picture=Image(str(path));ratio=picture.imageHeight/picture.imageWidth;picture.drawWidth=468;picture.drawHeight=468*ratio
            if picture.drawHeight>330:picture.drawHeight=330;picture.drawWidth=330/ratio
            group=[picture]
            if index<len(blocks) and blocks[index].strip().startswith('Figure '):group.append(Paragraph(inline(blocks[index].strip()),caption));index+=1
            story.extend([Spacer(1,8),KeepTogether(group),Spacer(1,8)]);continue
        if block.startswith('|'):
            rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in block.splitlines() if line.strip() and not re.fullmatch(r'[| :\-]+',line.strip())]
            count=len(rows[0]);widths=[60,88,58,45,42,175] if count==6 else [468/count]*count
            formatted=[[Paragraph(inline(c),cellhead if i==0 else cell) for c in row] for i,row in enumerate(rows)]
            table=Table(formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('LINEABOVE',(0,0),(-1,0),0.7,colors.black),('LINEBELOW',(0,0),(-1,0),0.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.7,colors.black),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f3f3')])]))
            story.append(table);continue
        if block.startswith('Table '):story.append(Paragraph('<b>'+inline(block)+'</b>',tablecap));continue
        if block.startswith('Note.'):story.append(Paragraph(inline(block),caption));continue
        if block.startswith('Keywords:'):story.append(Paragraph('<i>Keywords:</i>'+inline(block[len('Keywords:'):]),plain));story.append(PageBreak());abstract=False;continue
        if block in [profile['author_name'],f"Student ID: {profile['student_id']}",profile['institution'],profile['department'],'Architecture of Computers (CII3SE003CI), 2026/2027']:story.append(Paragraph(inline(block),identity));continue
        story.append(Paragraph(inline(block),reference if refs else plain if abstract else body))
    output=root/'Secure_DNS_Research_Paper.pdf'
    def page_number(canvas,doc):
        canvas.saveState();canvas.setFont(font,12);canvas.drawRightString(540,756,str(doc.page));canvas.restoreState()
    document=SimpleDocTemplate(str(output),pagesize=letter,leftMargin=72,rightMargin=72,topMargin=72,bottomMargin=72,title='Performance Overhead of Secure DNS',author=profile['author_name'],subject='Same-provider HTTP2 DoH and UDP DNS, connection state and separate-date replication')
    document.build(story,onFirstPage=page_number,onLaterPages=page_number)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();root=args.root.resolve()
    original=load(root/'results/summary.json');repeat=load(root/'results/replication-2026-11-19/summary.json');check_summary(original,'Original');check_summary(repeat,'Replication')
    profile=load(root/'profile.json');references=load(root/'docs/references.json')['references'];robustness=load(root/'results/robustness.json')
    text=(root/'docs/paper_source.md').read_text(encoding='utf-8');tokens=make_tokens(root,original,repeat,robustness,references,profile)
    for key,value in tokens.items():text=text.replace('{{'+key+'}}',value)
    text=text.replace('](../figures/','](figures/')
    unknown=re.findall(r'\{\{(.*?)\}\}',text)
    if unknown:raise ValueError('Unfilled source fields '+str(unknown))
    abstract=text.split('### Abstract\n\n')[1].split('\n\nKeywords:')[0]
    counted=text.split('## References')[0];counted=re.sub(r'!\[[^\]]*\]\([^)]*\)','',counted);counted=re.sub(r'[|#*]',' ',counted);counted=re.sub(r'\n\s*[-: ]+\n','\n',counted)
    counts={'main_words_including_abstract_tables_captions_declarations':len(counted.split()),'abstract_words':len(abstract.split()),'reference_count':len(references),'lookup_attempts_total':3600,'page_attempts_total':720,'dates':['2026-11-15','2026-11-19']}
    if not 250<=counts['abstract_words']<=300:raise ValueError('Abstract should contain 250–300 words: '+str(counts))
    if counts['main_words_including_abstract_tables_captions_declarations']>3000:raise ValueError('Conservative main-text count exceeds 3000: '+str(counts))
    output=render_pdf(text,root,profile);(root/'manuscript.md').write_text(text,encoding='utf-8');extended_results(root,original,repeat)
    counts['pdf']=output.name;(root/'results/paper_build.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8');print(json.dumps(counts,indent=2))


if __name__=='__main__':main()
