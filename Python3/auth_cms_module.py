#!/usr/bin/env python

'''
Script for getting CMS 1.x/2.x VM details.
Author: Narcis Serbanescu
Email: narcis_serbanescu@ro.ibm.com
Date: 12/04/2018
Version: 0.1
'''

import atexit
from pyVim.connect import SmartConnect, Disconnect
import ssl
import logging
from termcolor import colored


s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
s.verify_mode = ssl.CERT_NONE
vc_user = "vcenter@ssm"
vc_password = "********"


def cms_site():
    global vc_name, my_site, my_site_type
    site_code = ['deeh', 'es03', 'brho', 'frgr', 'ukpm', 'gbfm', 'us22',
                 'usbd', 'usrd', 'au04', 'jp08', 'catr', 'chwt', 'nl03',
                 'usrds2', 'usrds8', 'usrds9', 'deeh3']
    print ", " .join(site_code)
    # https://www.quora.com/What-should-we-write-to-make-the-system-exit-if-user-enter-invalid-input-in-Python-2-7
    while(True):
        my_site = raw_input("Infra code site or Quit [q]: ")
        if not my_site or my_site == "q":
            exit()
        elif my_site in site_code:
            break
        else:
            print colored(my_site + " " + "is an invalid input. Please try again!", "red")
            continue
    site_type = ['a', '1']
    while(True):
        my_site_type = raw_input("Site type - Infra [a] or POD [1] or Quit [q]: ")
        if my_site_type == "q":
            exit()
        elif my_site_type in site_type:
            break
        else:
            print colored(my_site_type + " " + "Is an invalid input. Please try again", "red")
            continue
    if my_site_type == "1" and my_site in ['deeh', 'usrd']:
        vc_name  = [my_site + "vcr011ccpv" + my_site_type,  my_site + "vcr011ccpv" + '2']
        return vc_name
        print "vCenter hostname: %s." % vc_name
        # ABN case: nl03vcr011ccpv1, nl03vcr021ccpv1, nl03vcr011ccpv2
    elif my_site_type == "1" and my_site in ['nl03']:
        vc_name = [my_site + "vcr0" + '1' + "1ccpv" + my_site_type,
                    my_site + "vcr0" + '2' + "1ccpv" + my_site_type,
                    my_site + "vcr0" + '1' + "1ccpv2"]
        return vc_name
        print "vCenter hostname: %s." % vc_name

    elif my_site_type == "a" and my_site in ['usrds2']:
        vc_name = ["usrdvcr012ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name
    elif my_site_type == "1" and my_site in ['usrds2']:
        vc_name = ["usrdvcr012ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name
    elif my_site_type == "a" and my_site in ['usrds8']:
        vc_name = ["usrdvcr018ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name
    elif my_site_type == "a" and my_site in ['usrds9']:
        vc_name = ["usrdvcr019ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name
    elif my_site_type == "1" and my_site in ['usrds8']:
        vc_name = ["usrdvcr018ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name
    elif my_site_type == "a" and my_site in ['deeh3']:
        vc_name = ["deehvcr003ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name

    elif my_site_type == "a" and my_site in ['deeh']:
        cmsv = ['1', '2']
        while(True):
            cms_ver = raw_input("EHN 1x [1] or 2x [2]: ")
            if cms_ver in cmsv:
                break
            else:
                print colored(cms_ver + " " + "Is an invalid input. Please try again", "red")
                continue
        if cms_ver == "2":
            vc_name = [my_site + "vcr016ccpv" + my_site_type]
            return vc_name
            print "vCenter hostname: %s." % vc_name
        elif cms_ver == "1":
            vc_name = [my_site + "vcr011ccpv" + my_site_type]
            return vc_name
            print "vCenter hostname: %s." % vc_name
    else:
        vc_name = [my_site + "vcr011ccpv" + my_site_type]
        return vc_name
        print "vCenter hostname: %s." % vc_name


def exit_my_conn():
    print colored("Connection to %s is ending" % vc, "red")
    Disconnect(my_conn)


def vc_conn(my_conn):
    try:
        for vc in vc_name:
            vc = vc+".ssm.sdc.gts.ibm.com"
            my_conn = SmartConnect(host=vc, user=vc_user, pwd=vc_password, sslContext=s)
            if not my_conn:
                raise SystemExit("Unable to connect to host with supplied info.")
            atexit.register(Disconnect, my_conn)
            print colored ("Searching in: "+vc, "yellow")
            print colored (my_conn.CurrentTime(), "yellow")
            aboutInfo=my_conn.content.about
            print colored("Connected to %s, %s" % (vc, aboutInfo.fullName), "green")
            global content
            content = my_conn.RetrieveContent()
            #print (content, dir(content))
            return content

    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
        logging.error("Could not connect to vcenter." + str(e))
        pass


def main():
    cms_site()
    my_conn = None
    vc_conn(my_conn)


if __name__ == "__main__":
    main()
