import time
import json
import os
import sys
import yaml
import re
from pprint import pprint
from netmiko import Netmiko,ConnectHandler
import datetime
from jinja2 import Template
import csv
import textfsm
from multiprocessing import Pool

create_delete_list = ['create','delete']
mep_meg_dmm_slm_list = ['meg','mep','dmm','slm']
maxhosts = 5

class Service:

    def __init__(self,**kwargs):
        self.data = kwargs

    def Command_Creation(self):                        
        for create_delete in create_delete_list:
            for node in self.data["site_list"]:
                with open('templates/create_xc_config_{}_{} copy.j2'.format(node["side"],create_delete),'r') as f:
                    Temp = f.read()
                    failure_command = Template(Temp).render(**self.data,**node)
                    file_open = open('templates/XC_command_{}_{}.txt'.format(node["Node_name"],create_delete), 'w+')
                    file_open.write(failure_command)
                    file_open.write('\n')
                    file_open.close()

    def push_config(self):
        for node in self.data["site_list"]:
            net_connect = Netmiko(**node['login'])
            with open('templates/XC_command_{}_create.txt'.format(node["Node_name"]),'r') as f:
                f2 = f.readlines()
                output = net_connect.send_config_set(f2)
                if node['login']['device_type'] == 'cisco_xr':
                    net_connect.commit()
                else:
                    pass
                #print(output)
                print("****  Configration completed on {}".format(node['Node_name']))
                net_connect.exit_config_mode()
                net_connect.disconnect()
            

    def delete_config(self):
        for node in self.data["site_list"]:
            net_connect = Netmiko(**node['login'])
            with open('templates/XC_command_{}_delete.txt'.format(node["Node_name"]),'r') as f:
                f2 = f.readlines()
                output = net_connect.send_config_set(f2)
                print(output)
                if node['login']['device_type'] == 'cisco_xr':
                    net_connect.commit()
                else:
                    pass
                net_connect.exit_config_mode()
                net_connect.disconnect()
    def parse_accedian(self):
        for node in self.data["site_list"]:
            if node['login']['device_type'] == 'cisco_xr':
                pass
            else:          
                net_connect = Netmiko(**node['login'])
                node['index'] = {}
                if node['Protected'] == 'YES':
                    node['out_port'] = 'LAG-{}'.format(node['Nni_port'] // 2 + 1)
                else:
                    node['out_port'] = 'PORT-{}'.format(node['Nni_port'])                                
                for mep_meg_dmm_slm in mep_meg_dmm_slm_list:
                    output = net_connect.send_command('cfm show {} configuration'.format(mep_meg_dmm_slm))
                    template = open('ntc/accedian_show_{}_index.textfsm'.format(mep_meg_dmm_slm))
                    re_table = textfsm.TextFSM(template)
                    fsm_results = re_table.ParseText(output)
                    if mep_meg_dmm_slm == 'meg':
                        node['index']['del_meg'] = 1
                        for rows in fsm_results:
                            if rows[1] == 'LEXXX-{}'.format(100000 + self.data['item']):
                                node['index']['del_meg'] = rows[0]
                    if len(fsm_results) == 0:
                        node['index'][mep_meg_dmm_slm] = 1
                    else:                   
                        node['index'][mep_meg_dmm_slm] = int(fsm_results[-1][0]) + 1
                net_connect.disconnect()
                print("****  persing completed on {}".format(node['Node_name']))
        return node['index']
    def Validate_ccm(self):
        for node in self.data["site_list"]:
            mep_name = 100000 + self.data['item']
            if 'EP' in node['side']:
                if node['login']['device_type'] == 'accedian':
                    net_connect = Netmiko(**node['login'])
                    print(node['Node_name'],end=' : ')
                    output = net_connect.send_command("cfm show mep status LEXXX-{}|{}|{}".format(mep_name,self.data['MEG_level'],node['Remote_MEP']))
                    if len(re.findall("Inactive", output)) == 14:
                        print("ccm is UP")
                    else:
                        print("CCm did not came Up")
                    net_connect.disconnect()          
                else:
                    net_connect = Netmiko(**node['login'])
                    print(node['Node_name'],end=' : ')
                    output = net_connect.send_command("show ethernet cfm services domain COLT-{} service ALX_NCS_LE-{}".format(self.data['MEG_level'],mep_name))
                    if len(re.findall("all operational, no errors", output)) == 2:
                        print("ccm is UP")
                    else:
                        print("CCm did not came Up")
                    net_connect.disconnect()
    def Y1564_test(self):
        list1 = []
        mep_name = 100000 + self.data['item']
        for node in self.data["site_list"]:
            if 'EP' in node['side']:
                list1.append(node['login']['device_type'])
        if list1 == ['accedian','accedian']:
            for node in self.data["site_list"]:
                if node['login']['device_type'] == 'accedian':
                    net_connect = Netmiko(**node['login'])
                    print(node['Node_name'],end=' : ')
                    output = net_connect.send_command("cfm show mep database LEXXX-{}|{}|{}".format(mep_name,self.data['MEG_level'],node['Remote_MEP']))
                    print(output)
                    net_connect.disconnect()
        elif list1 == ['cisco_xr','cisco_xr']:
            print("Loop can not be performed")
        elif list1 == ['cisco_xr','accedian'] or list1 == ['accedian','cisco_xr']:
            print("cisco to accedian loop")





