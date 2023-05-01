#!/usr/bin/env python3

from bs4 import BeautifulSoup
import json
from filters import mesafilter
from filters import webkitgtkfilter
from filters import brotlifilter
from filters import rustfilter
from filters import bluezfilter
from filters import frameworks5filter
from filters import plasmafilter
from filters import gimpfilter
from filters import linux_pam_filter
from filters import boostfilter
from filters import cupsfilter
from filters import gnomeshellextensionsfilter
from filters import openldapfilter
from filters import kframeworksplasma
from filters import pnmixer
from filters import rustfilter1
from filters import kframeworksfilter

systemd_service_tarball_url = 'http://www.linuxfromscratch.org/blfs/downloads/9.0-systemd/blfs-systemd-units-20180105.tar.bz2'
systemd_service_tarball = systemd_service_tarball_url.split('/')[-1]
systemd_service_dir = systemd_service_tarball[0:systemd_service_tarball.index('.')]

with open('config/templates/script_template') as tfp:
	template = tfp.read()

with open('config/templates/bin-template') as tfp:
	bin_template = tfp.read()

def load_json(file_path):
	with open(file_path, 'r') as fp:
		return json.load(fp)

additional_commands = load_json('config/additional_commands.json')
additional_downloads = load_json('config/additional_downloads.json')
deletions = load_json('config/deletion.json')
variables = load_json('config/variables.json')
expendable_deps = load_json('config/expendable_dependencies.json')
replaceable_deps = load_json('config/replacable_dependencies.json')
pkg_expendable_deps = load_json('config/package_expendable_dependencies.json')
url_deletion = load_json('config/url_deletion.json')
replaceable_cmds = load_json('config/replaceable_commands.json')
pkg_replaceable_cmds = load_json('config/package_replaceable_commands.json')
final_cmds = load_json('config/final-commands.json')

custom_package_filters = [
	mesafilter,
	webkitgtkfilter,
	brotlifilter,
	rustfilter, 
	bluezfilter, 
	frameworks5filter, 
	plasmafilter, 
	gimpfilter, 
	linux_pam_filter, 
	boostfilter, 
	cupsfilter, 
	gnomeshellextensionsfilter, 
	openldapfilter,
	kframeworksplasma,
	pnmixer,
	rustfilter1,
	kframeworksfilter
]

def get_package_sections(book_dir):
	doc = BeautifulSoup(read_raw(book_dir + '/index.html').decode("latin-1"), 'html.parser')
	section_anchors = doc.select("h4 a")
	sections = dict()
	for section_anchor in section_anchors:
		anchor_text = section_anchor.text
		href = section_anchor.attrs['href']
		parts = anchor_text.split(' ')
		parts = parts[1:]
		parts = map(str.strip, parts)
		parts = filter(lambda x : len(x) > 0, list(parts))
		section = ' '.join(parts)
		sections[section] = list()
		doc1 = BeautifulSoup(read_raw(book_dir + '/' + href).decode("latin-1"), 'html.parser')
		pkg_anchors = doc1.select('div.toc ul li a')
		for pkg_anchor in pkg_anchors:
			sections[section].append(pkg_anchor.attrs['href'].replace('.html', '').lower())
	return sections

def read_processed(file_path):
	with open(file_path, 'rb') as fp:
		data = fp.read()
	return data

def read_raw(file_path):
	with open(file_path, 'rb') as fp:
		data = fp.read()
	return data

def get_tarball(download_urls):
	if len(download_urls) > 0:
		return download_urls[0].split('/')[-1]

def is_number(number):
	for ch in number:
		if not str(ch).isdigit() and ch != '.':
			return False
	return True

def get_version(tarball):
	if tarball != None and is_number(tarball):
		return tarball
	start = -1
	end = -1
	if tarball != None:
		#print(tarball)
		for i, ch in enumerate(tarball):
			#print(str(i) + ': ' + str(ch))
			if (str(ch).isdigit() and tarball[i + 1] != '-' or ch == '.') and start == -1:
				#print('Start initialized')
				if '-' in tarball and i < tarball.index('-'):
					continue
				start = i
			if str(ch).isdigit() == False and start != -1 and ch != '.':
				#print('End initialized')
				end = i - 1
				break
		#print(str(start) + ':' + str(end))
		return tarball[start:end]

def process_html_data(data):
	parts = data.split(' ')
	space_removed = ''
	for part in parts:
		if part == '':
			continue
		space_removed = space_removed + part
		if not part[-1] == '\n':
			space_removed = space_removed + ' '
	modified = space_removed.replace('=\n', '=')
	print(modified)
	return modified

