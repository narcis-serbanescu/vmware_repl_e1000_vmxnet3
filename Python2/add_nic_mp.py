#!/usr/bin/env python
'''
Script for changing VMs NICs.
Author: Narcis Serbanescu
Email: narcis_serbanescu@ro.ibm.com
Date: 2020/05/12
Version: 1.0
'''

from pyVmomi import vim, vmodl
import tasks
import time
import json
from datetime import datetime
import logging
import multiprocessing as ThreadPool
import auth_cms_module as acm
from auth_cms_module import *


def exit_my_conn(vc):
    cprint("Connection to %s is ending" % vc, "red")
    Disconnect(my_conn)


def write_json(vm, lst_dct):
    global json_file
    dt = dt_now.strftime("%Y%m%d_%H%M%S")
    json_file = vm.name + "-nic-" + dt + ".json"
    with open(json_file, 'a') as f:
        json.dump(lst_dct, f, ensure_ascii=False, indent=4)


def VMpowerON(vm):
    cprint("Powering " + vm.name + " on ...", "green")
    try:
        poweron_task = vm.PowerOn()
        tasks.wait_for_tasks(my_conn, [poweron_task])
        cprint ("VM is up and running!", "green")
    # except Exception:
    except vmodl.MethodFault as e:
        cprint("Unexpected error while powering on vm: " + vm.name + e.msg, "red")


def VMpowerOFF(vm, ptask):
    cprint("Shutting " + vm.name + " down...", "green")
    if ptask == "powerOff":
        pwoff_task = vm.PowerOff()
    elif ptask == "shutdown":
        pwoff_task = vm.ShutdownGuest()
    try:
        pwoff_task
        # pwoff_task = vm.ShutdownGuest()
        ## pwoff_task = vm.PowerOff()
        while True:
            time.sleep(10)
            cprint (vm.name + " state is: " + vm.summary.runtime.powerState, "yellow")
            if vm.summary.runtime.powerState == "poweredOff":
                break
        cprint ("VM is not running!", "green")
    # except Exception:
    except vmodl.MethodFault as e:
        cprint("Unexpected error while powering off vm: " + vm.name + e.msg , "red")


def ResetVM(vm):
    cprint ("Quick reset ...", "cyan")
    VMpowerOFF(vm, "powerOff")
    time.sleep(5)
    # vm.PowerOff()
    VMpowerON(vm)
    cprint (vm.name + " state is: " + vm.summary.runtime.powerState, "yellow")


def vminfo(vm):
    # cprint (vm + ", "+ vm.name, "cyan")
    # cprint(vm.runtime.host.parent, "yellow")
    cprint("VM info for: " + vm.name, "cyan")
    print("VM: {0}, MOR ID: {1}, FQDN: {2}".format(vm.name,
            vm._moId, vm.guest.hostName))
    print("Cluster: {0}, Datacenter: {1}, Host: {2}".format(vm.runtime.host.parent.name,
                vm.runtime.host.parent.parent.parent.name,
                vm.runtime.host.name))
    print("VMware Tools: {0}, Version: {1}, Status: {2}".format(vm.guest.toolsRunningStatus,
                vm.guest.toolsVersion,
                vm.guest.toolsVersionStatus2))
    print("Status: {0}, Boot: {1}, Connection: {2}".format(vm.summary.runtime.powerState,
                    vm.summary.runtime.bootTime,
                    vm.summary.runtime.connectionState))
    global vminfo_list
    vminfo_list = list()
    vminfo_dict = {"VM": vm.name,
                    "MOR_ID": vm._moId,
                    "FQDN": vm.guest.hostName,
                    "Status": vm.summary.runtime.powerState,
                    "Boot": str(vm.summary.runtime.bootTime),
                    "Connection": vm.summary.runtime.connectionState,
                    "Cluster": vm.runtime.host.parent.name,
                    "Datacenter": vm.runtime.host.parent.parent.parent.name,
                    "Host": vm.runtime.host.name,
                    "VMware Tools": vm.guest.toolsRunningStatus,
                    "VMware Tools ver": vm.guest.toolsVersion,
                    "VMware Tools conn": vm.summary.runtime.connectionState
                    }
    vminfo_list.append(vminfo_dict)

    print (json.dumps(vminfo_list, indent=4))
    print ("Export data in json file")
    write_json(vm, vminfo_list)


