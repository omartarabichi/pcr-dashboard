#!/usr/bin/env python3
"""
PCR Dashboard Generator
Fetches all open PCRs from Jira assigned to Omar Tarabichi,
classifies them into themes/sub-themes, and outputs index.html.

Required env vars:
  JIRA_EMAIL     - e.g. omar.tarabichi@instacart.com
  JIRA_API_TOKEN - Jira API token
"""

import os, sys, json, base64, urllib.request, urllib.error, urllib.parse, re
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────
JIRA_HOST  = 'https://instacart.atlassian.net'
ASSIGNEE   = '712020:18d68096-380f-416f-b945-f0258928e9d5'
EMAIL      = os.environ.get('JIRA_EMAIL', '')
TOKEN      = os.environ.get('JIRA_API_TOKEN', '')
OUT_FILE   = os.environ.get('OUTPUT_FILE', 'index.html')

# ── THEMES ────────────────────────────────────────────────────────────────────
THEMES = [
    {'id': 1, 'name': 'Flyers',                          'color': '#4F46E5',
     'subthemes': ['PDF Viewer', 'Clickable Flyer Tooling', 'Scheduling & Lifecycle',
                   'IPP Self-Serve', 'New Retailer Integrations']},
    {'id': 2, 'name': 'CMS / Page Builder / Asset Mgmt', 'color': '#0284C7',
     'subthemes': ['Page Builder Core', 'Content Page Enhancements', 'Homepage Builder',
                   'Banners / Slots / Display', 'Branding & Theming', 'Asset Mgmt & Creative Tools']},
    {'id': 3, 'name': 'Merchandising & Catalog',          'color': '#059669',
     'subthemes': ['Collection Building & Mgmt', 'Department & Catalog Mgmt',
                   'Offers / Coupons / Promotions', 'Placements & Targeting']},
    {'id': 4, 'name': 'New Retailer Expansion',           'color': '#D97706',
     'subthemes': ['ALDI US', 'ALDI International & UK', 'Metro Canada', 'PFG', 'Other New Partners']},
    {'id': 5, 'name': 'Analytics & Tracking',             'color': '#7C3AED',
     'subthemes': ['GTM & Event Tracking', 'Analytics Integrations',
                   'Reporting & Measurement', 'Privacy & Compliance']},
]