def get_systemd_service_install_cmds(cmd):
	return '#!/bin/bash\n\nset -e\nset +h\n\n. /etc/alps/alps.conf\n\npushd $SOURCE_DIR\nwget -nc ' + systemd_service_tarball_url + '\ntar xf ' + systemd_service_tarball + '\ncd ' + systemd_service_dir + '\nsudo ' + cmd + '\npopd'

def Diff(li1, li2):
	result = li1.copy()
	for item in li2:
		if item in result:
			result.remove(item)
	return result

def clean_dependencies(package):
	new_deps = list()
	for dep in package['dependencies']:
		if 'x7driver#' in dep and dep.index('x7driver#') == 0:
			new_deps.append(dep.replace('x7driver#', ''))
			continue
		if dep not in expendable_deps:
			new_deps.append(dep.lower())
	final_deps = list()
	for dep in new_deps:
		if '/' in dep:
			final_deps.append(dep[dep.rindex('/') + 1:])
		else:
			final_deps.append(dep)
	if package['name'] in pkg_expendable_deps:
		package['dependencies'] = Diff(final_deps, pkg_expendable_deps[package['name']])
	else:
		package['dependencies'] = final_deps
	for dep, replacement in replaceable_deps.items():
		if dep in package['dependencies']:
			package['dependencies'].remove(dep)
			package['dependencies'].append(replacement)

def delete_url_if_needed(package):
	if package['name'] in url_deletion:
		package['download_urls'].clear()

def clean_commands(package):
	if package['name'] != 'sudo':
		package['commands'] = 'echo $USER > /tmp/currentuser\n\n' + package['commands']
	for key, value in replaceable_cmds.items():
		if 'commands' in package and key in package['commands']:
			package['commands'] = package['commands'].replace(key, value)

def endswith(haystack, needle):
	return needle in haystack and haystack.index(needle) == len(haystack) - len(needle)

def modify_patch_downloads(package, version, patches_file):
	modified = list()
	for url in package['download_urls']:
		if endswith(url, '.patch'):
			with open(patches_file, 'a') as fp:
				fp.write(url + '\n')
			modified.append('https://bitbucket.org/chandrakantsingh/patches/raw/' + version + '/' + url[url.rindex('/')+1:])
		else:
			modified.append(url)
	return modified

def parse_package(file_path, version, patches_file):
	package = dict()
	doc = BeautifulSoup(read_raw(file_path).decode("latin-1"), 'html.parser')
	package['name'] = file_path.split('/')[-1].replace('.html', '').lower()
	package['download_urls'] = list()
	package['dependencies'] = list()
	download_links = doc.select('div.itemizedlist ul.compact a.ulink[href]')
	for link in download_links:
		package['download_urls'].append(link.attrs['href'])
	package['download_urls'] = modify_patch_downloads(package, version, patches_file)
	for link in doc.select('p.required a.xref , p.recommended a.xref '):
		package['dependencies'].append(link.attrs['href'].split('/')[-1].replace('.html', ''))
	clean_dependencies(package)
	package['tarball'] = get_tarball(package['download_urls'])
	package['version'] = get_version(package['tarball'])
	commands = list()
	cmd_pres = doc.select('pre.userinput, pre.root')
	for cmd_pre in cmd_pres:
		if package['name'] == 'sudo':
			commands.append(cmd_pre.select('kbd.command')[0].text.strip())
		else:
			if cmd_pre.attrs['class'][0] == 'userinput':
				commands.append(cmd_pre.select('kbd.command')[0].text.strip())
			elif cmd_pre.attrs['class'][0] == 'root':
				if len(cmd_pre.select('kbd.command')) == 0:
					continue
				else:
					cmd = cmd_pre.select('kbd.command')[0].text.strip()
					# lynx has a make install-full command, needs bypassing
					if package['name'] != 'texlive' and package['name'] != 'lynx' and 'make install-' in cmd and cmd.index('make install-') == 0:
						cmd = get_systemd_service_install_cmds(cmd)
				root_cmd = 'sudo rm -rf /tmp/rootscript.sh\ncat > /tmp/rootscript.sh <<"ENDOFROOTSCRIPT"\n' + cmd + '\nENDOFROOTSCRIPT\n\nchmod a+x /tmp/rootscript.sh\nsudo /tmp/rootscript.sh\nsudo rm -rf /tmp/rootscript.sh\n'
				commands.append(root_cmd)
	if package['name'] in final_cmds:
		commands.extend(final_cmds[package['name']])
	for filter_function in custom_package_filters:
		(package, commands) = filter_function(package, commands)
	cmds = list()
	if package['name'] in deletions:
		for command in commands:
			do_add = True
			for deletable in deletions[package['name']]:
				if deletable in command:
					do_add = False
					break
			if do_add:
				cmds.append(command)
	else:
		cmds = commands
	if package['name'] in additional_commands:
		if additional_commands[package['name']]['position'] != 1000:
			cmds.insert(additional_commands[package['name']]['position'], additional_commands[package['name']]['command'])
		else:
			cmds.append(additional_commands[package['name']]['command'])
	package['commands'] = '\n'.join(cmds)
	if package['name'] in pkg_replaceable_cmds:
		for replaceable_element in pkg_replaceable_cmds[package['name']]:
			for orig, replacement in replaceable_element.items():
				package['commands'] = package['commands'].replace(orig, replacement)
	str_vars = ''
	for key, value in variables.items():
		if key in package['commands']:
			str_vars = str_vars + 'export ' + key + '="' + value + '"\n'
	package['commands'] = str_vars + '\n' + package['commands']
	delete_url_if_needed(package)
	clean_commands(package)
	return package