def get_ip(vm):
    cprint("Network (ip, mac) info for: " + vm.name, "cyan")
    if vm.guest.toolsRunningStatus == "guestToolsRunning":
        cprint("Network info from vm.guest: " + vm.name, "yellow")
        # Getting IPs, MACs and Networks
        vnic_list = [nic for nic in vm.guest.net if nic.connected is True]
        ip_list = [nic.ipAddress for nic in vnic_list]
        zip_ip_list = [zip1 for zip1 in zip(*ip_list)]
        print (list(zip_ip_list[0]))
        # print('IP: [%s]' % ', '.join(map(str, list(zip_ip_list[0]))))

        mac_list = [nic.macAddress for nic in vnic_list]
        print (mac_list)

        net_list = [nic.network for nic in vnic_list]
        print (net_list)

        # Getting json format
        vm_vnics = list()
        for vnic in vnic_list:
            vnic_dict = dict()
            vnic_dict.update({"Network": vnic.network,
                              "IP": vnic.ipAddress[0],
                              "MAC": vnic.macAddress})
            vm_vnics.append(vnic_dict)
            vminfo_list.append(vnic_dict)
        print (json.dumps(vm_vnics, indent=4))
        print ("Export data in json file")
        # write_json(vm_vnics)
        # write_json(vm, vminfo_list)


