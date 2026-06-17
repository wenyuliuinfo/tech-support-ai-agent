# Prepare for VMware VM disaster recovery with Azure Site Recovery - Azure Site Recovery | Microsoft Learn

This article describes how to prepare on-premises VMware servers for disaster recovery to Azure by using the [Azure Site Recovery](site-recovery-overview) services.

This article is the second tutorial in a series that shows you how to set up disaster recovery to Azure for on-premises VMware VMs. In the first tutorial, you [set up the Azure components](tutorial-prepare-azure) needed for VMware disaster recovery.

In this article, you learn how to:

- Prepare an account on the vCenter server or vSphere ESXi host to automate VM discovery.
- Prepare an account for automatic installation of the Mobility service on VMware VMs.
- Review VMware server and VM requirements and support.
- Prepare to connect to Azure VMs after failover.

Note

Tutorials show you the simplest deployment path for a scenario. They use default options where possible, and don't show all possible settings and paths. For detailed instructions, review the article in the How To section of the Site Recovery Table of Contents.

## Before you start

Make sure you prepared Azure as described in the [first tutorial in this series](tutorial-prepare-azure).

## Prepare an account for automatic discovery

Site Recovery needs access to VMware servers to:

- Automatically discover VMs. At least a read-only account is required.
- Orchestrate replication, failover, and failback. You need an account that can run operations such as creating and removing disks, and powering on VMs.

Create the account as follows:

1. To use a dedicated account, create a role at the vCenter level. Give the role a name such as **Azure\_Site\_Recovery**.
2. Assign the role the permissions summarized in the following table.
3. Create a user on the vCenter server or vSphere host. Assign the role to the user.

### VMware account permissions

| **Task** | **Role/Permissions** | **Details** |
| --- | --- | --- |
| **VM discovery** | At least a read-only user Data Center object –&gt; Propagate to Child Object, role=Read-only | User assigned at datacenter level, and has access to all the objects in the datacenter. To restrict access, assign the **No access** role with the **Propagate to child** object, to the child objects (vSphere hosts, datastores, VMs and networks). |
| **Full replication, failover, failback** | Create a role (Azure\_Site\_Recovery) with the required permissions, and then assign the role to a VMware user or group Data Center object –&gt; Propagate to Child Object, role=Azure\_Site\_Recovery Datastore -&gt; Allocate space, browse datastore, low-level file operations, remove file, update virtual machine files Network -&gt; Network assign Resource -&gt; Assign VM to resource pool, migrate powered off VM, migrate powered on VM Tasks -&gt; Create task, update task Virtual machine -&gt; Configuration Virtual machine -&gt; Interact -&gt; answer question, device connection, configure CD media, configure floppy media, power off, power on, VMware tools install Virtual machine -&gt; Inventory -&gt; Create, register, unregister Virtual machine -&gt; Provisioning -&gt; Allow virtual machine download, allow virtual machine files upload Virtual machine -&gt; Snapshots -&gt; Remove snapshots, Create snapshots | User assigned at datacenter level, and has access to all the objects in the datacenter. To restrict access, assign the **No access** role with the **Propagate to child** object, to the child objects (vSphere hosts, datastores, VMs and networks). |

## Prepare an account for Mobility service installation

You must install the Mobility service on machines you want to replicate. Site Recovery can push-install this service when you enable replication for a machine, or you can install it manually or by using installation tools.

- In this tutorial, you install the Mobility service by using the push installation.
- For this push installation, prepare an account that Site Recovery can use to access the VM. Specify this account when you set up disaster recovery in the Azure console.

Prepare the account as follows:

Prepare a domain or local account with permissions to install on the VM.

- **Windows VMs**: To install on Windows VMs, if you're not using a domain account, disable UAC remote restrictions on the local machine. After disabling, Azure Site Recovery can access the local machine remotely without UAC restriction. To do this, in the registry: **HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System**, add the DWORD entry **LocalAccountTokenFilterPolicy**, with a value of 1.
- **Linux VMs**: To install on Linux VMs, prepare a root account on the source Linux server.

## Check VMware requirements

Make sure VMware servers and VMs comply with requirements.

1. [Verify](vmware-physical-azure-support-matrix#on-premises-virtualization-servers) VMware server requirements.
2. For Linux VMs, [check](vmware-physical-azure-support-matrix#linux-file-systemsguest-storage) file system and storage requirements.
3. Check on-premises [network](vmware-physical-azure-support-matrix#network) and [storage](vmware-physical-azure-support-matrix#storage) support.
4. Check what's supported for [Azure networking](vmware-physical-azure-support-matrix#azure-vm-network-after-failover), [storage](vmware-physical-azure-support-matrix#azure-storage), and [compute](vmware-physical-azure-support-matrix#azure-compute), after failover.
5. Your on-premises VMs you replicate to Azure must comply with [Azure VM requirements](vmware-physical-azure-support-matrix#azure-vm-requirements).
6. In Linux virtual machines, device name or mount point name should be unique. Ensure that no two devices or mount points have the same names. Note that names aren't case-sensitive. For example, naming two devices for the same VM as *device1* and *Device1* isn't allowed.

## Prepare to connect to Azure VMs after failover

After failover, you might want to connect to the Azure VMs from your on-premises network.

To connect to Windows VMs using RDP after failover, do the following:

- **Internet access**. Before failover, enable RDP on the on-premises VM before failover. Make sure that TCP, and UDP rules are added for the **Public** profile, and that RDP is allowed in **Windows Firewall** &gt; **Allowed Apps**, for all profiles.
- **Site-to-site VPN access**:
    - Before failover, enable RDP on the on-premises machine.
    - RDP should be allowed in the **Windows Firewall** -&gt; **Allowed apps and features** for **Domain and Private** networks.
    - Check that the operating system's SAN policy is set to **OnlineAll**. [Learn more](https://support.microsoft.com/kb/3031135).
- There should be no Windows updates pending on the VM when you trigger a failover. If there are, you won't be able to sign in to the virtual machine until the update completes.
- On the Windows Azure VM after failover, check **Boot diagnostics** to view a screenshot of the VM. If you can't connect, check that the VM is running and review these [troubleshooting tips](https://social.technet.microsoft.com/wiki/contents/articles/31666.troubleshooting-remote-desktop-connection-after-failover-using-asr.aspx).

To connect to Linux VMs using SSH after failover, do the following:

- On the on-premises machine before failover, check that the Secure Shell service is set to start automatically on system boot.
- Check that firewall rules allow an SSH connection.
- On the Azure VM after failover, allow incoming connections to the SSH port for the network security group rules on the failed over VM, and for the Azure subnet to which it's connected.
- [Add a public IP address](site-recovery-monitor-and-troubleshoot) for the VM.
- You can check **Boot diagnostics** to view a screenshot of the VM.

## Failback requirements

If you plan to fail back to your on-premises site, you need to meet a number of [prerequisites for failback](vmware-azure-reprotect#before-you-begin). You can prepare these prerequisites now or after you fail over to Azure.