def parse_perl_modules(file_path):
	modules = list()
	doc = BeautifulSoup(read_raw(file_path).decode("latin-1"), 'html.parser')
	module_links = doc.select('div.itemizedlist ul.compact li p a.xref')
	for module_link in module_links:
		package = dict()
		name = module_link.attrs['href'][module_link.attrs['href'].index('#') + 1:]
		prefix = module_link.attrs['href'][:module_link.attrs['href'].index('#')].replace('.html', '')
		if prefix == 'x7driver':
			prefix = ''
		if 'perl-alternative' in name:
			continue
		if prefix != '':
			package['name'] = prefix + '#' + name
		else:
			package['name'] = name
		package['name'] = package['name'].lower()
		module_div = doc.select('div.sect2 h2.sect2 a#' + name)[0].parent.parent.select('div.package, div.installation')
		package['download_urls'] = list()
		urls = module_div[0].select('ul.compact  li p a.ulink')
		for url in urls:
			package['download_urls'].append(url.attrs['href'])
		#package['url'] = package['download_urls'][0]
		package['dependencies'] = list()
		deps = module_div[0].select('p.recommended a.xref, p.required a.xref')
		for dep in deps:
			package['dependencies'].append(dep.attrs['href'].replace('.html', ''))
		clean_dependencies(package)
		commands = list()
		cmds = module_div[1].select('pre.userinput, pre.root')
		for cmd in cmds:
			if cmd.attrs['class'][0] == 'userinput':
				commands.append(cmd.select('kbd.command')[0].text.replace('&&\nmake test', '').strip())
			elif cmd.attrs['class'][0] == 'root':
				commands.append('sudo rm -rf /tmp/rootscript.sh\ncat > /tmp/rootscript.sh <<"ENDOFROOTSCRIPT"\n' + cmd.select('kbd.command')[0].text + '\nENDOFROOTSCRIPT\n\nchmod a+x /tmp/rootscript.sh\nsudo /tmp/rootscript.sh\nsudo rm -rf /tmp/rootscript.sh\n')
		cmds = list()
		if package['name'] in deletions:
			for command in commands:
				do_add = True
				for deletable in deletions[package['name']]:
					if deletable in command:
						do_add = False
						break
				if do_add:
					cmds.append(command)
		else:
			cmds = commands
		if package['name'] in additional_commands:
			cmds.insert(additional_commands[package['name']]['position'], additional_commands[package['name']]['command'])
		package['commands'] = '\n'.join(cmds)
		package['tarball'] = get_tarball(package['download_urls'])
		package['version'] = get_version(package['tarball'])
		clean_commands(package)
		str_vars = ''
		for key, value in variables.items():
			if key in package['commands']:
				str_vars = str_vars + 'export ' + key + '="' + value + '"\n'
		package['commands'] = str_vars + '\n' + package['commands']
		if package['name'] in additional_downloads:
			for url in additional_downloads[package['name']]:
				package['download_urls'].append(url)
		if package['name'] in additional_commands:
			package['commands'].insert(additional_commands[package['name']].position, additional_commands[package['name']].command)
		modules.append(package)
	return modules

def print_package(package):
	print(package['name'])
	print(package['download_urls'])
	print(package['dependencies'])
	print(package['tarball'])
	print(package['version'])
	print(package['commands'])