def replace_nics(vm):
    cprint("Network info from vm.config: " + vm.name, "cyan")
    device = vm.config.hardware.device
    # switch_list = [switch for switch in device if type(switch).__name__ == 'vim.vm.device.VirtualVmxnet3']
    switch_list = [switch for switch in device if type(switch).__name__ == 'vim.vm.device.VirtualVmxnet3'
                    or type(switch).__name__ == 'vim.vm.device.VirtualE1000'
                    or type(switch).__name__ == 'vim.vm.device.VirtualE1000e']
    vnic_type_list = [type(switch).__name__.split(".")[3] for switch in switch_list]
    # print ("VNIC type: ", vnic_type_list)

    switch_label_list = [switch.deviceInfo.label for switch in switch_list]
    mac_list = [switch.macAddress for switch in switch_list]
    key_list= [switch.backing.port.portgroupKey for switch in switch_list if hasattr(switch.backing, 'port')]
    port_key_list= [switch.backing.port.portKey for switch in switch_list if hasattr(switch.backing, 'port')]

    DVS_key_list = [dvs.key for dvs in vm.network]
    dvs_list = [dvs for dvs in vm.network]
    DVP_list = [dvs.name for dvs in vm.network]

    DVS_name_list = [dvs.config.distributedVirtualSwitch.name for dvs in vm.network if hasattr(dvs, "config")]

    # https://stackoverflow.com/questions/11601961/sorting-multiple-lists-based-on-a-single-list-in-python
    key_list, port_key_list, switch_label_list, mac_list, vnic_type_list = zip(*sorted(zip(key_list, port_key_list, switch_label_list, mac_list, vnic_type_list)))
    DVS_key_list, DVP_list, DVS_name_list = zip(*sorted(zip(DVS_key_list, DVP_list, DVS_name_list)))

    # Final sort after Label
    switch_label_list, mac_list, dvs_list, port_key_list, DVS_name_list, DVP_list = \
        zip(*sorted(zip(switch_label_list, mac_list, dvs_list, port_key_list, DVS_name_list, DVP_list)))
    print ("Label: [%s]" % ', '.join(map(str, list(switch_label_list))))
    print ("MAC: [%s]" % ', '.join(map(str, list(mac_list))))
    print ("Port: [%s]" % ', '.join(map(str, list(port_key_list))))
    print ("Type: [%s]" % ', '.join(map(str, list(vnic_type_list))))
    print ("DVPgrp: [%s]" % ', '.join(map(str, list(DVP_list))))
    print ("DVS: [%s]" % ', '.join(map(str, list(DVS_name_list))))

    netdev_list = list()
    for switch_label, mac, port_key, vnic_type, DVP, DVS_name \
        in zip(switch_label_list, mac_list, port_key_list, vnic_type_list, DVP_list, DVS_name_list):
        netdev_dict = {"Label": switch_label, "MAC": mac, "Port": port_key, "Type": vnic_type, "DVP": DVP, "DVS": DVS_name}
        # netdev_list.append(netdev_dict)
        vminfo_list.append(netdev_dict)
    print (json.dumps(netdev_list, indent=4))
    print ("Export data in json file")
    # write_json(netdev_list)
    write_json(vm, vminfo_list)

    # Start removing & adding NICs
    nic_no = len(dvs_list)

    cprint ("Removing NICs: ", "red")
    # https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/delete_nic_from_vm.py
    for nic in range(1, nic_no + 1):
        nic_prefix_label = 'Network adapter '
        nic_label = nic_prefix_label + str(nic)
        virtual_nic_device = None
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) and dev.deviceInfo.label == nic_label:
                virtual_nic_device = dev

        if not virtual_nic_device:
            raise RuntimeError('Virtual {} could not be found.'.format(nic_label))

        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        virtual_nic_spec.device = virtual_nic_device

        spec = vim.vm.ConfigSpec()
        spec.deviceChange = [virtual_nic_spec]
        task = vm.ReconfigVM_Task(spec=spec)
        tasks.wait_for_tasks(my_conn, [task])
    print("NICs got REMOVED!")

    # ide_lst = [ide for ide in device if type(ide).__name__ == "vim.vm.device.VirtualIDEController"]
    # scsi_lst = [scsi for scsi in device if type(scsi).__name__ == "vim.vm.device.ParaVirtualSCSIController"]
    # print ("No of IDE controllers: %s" % len(ide_lst))
    no_disk = vm.summary.config.numVirtualDisks
    if no_disk > 1:
        print ("Setting boot order")
        print("No. of Disks: %s" % no_disk)
        # https://kb.vmware.com/s/article/2151704
        # https://kb.vmware.com/s/article/2011654?lang=en_US
        # https://superuser.com/questions/737614/how-to-set-the-bootorder-for-a-vm-in-vsphere-5-x-with-pysphere
        # https://www.egelev.com/2018/10/29/how-to-provide-input-parameters-to-a-running-virtual-machine/
        print("Set BIOS boot order")
        bootKey = 'bios.bootDeviceClasses'
        bootValue = 'allow:hd,cd,fd,net'
        bn = vim.option.OptionValue(key=bootKey, value=bootValue)
        vmconf = vim.vm.ConfigSpec()
        vmconf.extraConfig = [bn]
        # vm.ReconfigVM_Task(vmconf)
        btask = vm.ReconfigVM_Task(spec = vmconf)
        tasks.wait_for_tasks(my_conn, [btask])

        vdevice = vm.config.hardware.device
        scsi_lst = [scsi for scsi in vdevice if type(scsi).__name__ == "vim.vm.device.ParaVirtualSCSIController"]
        if len(scsi_lst) > 1:
            print ("No of SCSI controllers: %s" % len(scsi_lst))
            myKey = 'bios.hddOrderClasses'
            myValue = 'allow:scsi0:0,scsi0:1,scsi0:2,ide0:0,ide0:1'
            cspec = vim.vm.ConfigSpec()
            cspec.extraConfig = [vim.option.OptionValue(key=myKey, value=myValue)]
            vm.Reconfigure(cspec)
            # https://programtalk.com/vs2/python/11292/vmware-pyvmomi-examples/boot_vm_from_iso.py/
            bootConf = vim.vm.ConfigSpec()
            vmconf.bootOptions = vim.vm.BootOptions(bootOrder=[vim.vm.BootOptions.BootableDiskDevice()])
            btask2 = vm.ReconfigVM_Task(bootConf)
            tasks.wait_for_tasks(my_conn, [btask2])



    # ResetVM(vm)
    # time.sleep(300)


    cprint ("Adding NICs: ", "green")
    nic_type = ["VirtualE1000e", "VirtualVmxnet3"]
    # https://www.programcreek.com/python/example/92710/pyVmomi.vim.Network
    # https://github.com/StackStorm-Exchange/stackstorm-vsphere/blob/master/actions/stasis/new_networkadapter.py
    for nic in range(nic_no):
        network = dvs_list[nic]
        # device = vim.vm.device.VirtualVmxnet3(deviceInfo=vim.Description())
        device = vim.vm.device.VirtualVmxnet3()
        # device = vim.vm.device.VirtualE1000e()
        vim.vm.device.deviceInfo = vim.Description()
        vim.vm.device.deviceInfo.label = switch_label_list[nic]
        try:
            device.macAddress = mac_list[nic]
            device.addressType = vim.vm.device.VirtualEthernetCardOption.MacTypes.manual
        except Exception as e:
            print (e)

        # specify backing that connects device to a DVS switch portgroup
        dvs_port_conn = vim.dvs.PortConnection(portgroupKey=network.key, switchUuid=network.config.distributedVirtualSwitch.uuid)
        backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(port=dvs_port_conn)
        device.backing = backing
        # specify power status for nic
        device.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
                connected=False, startConnected=True, allowGuestControl=True)

        # build object with change specifications
        nicspec = vim.vm.device.VirtualDeviceSpec(device=device)
        nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        config_spec = vim.vm.ConfigSpec(deviceChange=[nicspec])
        # logger.info('Attaching network device to the virtual machine {}...'.format(name))
        task = vm.ReconfigVM_Task(config_spec)
        tasks.wait_for_tasks(my_conn, [task])
    print("NICs ADDED!")


