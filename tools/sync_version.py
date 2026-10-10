"""The sole editable version lives in version.json; validate and sync packaging."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'version.json').read_text())
version=data['version']
assert re.fullmatch(r'\d+\.\d+\.\d+',version)
assert data['store_version']==version+'.0'
assert data['release_tag']=='v'+version
installer=ROOT/'installer/CrowEyes.iss'
s=installer.read_text(encoding='utf-8')
s=re.sub(r'#define MyAppVersion "[^"]+"',f'#define MyAppVersion "{version}"',s)
s=re.sub(r'VersionInfoVersion=[^\n]+','VersionInfoVersion='+data['store_version'],s)
s=re.sub(r'OutputBaseFilename=[^\n]+','OutputBaseFilename=CrowEyes_Setup_'+version+'_Windows_x64',s)
installer.write_text(s,encoding='utf-8')
manifest=ROOT/'store/AppxManifest.xml'
s=manifest.read_text(encoding='utf-8')
s=re.sub(r'(<Identity[^>]+ Version=")[^"]+',r'\g<1>'+data['store_version'],s)
manifest.write_text(s,encoding='utf-8')
print('Version:',version,'GitHub:',data['release_tag'],'Store:',data['store_version'])
