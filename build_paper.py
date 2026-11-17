"""Build the paper from the authoritative recorded-data analysis and profile.

Run from the reproducibility package directory. Does not collect network data.
"""
import argparse
import datetime as dt
import html
import json
import math
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.graphics.shapes import Drawing, String, Line
from reportlab.graphics.charts.lineplots import LinePlot


def f(x): return f'{x:.1f}'
def signed(x): return f'{x:+.1f}'
def provider_name(p): return {'cloudflare':'Cloudflare','google':'Google'}[p]
def mode_name(m): return {'udp':'UDP','doh_fresh':'DoH fresh','doh_warm':'DoH established','doh_reused':'DoH established'}[m]
def ci(r): return f"{signed(r['median_delta_ms'])} [{signed(r['ci95_low_ms'])}, {signed(r['ci95_high_ms'])}]"


def find(rows,p,m,origins=None):
    return next(r for r in rows if r['provider']==p and r.get('mode',r.get('comparison'))==m and (origins is None or r['origins']==origins))


def register_fonts(font_dir=None):
    folder=Path(font_dir or 'C:/Windows/Fonts')
    if (folder/'times.ttf').exists():
        for name,file in [('Paper','times.ttf'),('PaperBold','timesbd.ttf'),('PaperItalic','timesi.ttf'),('PaperBoldItalic','timesbi.ttf')]:
            pdfmetrics.registerFont(TTFont(name,str(folder/file)))
        pdfmetrics.registerFontFamily('Paper',normal='Paper',bold='PaperBold',italic='PaperItalic',boldItalic='PaperBoldItalic')
        return 'Paper','PaperBold','PaperItalic'
    return 'Times-Roman','Times-Bold','Times-Italic'


def inline(text):
    value=html.escape(text)
    value=re.sub(r'\*([^*]+)\*',r'<i>\1</i>',value)
    value=re.sub(r'(https://[^\s<]+)',lambda m:f'<link href="{m[1]}" color="#19334d">{m[1]}</link>',value)
    return value


def table_flow(rows,kind,styles):
    if kind=='lookup':
        header=['Provider','Transport','Success /\nattempts','Median\n(ms)','p95\n(ms)','Paired difference (ms)\n[descriptive 95% interval]']
        widths=[61,88,58,47,42,172]
        data=[]
        for p in ['cloudflare','google']:
            for m in ['udp','doh_fresh','doh_warm']:
                r=find(rows['lookup_summary'],p,m)
                effect='Baseline' if m=='udp' else ci(find(rows['lookup_paired'],p,m))
                data.append([provider_name(p),mode_name(m),f"{r['succeeded']}/{r['attempted']}",f(r['median_ms']),f(r['p95_ms']),effect])
        caption='Table 1\nLookup latency by provider and connection state'
    else:
        header=['Provider /\nhostnames','Transport','Success /\nattempts','Median\n(ms)','p95\n(ms)','Paired difference (ms)\n[descriptive 95% interval]']
        widths=[72,83,56,45,42,170]
        data=[]
        for p in ['cloudflare','google']:
            for layout in [1,8]:
                for m in ['udp','doh_fresh','doh_reused']:
                    r=find(rows['page_summary'],p,m,layout)
                    effect='Baseline' if m=='udp' else ci(find(rows['page_paired'],p,m,layout))
                    data.append([f'{provider_name(p)} / {layout}',mode_name(m),f"{r['succeeded']}/{r['attempted']}",f(r['median_ms']),f(r['p95_ms']),effect])
        caption='Table 2\nLoad event time in the controlled DNS-gated browser fixture'
    head=[Paragraph(inline(c).replace('\n','<br/>'),styles['thead']) for c in header]
    formatted=[[Paragraph(inline(c),styles['cell']) for c in row] for row in data]
    table=Table([head]+formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
    padding=5 if kind=='page' else 7
    table.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('LINEABOVE',(0,0),(-1,0),0.7,colors.black),('LINEBELOW',(0,0),(-1,0),0.6,colors.black),
        ('LINEBELOW',(0,-1),(-1,-1),0.7,colors.black),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f4f4')]),
    ]))
    label,title=caption.split('\n')
    return [Paragraph(f'<b>{label}</b>',styles['caption']),Paragraph(f'<i>{title}</i>',styles['caption']),table,
            Paragraph('Note. Positive paired differences indicate slower DoH. Differences are medians of matched DoH minus UDP observations, not differences of column medians. Intervals condition on the observed windows and successful pairs. p95 is a nearest-rank sample percentile.',styles['note']),Spacer(1,12)]


