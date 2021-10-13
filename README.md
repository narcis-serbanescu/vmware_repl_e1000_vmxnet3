# Automated method to replace E1000 NICs with VMXNET3     


The add_nic_mp.py script can be run from every system that have Python installed, along with few supplementary modules required by the script, like:
- Vmware / pyvmomi: https://github.com/vmware/pyvmomi     
- Termcolor: https://pypi.org/project/termcolor/     




What the script is requiring and doing:
- It can be run without any argument: $ sudo python add_nic_mp.py    
- A list of affected VM is required to be pasted in a file named vmlist.txt. The list of affected VMs can be found in the Change scheduled previously by AHT team. In case vmlist.txt file is missing, the script requires a VM name as argument
- Authentication to vCenter is done via auth_cms_module.py
- Current network configuration is saved in a separate json file for each VM.
- Remove existing E1000 NIC
- Add new VMXNET3 NIC with the same configuration (Label, MAC, DVS)
- Boot order is updated in case of many disks and controllers - https://kb.vmware.com/s/article/2011654?lang=en_US
- Parallel processing is used to modify NICs for all VMs found in list in almost the same time
- During NIC replacement RHEL VMs remain accessible through ssh, no network disruption were observed, no AHT intervention is necessary, while in Windows VM case, AHT intervention is mandatory to enable new NIC drivers at OS level. 