def get_script(p):
	tmp = '' + template
	deps = ''
	if p['dependencies'] != None:
		for dep in p['dependencies']:
			deps = deps + '#REQ:' + dep + '\n'
	else:
		deps = ''
	tmp = tmp.replace('##DEPS##', deps)
	if p['name'] != None:
		tmp = tmp.replace('##NAME##', 'NAME=' + p['name'])
	if 'description' in p:
		tmp = tmp.replace('##DESCRIPTION##', 'DESCRIPTION="' + p['description'] + '"')
	else:
		tmp = tmp.replace('##DESCRIPTION##\n', '')
	if 'section' in p:
		tmp = tmp.replace('##SECTION##', 'SECTION="' + p['section'].replace('.html', '') + '"')
	else:
		tmp = tmp.replace('##SECTION##\n', '')
	if p['version'] != None:
		tmp = tmp.replace('##VERSION##', 'VERSION=' + p['version'])
	else:
		tmp = tmp.replace('##VERSION##', '')
	urls = ''
	if len(p['download_urls']) > 0:
		if 'url' not in p:
			tmp = tmp.replace('##URL##', 'URL=' + p['download_urls'][0])
			for url in p['download_urls']:
				urls = urls + 'wget -nc ' + url + '\n'
			tmp = tmp.replace('##DOWNLOADS##', urls)
		else:
			if p['url'] == None:
				tmp = tmp.replace('##URL##', '')
				for url in p['download_urls']:
					urls = urls + 'wget -nc ' + url + '\n'
				tmp = tmp.replace('##DOWNLOADS##', urls)
	else:
		tmp = tmp.replace('##URL##', '')
		tmp = tmp.replace('##DOWNLOADS##', '')
		tmp = tmp.replace('##VERSION##', '')
	if p['commands'] == None or len(p['commands']) > 0:
		tmp = tmp.replace('##COMMANDS##', p['commands'])
	else:
		tmp = tmp.replace('##COMMANDS##', '')
	return tmp

def get_bin_script(p):
	tmp = '' + bin_template
	deps = ''
	if p['dependencies'] != None:
		for dep in p['dependencies']:
			deps = deps + '#REQ:' + dep + '\n'
	else:
		deps = ''
	tmp = tmp.replace('##DEPS##', deps)
	if p['name'] != None:
		tmp = tmp.replace('##NAME##', 'NAME=' + p['name'])
	if p['version'] != None:
		tmp = tmp.replace('##VERSION##', 'VERSION=' + p['version'])
	else:
		tmp = tmp.replace('##VERSION##', '')
	urls = ''
	if len(p['download_urls']) > 0:
		tmp = tmp.replace('##URL##', '')
		for url in p['download_urls']:
			urls = urls + 'wget -nc ' + url + '\n'
		tmp = tmp.replace('##DOWNLOADS##', urls)
	else:
		tmp = tmp.replace('##URL##', '')
		tmp = tmp.replace('##DOWNLOADS##', '')
		tmp = tmp.replace('##VERSION##', '')
	if p['commands'] == None or len(p['commands']) > 0:
		tmp = tmp.replace('##COMMANDS##', p['commands'])
	else:
		tmp = tmp.replace('##COMMANDS##', '')
	return tmp

def package_clone(package, new_name, removable_deps):
	pkg = package.copy()
	pkg['name'] = new_name
	for dep in removable_deps:
		if dep in pkg['dependencies']:
			pkg['dependencies'].remove(dep)
	return pkg

def find_package(packages, name):
	for package in packages:
		if package['name'] == name:
			return package

def get_section(package, sections):
	pkg_section = None
	for section_name, pkgs in sections.items():
		if package['name'] in pkgs:
			pkg_section = section_name
	if pkg_section == None:
		pkg_section = 'Others'
	return pkg_section

def get_descriptions(base_url):
	descriptions = dict()
	base_url = '/home/chandrakant/aryalinux/books/blfs/'
	doc = BeautifulSoup(read_processed(base_url + 'index.html'), features="lxml")
	anchors = doc.select('a[href]')
	skip_chapters = ['preface', 'introduction']

	for anchor in anchors:
		parts = anchor.attrs['href'].split('/')
		if len(parts) < 2:
			continue
		chapter = parts[0]
		filename = parts[1]
		packagename = filename.replace('.html', '').lower()
		if chapter not in skip_chapters:
			doc = BeautifulSoup(read_processed(base_url + anchor.attrs['href']), features="lxml")
			try:
				firstp = doc.select('div.package p')[0]
				description = firstp.text
				lines = description.split('\n')
				new_desc = list()
				for line in lines:
					if (len(line.strip())) != 0:
						new_desc.append(line.strip())
				description = ' '.join(new_desc)
				if '"' in description:
					description = description.replace('\"', '\\\"')
				descriptions[packagename] = description
			except:
				pass

	return descriptions