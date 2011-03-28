#!/usr/bin/python
import Foundation, shutil, errno
from zipfile import ZipFile
from contextlib import closing
from sys import argv
from os import makedirs
from os.path import abspath
from os.path import join as path_join

class HCZipFile(ZipFile):
    def find(self, name, level=2):
        def at_pos(lst, pos):
            #print "l: %s, p: %s" % (lst, pos)
            return lst[pos] if len(lst) > pos else ""
        best_candidates = [n for n in self.namelist() if at_pos(n.split('/'), level).lower() == name]
        if best_candidates:
            candidates = best_candidates
        else:
            candidates = [n for n in self.namelist() if at_pos(n.split('/'), level).endswith(name)]
        if not candidates:
            raise Exception("couldn't find", name)
        #print 'candidates for %s at %s:' % (name, level)
        #print candidates
        return candidates[0]
    def dig_out(self, name, level=2):
        fh = self.open(self.find(name, level))
        result = fh.read()
        fh.close()
        return result

if len(argv) != 4:
    print 'arguments: ipa, url, publish dir'
    raise SystemExit
ipa_name = argv[1]
url = argv[2].rstrip('/')
publish_dir = abspath(argv[3])
try:
    makedirs(publish_dir)
except OSError as e:
    if e.errno == errno.EEXIST:
        pass
    else:
        raise

index_html_template = """ <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
<title>%(bundle_name)s</title>
<style type="text/css">
body {background:#fff;margin:0;padding:0;font-family:arial,helvetica,sans-serif;text-align:center;padding:10px;color:#333;font-size:13px;}
#container {width:320px;}
h1 {margin:0; padding:0; font-size:14px;}
.link {background:#f5f5f5;border-top:1px solid #fff;border:1px solid #dddddd;margin-top:.5em;padding:.3em;}
.link a {text-decoration:none;font-size:15px;display:block;color:#336699;}

</style>
</head>
<body>

<div id="container">

<h1>iOS 4.0 and above:</h1>
<div class="link"><a href="itms-services://?action=download-manifest&url=%(url)s/manifest.plist">Tap Here to Install<br />%(bundle_name)s</a></div>
<h1 style="margin-top:1em;">Pre iOS 4.0:</h1>
Use your regular computer to download the zip below and install its contents via iTunes.
<div class="link"><a href="app_archive.zip">%(bundle_name)s<br />Version for older iOS devices</a></div>
</div>
</body>
</html>"""

plist_template = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>items</key>
        <array>
                <dict>
                        <key>assets</key>
                        <array>
                                <dict>
                                        <key>kind</key>
                                        <string>software-package</string>
                                        <key>url</key>
                                        <string>%(url)s/application.ipa</string>
                                </dict>
                        </array>
                        <key>metadata</key>
                        <dict>
                                <key>bundle-identifier</key>
                                <string>%(bundle_id)s</string>
                                <key>bundle-version</key>
                                <string>%(bundle_version)s</string>
                                <key>kind</key>
                                <string>software</string>
                                <key>title</key>
                                <string>%(bundle_name)s</string>
                        </dict>
                </dict>
        </array>
</dict>
</plist>"""

with closing(HCZipFile(ipa_name,'r')) as za:
    provision = za.dig_out('.mobileprovision')
    info_plist_s = za.dig_out('info.plist')
    info_plist_d = Foundation.NSData.dataWithBytes_length_(info_plist_s, len(info_plist_s))
info_plist = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(info_plist_d, 0, None)[0]

ofk = lambda key:info_plist.objectForKey_(key)
info_plist_dict = dict(url=url, 
        bundle_id = ofk('CFBundleIdentifier'), 
        bundle_name = ofk('CFBundleName'),
        bundle_version = ofk('CFBundleVersion'))
print info_plist_dict
plist_out = plist_template % info_plist_dict
o = lambda fn: open(path_join(publish_dir, fn), 'w')
print "writing to", publish_dir
with o('index.html') as fh:
    print 'index.html'
    fh.write(index_html_template % info_plist_dict)
with o('manifest.plist') as fh:
    print 'manifest.plist'
    fh.write(plist_template % info_plist_dict)

app_archive = 'app_archive.zip'
with closing(HCZipFile(path_join(publish_dir, app_archive), 'w')) as zip:
    zip.write(ipa_name, 'application.ipa') 
    zip.writestr('provision.mobileprovision', provision)

print 'application.ipa'
shutil.copy(ipa_name, path_join(publish_dir, 'application.ipa'))

print app_archive
print 'done'
print url