# ── CLASSIFICATION ────────────────────────────────────────────────────────────
def classify(summary):
    s = summary.lower()

    # Theme 4: New Retailer Expansion (check first – most specific retailer signals)
    if re.search(r'aldi uk|aldi\s+intl.*non.uk|bottle deposit.*non.uk', s):
        return 4, 'ALDI International & UK'
    if re.search(r'\baldi\b', s):
        return 4, 'ALDI US'
    if re.search(r'\bmetro\b', s):
        return 4, 'Metro Canada'
    if re.search(r'\bpfg\b|pattison food group', s):
        return 4, 'PFG'
    if re.search(r'\bwakefern\b|\bcostco\b|\bpublix\b|\bsprouts\b|\bsave mart\b|\bfareway\b'
                 r'|\bcoborn\b|\bwoodman\b|\balgolia\b|\blunds\b|\bbylerlys\b|\ballegiance\b'
                 r'|\btops\b|\bpcny\b|\bngi\b|\bgelsons?\b|\bheritage grocer\b|\bred pepper\b'
                 r'|\bmetcash\b|\bcalgary coop\b|\bcub\b|\bharmons\b|\bsave mart\b', s):
        return 4, 'Other New Partners'

    # Theme 1: Flyers
    if re.search(r'\bflyer\b|\bflyers\b|\bipp\b|clickable|weekly ad|sftp flyer'
                 r'|shoppable flyer|digital.first flyer|flyer pdf|flyer page|flyer task'
                 r'|flyer template|flyer url|flyer url', s):
        if re.search(r'pdf.*viewer|viewer.*pdf', s):
            return 1, 'PDF Viewer'
        if re.search(r'clickable flyer|flyer.*clickable|clickable.*pdf|seasonal.*clickable'
                     r'|make.*clickable|self.serve.*clickable', s):
            return 1, 'Clickable Flyer Tooling'
        if re.search(r'schedule.*flyer|flyer.*schedule|seasonal flyer|flyer.*lifecycle'
                     r'|ended.*flyer|active.*flyer|duration.*flyer', s):
            return 1, 'Scheduling & Lifecycle'
        if re.search(r'\bipp\b', s):
            return 1, 'IPP Self-Serve'
        return 1, 'New Retailer Integrations'

    # Theme 5: Analytics & Tracking
    if re.search(r'\bgtm\b|google tag manager|tag manager|\bpixel track\b|event track'
                 r'|\butm param\b|ga track|adobe analytics|tracking.*event|meaningful.*identifier'
                 r'|autocomplete.*track|tracking.*parameter|disable.*tracking', s):
        return 5, 'GTM & Event Tracking'
    if re.search(r'\banalytics\b|\btracking\b|\bmeasurement\b', s):
        return 5, 'GTM & Event Tracking'

    # Theme 2: CMS / Page Builder / Asset Mgmt
    if re.search(r'homepage.*builder|homepage content builder|homepage stub', s):
        return 2, 'Homepage Builder'
    if re.search(r'content page', s):
        return 2, 'Content Page Enhancements'
    if re.search(r'page builder|pagebuilder', s):
        return 2, 'Page Builder Core'
    if re.search(r'\bbanner\b|\bslot\b|display banner|quick link|image tile|feature collection'
                 r'|split banner|slim banner|slot block|aicc carousel|\bmrlp\b', s):
        return 2, 'Banners / Slots / Display'
    if re.search(r'branding|brand.*email|order email.*brand|font.*brand|site font', s):
        return 2, 'Branding & Theming'
    if re.search(r'\bdam\b|digital asset|media library|asset management|bulk upload.*image'
                 r'|image.*folder|asset.*folder|creative.*folder|marketing.*folder', s):
        return 2, 'Asset Mgmt & Creative Tools'
    if re.search(r'\bcms\b|content management|page.*template|template.*page|discovery page'
                 r'|loyalty.*template|content builder', s):
        return 2, 'Page Builder Core'

    # Theme 3: Merchandising & Catalog (default)
    if re.search(r'coupon|offer|promo|discount|clipp', s):
        return 3, 'Offers / Coupons / Promotions'
    if re.search(r'targeting|fulfillment.*context|delivery.*context|pickup.*context'
                 r'|placement.*targeting|merchandis.*placement', s):
        return 3, 'Placements & Targeting'
    if re.search(r'department|catalog|aisle|barcode|store.*pick|store.*map|store.*location', s):
        return 3, 'Department & Catalog Mgmt'
    return 3, 'Collection Building & Mgmt'


# ── JIRA FETCH ────────────────────────────────────────────────────────────────
def fetch_pcrs():
    creds = base64.b64encode(f'{EMAIL}:{TOKEN}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {creds}',
        'Accept': 'application/json',
        'User-Agent': 'PCR-Dashboard-Generator/1.0',
    }

    pcrs = []
    last_key = None
    page = 0
    while True:
        jql = f'project = PCR AND assignee = "{ASSIGNEE}" AND statusCategory != Done'
        if last_key:
            jql += f' AND key < {last_key}'
        jql += ' ORDER BY key DESC'

        url = (f'{JIRA_HOST}/rest/api/3/search/jql'
               f'?jql={urllib.parse.quote(jql)}'
               f'&maxResults=100'
               f'&fields=summary,status,priority,created,updated')

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f'Jira HTTP error: {e.code} {e.read().decode()[:200]}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f'Jira request error: {e}', file=sys.stderr)
            sys.exit(1)

        issues = data.get('issues', [])
        if not issues:
            break
        pcrs.extend(issues)
        last_key = issues[-1]['key']
        page += 1
        print(f'  Page {page}: fetched {len(issues)} issues (total {len(pcrs)})', file=sys.stderr)
        if len(issues) < 100:
            break

    return pcrs