def getvm(vmname):
    cprint(vmname, "yellow")
    # vm_list = list()
    global my_conn
    my_conn = None
    global vc
    # global vm
    for vc in acm.vc_name:
    # while vc:
        cprint (vc, "green")
        my_conn = SmartConnect(host=vc, user=acm.vc_user, pwd=acm.vc_password, sslContext=acm.s)
        if not my_conn:
            raise SystemExit("Unable to connect to host with supplied info.")
        atexit.register(Disconnect, my_conn)
        # atexit.register(exit_my_conn)
        cprint("Searching in: "+vc, "yellow")
        cprint(my_conn.CurrentTime(), "yellow")
        aboutInfo = my_conn.content.about
        cprint("Connected to %s, %s" % (vc, aboutInfo.fullName), "yellow")
        content = my_conn.RetrieveContent()
        #print (content, dir(content))

#    if my_conn:
        #cprint("Datacenters list using for", "red")
        # datacenters = [datacenter for datacenter in content.rootFolder.childEntity if hasattr(datacenter, "hostFolder")]
        datacenters = content.rootFolder.childEntity
        for datacenter in datacenters:
            print ("Available Folders and Datacenters: %s" % datacenter.name)
            # Avoid searching hosts in simply Folders
            if not hasattr(datacenter, "hostFolder"):
                continue
            cluster_list = [cluster for cluster in datacenter.hostFolder.childEntity if hasattr(cluster, 'host')]
            for cluster in cluster_list:
                cprint(cluster.name, "green")
                #print cluster.host
                esx_host = [host for host in cluster.host]
                esx_host_name = [hn.name for hn in esx_host]
                for host in esx_host:
                    cprint("Searching " + vmname + " VM in: " + host.name, "green")
                    vm_list = [vm for vm in host.vm if (vmname.lower()) == vm.name or (vmname.upper() == vm.name)]
                    cprint("Remaining VMs: " + vmname, "cyan")
                    # vm_list_name = [vm_vmlist.name for vm_vmlist in vm_list]
                    # cprint (vm_list_name, "cyan")
                    # print (len(vm_list))
                    if len(vm_list) == 1:
                        vm = vm_list[0]
                        # print(vm, vm.name, vmname)
                        start_VMtime = datetime.now()

                        vminfo(vm)
                        get_ip(vm)

                        # if vm.summary.runtime.powerState != 'poweredOff':
                          #   VMpowerOFF(vm, "shutdown")
                            #raise SystemExit(
                            #    "VM must be powered off before changing NICs! "
                            #    "Rerun the script after verifying VM was powered off. ")
                            #continue

                        replace_nics(vm)
                        # time.sleep(10)
                        # VMpowerON(vm)

                        end_VMtime = datetime.now()
                        print('Duration: {}'.format(end_VMtime - start_VMtime))
                        break


def main():
    global dt_now
    dt_now = datetime.now()
    acm
    acm.cms_site()
    # vmname = raw_input("VM name, eg. tec011 for ukpmtec011ccp8a, or TEM011 for UKPMTEM011CCP8A: ")
    # global vmname_list
    vmname = list()
    # vmname = ["lsghsux1"] # powered off with many disks
    # vmname = ["lo11doi1"] # powered off
    # vmname = ["usrd21q7110210"] # powered off
    # vmname = ["es0311gct2010", "es0311gct2011", "lo11doi1"]

    # if len(vmname) == 0:
    #     vm_name = raw_input("VM name, eg. tec011 for ukpmtec011ccp8a, or TEM011 for UKPMTEM011CCP8A: ")
    #     vmname.append(vm_name)

    if len(vmname) == 0:
        vmlist_file = "vmlist_e1000.txt"
        try:
            vmlist = open(vmlist_file, "r")
            for vm in vmlist:
                vm = vm.rstrip('\n')
                vmname.append(vm)
            vmlist.close()
        except IOError as e:
            cprint ("Unable to open file "+ vmlist_file, "red") #Does not exist OR no read permission
            print (e)
            vm_name = raw_input("VM name, eg. ukpmtec011ccp8a, or q for none: ")
            if not vm_name or vm_name == "q":
                exit()
            vmname.append(vm_name)
        finally:
            print (vmname)

    threads = len(vmname)
    # https://chriskiehl.com/article/parallelism-in-one-line
    start_dtime = datetime.now()
    # for vmname in vmname_list:
    #     getvm(vmname)
    pool = ThreadPool.Pool(threads)
    pool.map(getvm, vmname)
    ## close the pool and wait for the work to finish
    pool.close()
    pool.join()
    end_dtime = datetime.now()
    print('Duration: {}'.format(end_dtime - start_dtime))


if __name__ == "__main__":
    main()