def ecdf(raw,styles):
    drawing=Drawing(468,230)
    palette=[colors.black,colors.HexColor('#8c382e'),colors.HexColor('#235d87')]
    for panel,p in enumerate(['cloudflare','google']):
        chart=LinePlot();chart.x=34+panel*237;chart.y=45;chart.width=191;chart.height=150
        chart.data=[]
        maxx=0
        for m in ['udp','doh_fresh','doh_warm']:
            vals=sorted(r['elapsed_ms'] for r in raw if r.get('phase')=='measure' and r['provider']==p and r['protocol']==m and r.get('valid'))
            maxx=max(maxx,max(vals))
            points=[(0,0)]
            for i,x in enumerate(vals):points.extend([(x,i/len(vals)),(x,(i+1)/len(vals))])
            chart.data.append(points)
        chart.joinedLines=1;chart.lines.strokeWidth=1
        for i,color in enumerate(palette):chart.lines[i].strokeColor=color
        chart.lines[1].strokeDashArray=[4,2]
        chart.lines[2].strokeDashArray=[1,2]
        chart.xValueAxis.valueMin=0;chart.xValueAxis.valueMax=math.ceil(maxx/50)*50
        chart.xValueAxis.valueStep=max(25,math.ceil(maxx/4/25)*25)
        chart.yValueAxis.valueMin=0;chart.yValueAxis.valueMax=1;chart.yValueAxis.valueStep=0.25
        chart.xValueAxis.labels.fontName=styles['base_font'];chart.xValueAxis.labels.fontSize=8
        chart.yValueAxis.labels.fontName=styles['base_font'];chart.yValueAxis.labels.fontSize=8
        chart.xValueAxis.strokeColor=colors.grey;chart.yValueAxis.strokeColor=colors.grey
        drawing.add(chart)
        drawing.add(String(130+panel*237,207,provider_name(p),textAnchor='middle',fontName=styles['bold_font'],fontSize=11))
        drawing.add(String(130+panel*237,20,'Lookup latency (ms)',textAnchor='middle',fontName=styles['base_font'],fontSize=9))
    drawing.add(String(3,196,'CDF',fontName=styles['base_font'],fontSize=8))
    for i,label in enumerate(['UDP','DoH fresh','DoH established']):
        x=47+i*140;drawing.add(Line(x,5,x+18,5,strokeColor=palette[i],strokeWidth=1.2))
        drawing.add(String(x+23,2,label,fontName=styles['base_font'],fontSize=9))
    return drawing


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--font-dir')
    args=parser.parse_args();root=args.root.resolve()
    summary=json.loads((root/'results/summary.json').read_text(encoding='utf-8'))
    if summary['counts']['lookup_measurements']!=1800 or summary['counts']['pages']!=360:raise ValueError('Full 1800 lookup / 360 navigation dataset required')
    for a in summary['validation'].values():
        if isinstance(a,dict) and (a.get('validation_errors') or a.get('transport_mismatches')):raise ValueError('Recorded-data audit failed')
    if summary['warnings']:raise ValueError('Resolve analysis warnings before building paper')
    if any(r['failed'] for r in summary['lookup_summary']+summary['page_summary']):raise ValueError('This manuscript template assumes the published complete-success dataset; revise text before building from data with failures.')
    profile=json.loads((root/'profile.json').read_text(encoding='utf-8'))
    env=json.loads((root/'data/environment.json').read_text(encoding='utf-8'))
    pageenv=json.loads((root/'data/page-environment.jsonl').read_text(encoding='utf-8').splitlines()[0])
    complete=all(profile.get(k,'').strip() for k in ['author_name','student_id','repository_url'])
    name=profile.get('author_name') or 'Author name ______________________________'
    student_id=profile.get('student_id') or '______________________________'
    identity=f"{name}\n\nStudent ID: {student_id}\n\n{profile.get('institution','Vistula University')}\n\n{profile.get('department','Computer Engineering')}\n\nArchitecture of Computers (CII3SE003CI), 2026/2027"
    L=lambda p,m:find(summary['lookup_summary'],p,m)
    D=lambda p,m:find(summary['lookup_paired'],p,m)
    P=lambda p,m,o:find(summary['page_summary'],p,m,o)
    Q=lambda p,m,o:find(summary['page_paired'],p,m,o)
    lookup_fail=sum(r['failed'] for r in summary['lookup_summary']);page_fail=sum(r['failed'] for r in summary['page_summary'])
    times=summary['window_times'];start=min(x['first_start_utc'] for x in times);end=max(x['last_start_utc'] for x in times)
    local=lambda x:(dt.datetime.fromisoformat(x.replace('Z','+00:00'))+dt.timedelta(hours=1)).strftime('%H:%M:%S')
    tokens={
        'IDENTITY':identity,'DNS_N':'1,800','PAGE_N':'360',
        'PLATFORM':f"Windows {env['release']} ({env['arch']})",'NODE_VERSION':env['node'].removeprefix('v'),
        'CPU_MODEL':env['cpu_model'].strip(),'LOGICAL_CPUS':str(env['logical_cpus']),'MEMORY_GIB':f(env['total_memory_gib']),
        'CHROME_VERSION':pageenv['browser'],'PLAYWRIGHT_VERSION':pageenv['playwright'],
        'ABSTRACT_RESULTS':f"Fresh DoH increased paired lookup latency by {f(D('cloudflare','doh_fresh')['median_delta_ms'])} ms for Cloudflare and {f(D('google','doh_fresh')['median_delta_ms'])} ms for Google. With an established session, paired differences were {signed(D('cloudflare','doh_warm')['median_delta_ms'])} ms and {signed(D('google','doh_warm')['median_delta_ms'])} ms, respectively.",
        'COMPLETENESS':f"The dataset contains 1,800 lookup attempts, 120 lookup-priming records and 360 page attempts. There were {lookup_fail} failed lookup attempts and {page_fail} failed page attempts. Each lookup condition contains 300 successful observations and each page condition thirty. Collection ran from {local(start)} to approximately {local(end)} Europe/Warsaw time. All measured DoH responses negotiated HTTP/2 over TLS 1.3. Fresh direct-lookup sessions reported no TLS resumption, and established-session records passed the connection-state checks. An independent decoder rechecked the saved DNS messages. Preparatory smoke tests were excluded.",
        'LOOKUP_RESULTS':f"Table 1 reports the marginal distributions. For Cloudflare, median UDP latency was {f(L('cloudflare','udp')['median_ms'])} ms, compared with {f(L('cloudflare','doh_fresh')['median_ms'])} ms for fresh DoH and {f(L('cloudflare','doh_warm')['median_ms'])} ms for established DoH. For Google, the corresponding medians were {f(L('google','udp')['median_ms'])}, {f(L('google','doh_fresh')['median_ms'])} and {f(L('google','doh_warm')['median_ms'])} ms. Figure 1 shows the complete successful-lookup distributions.",
        'LOOKUP_TABLE':'{{LOOKUP_TABLE}}','LOOKUP_FIGURE':'{{LOOKUP_FIGURE}}','PAGE_TABLE':'{{PAGE_TABLE}}',
        'LOOKUP_PAIRED':f"The median paired fresh-DoH difference was {ci(D('cloudflare','doh_fresh'))} ms for Cloudflare and {ci(D('google','doh_fresh'))} ms for Google. Established DoH differences were {ci(D('cloudflare','doh_warm'))} ms and {ci(D('google','doh_warm'))} ms. Brackets give the descriptive bootstrap interval. These paired estimates, rather than subtraction of marginal medians, are the primary comparisons.",
        'PAGE_RESULTS':f"Table 2 reports observed load-event times for the fixture. With one hostname, fresh DoH added a median paired {f(Q('cloudflare','doh_fresh',1)['median_delta_ms'])} ms for Cloudflare and {f(Q('google','doh_fresh',1)['median_delta_ms'])} ms for Google. With eight hostnames, the differences were {f(Q('cloudflare','doh_fresh',8)['median_delta_ms'])} and {f(Q('google','doh_fresh',8)['median_delta_ms'])} ms. These loads shared one fresh session per page.",
        'PAGE_PAIRED':f"Established-session page differences were {ci(Q('cloudflare','doh_reused',1))} ms for the Cloudflare one-hostname fixture and {ci(Q('cloudflare','doh_reused',8))} ms for eight hostnames. Google differences were {ci(Q('google','doh_reused',1))} ms and {ci(Q('google','doh_reused',8))} ms. All conditions completed seven image loads. Per-window effects, per-domain lookup contrasts and leave-one-window-out estimates are supplied in the analysis tables.",
        'DISCUSSION_RESULTS':f"Connection establishment accounted for a large part of the difference between the two DoH conditions. Cloudflare's established lookup median was close to its UDP baseline. For Google, the established-session paired differences across windows were "+', '.join(signed(r['median_delta_ms'])+' ms' for r in summary['window_effects'] if r['experiment']=='lookup' and r['provider']=='google' and r['comparison']=='doh_warm')+". The sign changed within this brief session, so a pooled estimate conceals an important sensitivity. The experiment provides no single provider-independent DoH penalty. Small negative estimates are compatible with differences in routing, caches and implementation costs. They do not establish that encryption makes DNS intrinsically faster.",
        'CONCLUSION_RESULTS':f"In this local experiment, fresh HTTP/2 DoH sessions were slower than UDP DNS for both providers. Reusing the session substantially reduced the observed difference, with provider-specific established-session results. The controlled browser measurements show the cost of waiting for DNS under a fixed resource graph, while leaving general website performance unresolved.",
        'EVIDENCE_LINK':f"Reviewer-accessible evidence repository: {profile['repository_url']}" if profile.get('repository_url') else 'Reviewer-accessible evidence repository: ________________________________________',
    }
    text=(root/'paper_source.md').read_text(encoding='utf-8')
    for key,value in tokens.items():text=text.replace('{{'+key+'}}',value)
    unknown=set(re.findall(r'\{\{(.*?)\}\}',text)) - {'LOOKUP_TABLE','LOOKUP_FIGURE','PAGE_TABLE'}
    if unknown:raise ValueError('Unfilled manuscript fields: '+str(unknown))
    # Markdown contains portable tables in addition to the PDF's formatted tables.
    md=text
    for marker,summary_key,paired_key in [('LOOKUP_TABLE','lookup_summary','lookup_paired'),('PAGE_TABLE','page_summary','page_paired')]:
        lines=['| Provider | Hostnames | Mode | Success / attempts | Median ms | p95 ms | Paired delta ms [95% interval] |','|---|---:|---|---:|---:|---:|---|']
        for r in summary[summary_key]:
            effect='Baseline' if r['mode']=='udp' else ci(find(summary[paired_key],r['provider'],r['mode'],r['origins'] if r['origins']!='' else None))
            lines.append(f"| {provider_name(r['provider'])} | {r['origins']} | {mode_name(r['mode'])} | {r['succeeded']}/{r['attempted']} | {f(r['median_ms'])} | {f(r['p95_ms'])} | {effect} |")
        md=md.replace('{{'+marker+'}}','\n'.join(lines))
    md=md.replace('{{LOOKUP_FIGURE}}','Figure 1 is embedded in the PDF and is calculated directly from the recorded successful lookup latencies.')
    (root/'manuscript.md').write_text(md,encoding='utf-8')
    font,bold,italic=register_fonts(args.font_dir)
    styles={'base_font':font,'bold_font':bold}
    styles['body']=ParagraphStyle('Body',fontName=font,fontSize=12,leading=24,firstLineIndent=36,spaceAfter=0,allowWidows=0,allowOrphans=0)
    styles['abstract']=ParagraphStyle('Abstract',parent=styles['body'],firstLineIndent=0)
    styles['title']=ParagraphStyle('Title',fontName=bold,fontSize=14,leading=19,alignment=TA_CENTER,spaceAfter=8,keepWithNext=True)
    styles['subtitle']=ParagraphStyle('Subtitle',fontName=bold,fontSize=12,leading=17,alignment=TA_CENTER,spaceAfter=12,keepWithNext=True)
    styles['identity']=ParagraphStyle('Identity',fontName=font,fontSize=12,leading=20,alignment=TA_CENTER,spaceAfter=4)
    styles['h1']=ParagraphStyle('Heading1',fontName=bold,fontSize=12,leading=24,alignment=TA_CENTER,spaceBefore=10,spaceAfter=0,keepWithNext=True)
    styles['h2']=ParagraphStyle('Heading2',parent=styles['h1'],alignment=TA_LEFT)
    styles['caption']=ParagraphStyle('Caption',fontName=font,fontSize=11,leading=15,spaceAfter=4,keepWithNext=True)
    styles['note']=ParagraphStyle('Note',fontName=font,fontSize=10,leading=14,spaceBefore=6,spaceAfter=0)
    styles['cell']=ParagraphStyle('Cell',fontName=font,fontSize=9.2,leading=13)
    styles['thead']=ParagraphStyle('TableHead',parent=styles['cell'],fontName=bold)
    styles['ref']=ParagraphStyle('Reference',parent=styles['body'],firstLineIndent=-36,leftIndent=36,spaceAfter=5)
    story=[];in_abstract=False;in_refs=False;identity_lines=set(identity.split('\n\n'))
    paragraphs=text.split('\n\n')
    for block in paragraphs:
        block=block.strip()
        if not block:continue
        if block=='{{LOOKUP_TABLE}}':story.extend(table_flow(summary,'lookup',styles));continue
        if block=='{{PAGE_TABLE}}':story.extend(table_flow(summary,'page',styles));continue
        if block=='{{LOOKUP_FIGURE}}':
            raw=[json.loads(line) for line in (root/'data/dns_raw.jsonl').read_text().splitlines() if line.strip()]
            story.append(KeepTogether([Paragraph('<b>Figure 1</b>',styles['caption']),Paragraph('<i>Empirical cumulative distribution of successful lookup latency</i>',styles['caption']),ecdf(raw,styles),Paragraph('Note. Each line contains 300 successful queries. The two panels have different horizontal scales. Setup is included in fresh DoH. All points, including long successful observations, are shown.',styles['note'])]));continue
        if block.startswith('# '):story.append(Paragraph(inline(block[2:]),styles['title']));continue
        if block.startswith('## Evaluating'):story.append(Paragraph(inline(block[3:]),styles['subtitle']));continue
        if block.startswith('## '):
            title=block[3:];in_abstract=False
            if title=='References':in_refs=True;story.append(PageBreak())
            story.append(Paragraph(inline(title),styles['h1']));continue
        if block.startswith('### '):
            title=block[4:];in_abstract=title=='Abstract'
            if in_abstract:story.append(PageBreak())
            story.append(Paragraph(inline(title),styles['h2'] if title!='Abstract' else styles['h1']));continue
        if block in identity_lines:story.append(Paragraph(inline(block),styles['identity']));continue
        if block.startswith('Keywords:'):story.append(Paragraph('<i>Keywords:</i>'+inline(block[len('Keywords:'):]),styles['abstract']));in_abstract=False;story.append(PageBreak());continue
        story.append(Paragraph(inline(block),styles['ref'] if in_refs else styles['abstract'] if in_abstract else styles['body']))
    filename='Secure_DNS_Research_Paper.pdf' if complete else 'Secure_DNS_Research_Paper_REVIEW.pdf'
    pdf=root/filename
    def chrome(canvas,doc):
        canvas.saveState();canvas.setFont(font,12);canvas.drawRightString(540,756,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(pdf),pagesize=letter,rightMargin=72,leftMargin=72,topMargin=72,bottomMargin=72,title='Performance Overhead of Secure DNS',author=profile.get('author_name') or 'Student author to be completed',subject='Same-provider UDP DNS and HTTP/2 DoH latency with a controlled browser fixture')
    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    count_text=re.sub(r'[|#*]',' ',md.split('## References')[0])
    count_text=re.sub(r'\n\s*[-: ]+\n','\n',count_text)
    abstract=text.split('### Abstract\n\n')[1].split('\n\nKeywords:')[0]
    counts={'main_text_words_including_abstract_declarations_and_availability':len(count_text.split()),'abstract_words':len(abstract.split()),'pdf':filename,'identity_and_repository_complete':complete,'font':font}
    if counts['main_text_words_including_abstract_declarations_and_availability']>3000:raise ValueError('Paper exceeds 3000-word conservative count')
    if not 250<=counts['abstract_words']<=300:raise ValueError('Abstract outside requested 250-300 word range')
    (root/'results/paper_build.json').write_text(json.dumps(counts,indent=2)+'\n')
    print(json.dumps(counts,indent=2))


if __name__=='__main__':main()