# ── HELPERS ───────────────────────────────────────────────────────────────────
STATUS_CLASS = {
    'To Do': 'badge-todo', 'New': 'badge-todo', 'Open': 'badge-todo', 'Backlog': 'badge-todo',
    'In Progress': 'badge-inprogress', 'On Track': 'badge-inprogress', 'Accepted': 'badge-inprogress',
    'At Risk': 'badge-blocked', 'In Review': 'badge-review',
    'Done': 'badge-default', 'Closed': 'badge-default', 'Blocked': 'badge-blocked',
}

def badge(status_name):
    cls = STATUS_CLASS.get(status_name, 'badge-default')
    return f'<span class="badge {cls}">{html_esc(status_name)}</span>'

def html_esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = ("*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
       ":root{--green:#43B02A;--bg:#F2F4F7;--card:#fff;--text:#111827;--text2:#6B7280;--border:#E5E7EB}"
       "body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}"
       "header{background:#0F172A;color:white;padding:0 28px;height:58px;display:flex;align-items:center;"
       "justify-content:space-between;position:sticky;top:0;z-index:200;box-shadow:0 1px 4px rgba(0,0,0,.4)}"
       ".hdr-left{display:flex;align-items:center;gap:14px}"
       ".logo{width:34px;height:34px;background:var(--green);border-radius:9px;display:flex;"
       "align-items:center;justify-content:center;font-size:18px}"
       ".hdr-title{font-size:15px;font-weight:700}.hdr-sub{font-size:11px;color:#94A3B8;margin-top:1px}"
       ".hdr-right{font-size:12px;color:#64748B}"
       "main{max-width:1300px;margin:0 auto;padding:24px 24px 48px}"
       ".stat-grid{display:grid;grid-template-columns:repeat(5,1fr) 1.1fr;gap:12px;margin-bottom:20px}"
       ".stat-card{background:var(--card);border-radius:12px;padding:18px 16px 14px;"
       "border:1px solid var(--border);position:relative;overflow:hidden}"
       ".stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--tc)}"
       ".stat-label{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text2);"
       "font-weight:600;margin-bottom:8px}"
       ".stat-value{font-size:30px;font-weight:800;color:var(--tc);line-height:1}"
       ".stat-name{font-size:12px;color:var(--text2);margin-top:5px;line-height:1.3}"
       ".stat-pct{font-size:11px;color:var(--text2);margin-top:3px}"
       ".total-card{background:#0F172A;border:none}.total-card::before{display:none}"
       ".total-card .stat-label{color:#64748B}.total-card .stat-value{color:white;font-size:36px}"
       ".total-card .stat-name{color:#94A3B8}"
       ".charts-row{display:grid;grid-template-columns:280px 1fr;gap:14px;margin-bottom:20px}"
       ".card{background:var(--card);border-radius:12px;border:1px solid var(--border);padding:20px}"
       ".card-title{font-size:13px;font-weight:600;color:var(--text2);text-transform:uppercase;"
       "letter-spacing:.05em;margin-bottom:16px}"
       ".donut-wrap{position:relative;width:200px;height:200px;margin:0 auto 16px}"
       ".donut-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);"
       "text-align:center;pointer-events:none}"
       ".donut-total{font-size:30px;font-weight:800;line-height:1}"
       ".donut-label{font-size:11px;color:var(--text2);margin-top:2px}"
       ".legend-row{display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:6px}"
       ".legend-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}"
       ".legend-name{flex:1;color:var(--text2)}.legend-val{font-weight:700}"
       ".toolbar{display:flex;align-items:center;gap:12px;margin-bottom:14px}"
       ".search-wrap{position:relative;flex:1;max-width:380px}"
       ".search-icon{position:absolute;left:11px;top:50%;transform:translateY(-50%);"
       "color:#9CA3AF;pointer-events:none}"
       ".search-input{width:100%;padding:9px 12px 9px 34px;border:1px solid var(--border);"
       "border-radius:8px;font-size:13px;font-family:inherit;outline:none;background:white}"
       ".search-input:focus{border-color:var(--green);box-shadow:0 0 0 3px rgba(67,176,42,.12)}"
       ".count-label{font-size:13px;color:var(--text2);margin-left:auto}"
       ".btn{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:7px;"
       "font-size:13px;font-weight:500;cursor:pointer;border:1px solid var(--border);"
       "background:white;font-family:inherit;transition:all .15s}.btn:hover{background:#F8FAFC}"
       ".theme-section{background:var(--card);border-radius:12px;border:1px solid var(--border);"
       "margin-bottom:10px;overflow:hidden}"
       ".theme-header{display:flex;align-items:center;padding:15px 20px;cursor:pointer;"
       "user-select:none;transition:background .1s}.theme-header:hover{background:#F8FAFC}"
       ".theme-bar{width:4px;height:38px;border-radius:3px;margin-right:16px;flex-shrink:0}"
       ".theme-text{flex:1}.theme-name{font-size:15px;font-weight:700}"
       ".theme-tags{font-size:11px;color:var(--text2);margin-top:3px;white-space:nowrap;"
       "overflow:hidden;text-overflow:ellipsis;max-width:600px}"
       ".theme-count{font-size:18px;font-weight:800;padding:5px 13px;border-radius:20px;"
       "margin-right:14px;flex-shrink:0}"
       ".chevron{color:#9CA3AF;font-size:11px;transition:transform .2s;flex-shrink:0}"
       ".chevron.open{transform:rotate(180deg)}"
       ".theme-body{display:none;border-top:1px solid var(--border)}.theme-body.open{display:block}"
       ".theme-grid{display:grid;grid-template-columns:260px 1fr}"
       ".sub-panel{padding:18px 18px 18px 20px;border-right:1px solid var(--border)}"
       ".sub-title{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text2);"
       "font-weight:600;margin-bottom:12px}"
       ".st-row{display:flex;align-items:center;gap:8px;margin-bottom:10px}"
       ".st-name{font-size:12px;color:var(--text);width:130px;flex-shrink:0;line-height:1.3}"
       ".st-bar-bg{flex:1;height:7px;background:#F1F5F9;border-radius:4px;overflow:hidden}"
       ".st-bar-fill{height:100%;border-radius:4px}"
       ".st-count{font-size:12px;font-weight:700;width:22px;text-align:right;flex-shrink:0}"
       ".table-panel{overflow-x:auto}.table-scroll{max-height:420px;overflow-y:auto}"
       ".pcr-table{width:100%;border-collapse:collapse;min-width:500px}"
       ".pcr-table thead th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;"
       "color:var(--text2);font-weight:600;padding:10px 14px;text-align:left;"
       "border-bottom:1px solid var(--border);background:#FAFAFA;position:sticky;top:0;z-index:1}"
       ".pcr-table tbody td{padding:9px 14px;font-size:13px;border-bottom:1px solid #F3F6FA;"
       "vertical-align:middle}"
       ".pcr-table tbody tr:last-child td{border-bottom:none}"
       ".pcr-table tbody tr:hover td{background:#F8FAFC}"
       ".pcr-key{font-family:'SF Mono','Fira Code',monospace;font-size:11.5px;font-weight:700;"
       "text-decoration:none;white-space:nowrap}.pcr-key:hover{text-decoration:underline}"
       ".pcr-sum{max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
       ".badge{display:inline-flex;align-items:center;padding:3px 8px;border-radius:20px;"
       "font-size:11px;font-weight:600;white-space:nowrap}"
       ".badge-todo{background:#EFF6FF;color:#2563EB}"
       ".badge-inprogress{background:#FFFBEB;color:#D97706}"
       ".badge-review{background:#F5F3FF;color:#7C3AED}"
       ".badge-blocked{background:#FEF2F2;color:#DC2626}"
       ".badge-default{background:#F3F4F6;color:#6B7280}"
       ".st-badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10.5px;"
       "font-weight:500;background:#F1F5F9;color:#64748B;white-space:nowrap}"
       ".updated-note{font-size:12px;color:#9CA3AF;text-align:center;margin-top:32px;padding-bottom:8px}"
       ".refresh-btn{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;"
       "border-radius:7px;font-size:12px;font-weight:500;cursor:pointer;"
       "border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.08);"
       "color:#CBD5E1;font-family:inherit;transition:all .15s}"
       ".refresh-btn:hover{background:rgba(255,255,255,.16);color:#fff}"
       ".refresh-btn svg{transition:transform .5s}"
       ".refresh-btn:hover svg{transform:rotate(180deg)}"
       "@media(max-width:1100px){.stat-grid{grid-template-columns:repeat(3,1fr)}"
       ".charts-row{grid-template-columns:1fr}}"
       "@media(max-width:720px){.stat-grid{grid-template-columns:repeat(2,1fr)}"
       ".theme-grid{grid-template-columns:1fr}"
       ".sub-panel{border-right:none;border-bottom:1px solid var(--border)}"
       ".theme-tags{display:none}main{padding:16px}}")


