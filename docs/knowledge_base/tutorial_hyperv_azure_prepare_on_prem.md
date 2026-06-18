# Prepare on-premises Hyper-V servers for disaster recovery by using Azure Site Recovery - Azure Site Recovery | Microsoft Learn

This article describes how to prepare your on-premises Hyper-V infrastructure for disaster recovery to Azure by using [Azure Site Recovery](site-recovery-overview).

This tutorial is the second in a series that shows you how to set up disaster recovery to Azure for on-premises Hyper-V virtual machines (VMs). In the first tutorial, you [set up the Azure components](tutorial-prepare-azure) that are required for Hyper-V disaster recovery to Azure.

In this tutorial, you learn how to:

- Review Hyper-V requirements.
- Review requirements if your Hyper-V hosts are managed by System Center Virtual Machine Manager.
- Prepare Virtual Machine Manager, if applicable.
- Verify internet access to Azure locations.
- Prepare VMs so that you can access them after failover to Azure.

Note

The tutorials show the simplest deployment path for a scenario. They use default options when possible, and they don't show all possible settings and paths. For more information about a scenario, see the *How-to Guides* section of the [Site Recovery documentation](./).

## Before you start

Make sure that you prepared Azure as described in the [first tutorial in this series](tutorial-prepare-azure).

## Review requirements and prerequisites

Make sure Hyper-V hosts and VMs comply with requirements.

1. [Verify](hyper-v-azure-support-matrix#on-premises-servers) on-premises server requirements.
2. [Check the requirements](hyper-v-azure-support-matrix#replicated-vms) for Hyper-V VMs you want to replicate to Azure.
3. Check Hyper-V host [networking](hyper-v-azure-support-matrix#hyper-v-network-configuration) and host and guest [storage](hyper-v-azure-support-matrix#hyper-v-host-storage) support for on-premises Hyper-V hosts.
4. Check what's supported for [Azure networking](hyper-v-azure-support-matrix#azure-vm-network-configuration-after-failover), [storage](hyper-v-azure-support-matrix#azure-storage), and [compute](hyper-v-azure-support-matrix#azure-compute-features) after failover.
5. Verify that the on-premises VMs you replicate to Azure comply with [Azure VM requirements](hyper-v-azure-support-matrix#azure-vm-requirements).

## Prepare Virtual Machine Manager (optional)

If Hyper-V hosts are managed by System Center Virtual Machine Manager, you need to prepare the on-premises Virtual Machine Manager server.

- Make sure the Virtual Machine Manager server has at least one cloud, with one or more host groups. The Hyper-V host on which VMs are running should be located in the cloud.
- Prepare the Virtual Machine Manager server for network mapping.

### Prepare Virtual Machine Manager for network mapping

If you're using Virtual Machine Manager, [network mapping](hyper-v-vmm-network-mapping) maps between on-premises Virtual Machine Manager VM networks and Azure virtual networks. Mapping ensures that Azure VMs are connected to the correct network when they're created after failover.

To prepare Virtual Machine Manager for network mapping:

1. Make sure that you have a [Virtual Machine Manager logical network](/en-us/system-center/vmm/network-logical) that's associated with the cloud in which the Hyper-V hosts are located.
2. Ensure that you have a [VM network](/en-us/system-center/vmm/network-virtual) that's linked to the logical network.
3. In Virtual Machine Manager, connect the VMs to the VM network.

## Verify internet access

For this tutorial, the simplest configuration is for the Hyper-V hosts and the Virtual Machine Manager server to have direct access to the internet without using a proxy.

1. Make sure that Hyper-V hosts and the Virtual Machine Manager server, if relevant, can access the required URLs listed in the following table.
2. If you're controlling access by IP address, make sure that:
    - IP address-based firewall rules can connect to [Azure Datacenter IP ranges](https://www.microsoft.com/download/details.aspx?id=41653) and the HTTPS port (443).
    - You allow IP address ranges for the Azure region of your subscription.

### Required URLs

| Name | Commercial URL | Government URL | Description |
| --- | --- | --- | --- |
| Microsoft Entra ID | `login.microsoftonline.com` | `login.microsoftonline.us` | Used for access control and identity management. |
| Backup | `*.backup.windowsazure.com` | `*.backup.windowsazure.us` | Used for replication data transfer and coordination. |
| Replication | `*.hypervrecoverymanager.windowsazure.com` | `*.hypervrecoverymanager.windowsazure.us` | Used for replication management operations and coordination. |
| Storage | `*.blob.core.windows.net` | `*.blob.core.usgovcloudapi.net` | Used for access to the storage account that stores replicated data. |
| Telemetry (optional) | `dc.services.visualstudio.com` | `dc.services.visualstudio.com` | Used for telemetry. |
| Time synchronization | `time.windows.com` | `time.nist.gov` | Used to check time synchronization between system and global time in all deployments. |

## Prepare to connect to Azure VMs after failover

During a failover scenario, you might want to connect to your replicated on-premises network.

To connect to Windows VMs by using Remote Desktop Protocol (RDP) after failover, allow access as follows:

1. To access VMs over the internet, enable RDP on the on-premises VM before failover. Make sure that TCP and UDP rules are added for the **Public** profile, and that RDP is allowed in **Windows Firewall** &gt; **Allowed Apps** for all profiles.
2. To access VMs over site-to-site VPN, enable RDP on the on-premises machine. RDP should be allowed in **Windows Firewall** &gt; **Allowed apps and features** for **Domain and Private** networks.

    Check that the operating system's SAN policy is set to **OnlineAll**. [Learn more](https://support.microsoft.com/kb/3031135). No Windows updates should be pending on the VM when you initiate failover. If updates are pending, you can't sign in to the VM until the update completes.
3. On the Windows Azure VM after failover, check **Boot diagnostics** to view a screenshot of the VM. If you can't connect, check that the VM is running and review these [troubleshooting tips](https://social.technet.microsoft.com/wiki/contents/articles/31666.troubleshooting-remote-desktop-connection-after-failover-using-asr.aspx).

After failover, you can access Azure VMs by using the same IP address as the replicated on-premises VM, or you can use a different IP address. [Learn more](concepts-on-premises-to-azure-networking) about setting up IP addresses for failover.