# ── HTML GENERATION ───────────────────────────────────────────────────────────
def generate_html(pcrs, timestamp):
    # Classify all PCRs
    classified = []
    for issue in pcrs:
        key = issue['key']
        summary = issue['fields'].get('summary', '')
        status_name = (issue['fields'].get('status') or {}).get('name', 'Unknown')
        theme_id, subtheme = classify(summary)
        classified.append({'key': key, 'summary': summary, 'status': status_name,
                            'theme_id': theme_id, 'subtheme': subtheme})

    total = len(classified)

    # Build per-theme data
    theme_data = {}
    for t in THEMES:
        tid = t['id']
        theme_pcrs = [p for p in classified if p['theme_id'] == tid]
        st_counts = {st: 0 for st in t['subthemes']}
        for p in theme_pcrs:
            if p['subtheme'] in st_counts:
                st_counts[p['subtheme']] += 1
            else:
                st_counts[t['subthemes'][-1]] += 1
        theme_data[tid] = {'pcrs': theme_pcrs, 'st_counts': st_counts, 'count': len(theme_pcrs)}

    # Stat cards
    stat_cards = ''
    for t in THEMES:
        tid = t['id']
        cnt = theme_data[tid]['count']
        pct = round(cnt * 100 / total) if total else 0
        c = t['color']
        stat_cards += (f'<div class="stat-card" style="--tc:{c}">'
                       f'<div class="stat-label">Theme {tid}</div>'
                       f'<div class="stat-value">{cnt}</div>'
                       f'<div class="stat-name">{html_esc(t["name"])}</div>'
                       f'<div class="stat-pct">{pct}% of total</div></div>')
    stat_cards += (f'<div class="stat-card total-card">'
                   f'<div class="stat-label">Total Open</div>'
                   f'<div class="stat-value">{total}</div>'
                   f'<div class="stat-name">PCRs assigned to you</div></div>')

    # Donut legend
    legend = ''
    for t in THEMES:
        legend += (f'<div class="legend-row">'
                   f'<div class="legend-dot" style="background:{t["color"]}"></div>'
                   f'<span class="legend-name">{html_esc(t["name"])}</span>'
                   f'<span class="legend-val">{theme_data[t["id"]]["count"]}</span></div>')

    # Theme sections
    theme_sections = ''
    for t in THEMES:
        tid = t['id']
        td = theme_data[tid]
        cnt = td['count']
        c = t['color']
        st_counts = td['st_counts']
        tags = ' · '.join(f'{html_esc(st)} ({st_counts.get(st, 0)})' for st in t['subthemes'])

        max_st = max(st_counts.values()) if any(st_counts.values()) else 1
        sub_bars = '<div class="sub-title">Sub-themes</div>'
        for st in t['subthemes']:
            n = st_counts.get(st, 0)
            pct = round(n * 100 / max_st) if max_st else 0
            sub_bars += (f'<div class="st-row">'
                         f'<span class="st-name">{html_esc(st)}</span>'
                         f'<div class="st-bar-bg"><div class="st-bar-fill" '
                         f'style="width:{pct}%;background:{c}"></div></div>'
                         f'<span class="st-count" style="color:{c}">{n}</span></div>')

        rows = ''
        for p in sorted(td['pcrs'], key=lambda x: int(x['key'].split('-')[1]), reverse=True):
            rows += (f'<tr>'
                     f'<td><a class="pcr-key" href="https://instacart.atlassian.net/browse/{p["key"]}"'
                     f' target="_blank" style="color:{c}">{p["key"]}</a></td>'
                     f'<td class="pcr-sum" title="{html_esc(p["summary"])}">{html_esc(p["summary"])}</td>'
                     f'<td>{badge(p["status"])}</td>'
                     f'<td><span class="st-badge">{html_esc(p["subtheme"])}</span></td>'
                     f'</tr>')

        theme_sections += (
            f'<div class="theme-section">'
            f'<div class="theme-header" onclick="toggle(this)">'
            f'<div class="theme-bar" style="background:{c}"></div>'
            f'<div class="theme-text"><div class="theme-name">{html_esc(t["name"])}</div>'
            f'<div class="theme-tags">{tags}</div></div>'
            f'<div class="theme-count" style="background:{c}1A;color:{c}">{cnt}</div>'
            f'<div class="chevron">&#9660;</div>'
            f'</div>'
            f'<div class="theme-body">'
            f'<div class="theme-grid">'
            f'<div class="sub-panel">{sub_bars}</div>'
            f'<div class="table-panel"><div class="table-scroll">'
            f'<table class="pcr-table"><thead><tr>'
            f'<th>Key</th><th>Summary</th><th>Status</th><th>Sub-theme</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
            f'</div></div></div></div></div>'
        )

    # Chart data
    theme_names  = [t['name'] for t in THEMES]
    theme_counts = [theme_data[t['id']]['count'] for t in THEMES]
    theme_colors = [t['color'] for t in THEMES]
    all_st_labels, all_st_data, all_st_colors = [], [], []
    for t in THEMES:
        for st in t['subthemes']:
            all_st_labels.append(st)
            all_st_data.append(theme_data[t['id']]['st_counts'].get(st, 0))
            all_st_colors.append(t['color'])

    # Build Chart.js calls using string concat to avoid f-string/JS-template-literal conflicts
    donut_js = (
        "new Chart(document.getElementById('donut'),{type:'doughnut',data:{"
        + "labels:" + json.dumps(theme_names)
        + ",datasets:[{data:" + json.dumps(theme_counts)
        + ",backgroundColor:" + json.dumps(theme_colors)
        + ",borderWidth:3,borderColor:'#fff'}]},"
        + "options:{cutout:'66%',responsive:true,plugins:{legend:{display:false},"
        + "tooltip:{callbacks:{label:function(ctx){return ' '+ctx.label+': '+ctx.raw+' PCRs';}}}}}}})"
        + ";"
    )

    bar_js = (
        "new Chart(document.getElementById('barChart'),{type:'bar',data:{"
        + "labels:" + json.dumps(all_st_labels)
        + ",datasets:[{data:" + json.dumps(all_st_data)
        + ",backgroundColor:" + json.dumps(all_st_colors)
        + ",borderWidth:0,borderRadius:4}]},"
        + "options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false},"
        + "tooltip:{callbacks:{label:function(ctx){return ' '+ctx.raw+' PCRs';}}}},"
        + "scales:{x:{grid:{display:false}},y:{grid:{display:false},"
        + "ticks:{font:{size:11}}}}}})"
        + ";"
    )

    jira_url = (f'https://instacart.atlassian.net/jira/software/c/projects/PCR/list'
                f'?filter=assignee%20%3D%20{ASSIGNEE}&hideDone=true')

    search_js = (
        "function toggle(hdr){var body=hdr.nextElementSibling;"
        "var ch=hdr.querySelector('.chevron');body.classList.toggle('open');"
        "ch.classList.toggle('open');}\n"
        "function expandAll(open){document.querySelectorAll('.theme-body')"
        ".forEach(function(b){b.classList.toggle('open',open);});"
        "document.querySelectorAll('.chevron')"
        ".forEach(function(c){c.classList.toggle('open',open);});}\n"
        "function doSearch(q){var lq=q.toLowerCase().trim();var vis=0;"
        "document.querySelectorAll('.pcr-table tbody tr').forEach(function(row){"
        "var show=!lq||row.textContent.toLowerCase().indexOf(lq)>=0;"
        "row.style.display=show?'':'none';if(show)vis++;});"
        "document.getElementById('count-lbl').textContent="
        f"lq?vis+' matching PCRs':'{total} open PCRs';}}"
    )

    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        "<title>PCR Theme Dashboard \u2014 Omar Tarabichi</title>\n"
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>\n'
        "<style>" + CSS + "</style>\n"
        "</head><body>\n"
        '<header><div class="hdr-left"><div class="logo">\U0001f955</div>'
        '<div><div class="hdr-title">PCR Theme Dashboard</div>'
        '<div class="hdr-sub">Omar Tarabichi \u00b7 Instacart \u00b7 Open PCRs</div></div></div>'
        '<div style="display:flex;align-items:center;gap:14px">'
        f'<div class="hdr-right">Data as of {timestamp}</div>'
        '<button class="refresh-btn" onclick="location.reload()" title="Reload page to get latest data">'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>'
        '<path d="M21 3v5h-5"/></svg>Refresh</button>'
        '</div></header>\n'
        "<main>\n"
        f'<div class="stat-grid">{stat_cards}</div>\n'
        '<div class="charts-row">\n'
        '  <div class="card"><div class="card-title">By Theme</div>\n'
        '    <div class="donut-wrap"><canvas id="donut"></canvas>\n'
        f'      <div class="donut-center"><div class="donut-total">{total}</div>'
        '<div class="donut-label">PCRs</div></div>\n'
        f'    </div><div>{legend}</div>\n'
        '  </div>\n'
        '  <div class="card"><div class="card-title">Sub-theme Breakdown</div>'
        '<canvas id="barChart"></canvas></div>\n'
        '</div>\n'
        '<div class="toolbar">\n'
        '  <div class="search-wrap">\n'
        '    <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/>'
        '<path d="m21 21-4.35-4.35"/></svg>\n'
        '    <input class="search-input" id="q" placeholder="Search by key or title\u2026" '
        'oninput="doSearch(this.value)">\n'
        '  </div>\n'
        '  <button class="btn" onclick="expandAll(true)">Expand All</button>\n'
        '  <button class="btn" onclick="expandAll(false)">Collapse All</button>\n'
        f'  <span class="count-label" id="count-lbl">{total} open PCRs</span>\n'
        '</div>\n'
        + theme_sections
        + f'\n<div class="updated-note">Last updated: {timestamp} \u00b7 '
        f'<a href="{jira_url}" target="_blank" style="color:#43B02A">View in Jira \u2197</a></div>\n'
        "</main>\n"
        "<script>\n"
        + donut_js + "\n"
        + bar_js + "\n"
        + search_js + "\n"
        + "</script></body></html>"
    )
    return html


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not EMAIL or not TOKEN:
        print('Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set.',
              file=sys.stderr)
        sys.exit(1)

    print('Fetching PCRs from Jira...', file=sys.stderr)
    pcrs = fetch_pcrs()
    print(f'Fetched {len(pcrs)} PCRs total.', file=sys.stderr)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime('%B %-d, %Y at %-I:%M %p UTC')

    print('Generating HTML...', file=sys.stderr)
    html = generate_html(pcrs, timestamp)

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Written to {OUT_FILE} ({len(html):,} bytes)', file=sys.stderr)


if __name__ == '__main__':
    main()
