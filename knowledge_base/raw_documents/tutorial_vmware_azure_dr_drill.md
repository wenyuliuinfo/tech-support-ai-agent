# Run a disaster recovery drill to Azure with Azure Site Recovery - Azure Site Recovery | Microsoft Learn

This article describes how to run a disaster recovery drill for an on-premises machine to Azure by using the [Azure Site Recovery](site-recovery-overview) service. A drill validates your replication strategy without data loss.

This tutorial is the fourth in a series that shows you how to set up disaster recovery to Azure for on-premises machines.

In this tutorial, you learn how to:

- Set up an isolated network for the test failover
- Prepare to connect to the Azure VM after failover
- Run a test failover for a single machine.

Note

Tutorials show you the simplest deployment path for a scenario. They use default options where possible, and don't show all possible settings and paths. If you want to learn about the disaster recovery drill steps in more detail, [review this article](site-recovery-test-failover-to-azure).

## Before you start

Complete the previous tutorials:

1. Make sure you [set up Azure](tutorial-prepare-azure) for on-premises disaster recovery of VMware VMs, Hyper-V VMs, and physical machines to Azure.
2. Prepare your on-premises [VMware](vmware-azure-tutorial-prepare-on-premises) or [Hyper-V](hyper-v-prepare-on-premises-tutorial) environment for disaster recovery. If you're setting up disaster recovery for physical servers, review the [support matrix](vmware-physical-secondary-support-matrix).
3. Set up disaster recovery for [VMware VMs](vmware-azure-tutorial), [Hyper-V VMs](hyper-v-azure-tutorial), or [physical machines](physical-azure-disaster-recovery).

## Verify VM properties

Before you run a test failover, verify the VM properties, and make sure that the [Hyper-V VM](hyper-v-azure-support-matrix#replicated-vms), or [VMware VM](vmware-physical-azure-support-matrix#replicated-machines) complies with Azure requirements.

1. In **Protected Items**, select **Replicated Items** and the VM.
2. In the **Replicated item** pane, review the summary of VM information, health status, and the latest available recovery points. Select **Properties** to view more details.
3. In **Compute and Network**, modify the Azure name, resource group, target size, availability set, and managed disk settings.
4. View and modify network settings, including the network and subnet in which the Azure VM will be located after failover, and the IP address that you assign to it.
5. In **Disks**, see information about the operating system and data disks on the VM.

## Create a network for test failover

For test failover, choose a network that's isolated from the production recovery site network. Specify this network in the **Compute and Network** settings for each VM. By default, when you create an Azure virtual network, it is isolated from other networks. The test network should mimic your production network:

- The test network should have the same number of subnets as your production network. Subnets should have the same names.
- The test network should use the same IP address range.
- Update the DNS of the test network with the IP address specified for the DNS VM in **Compute and Network** settings. For more details, see [test failover considerations for Active Directory](site-recovery-active-directory#test-failover-considerations).

## Run a test failover for a single VM

When you run a test failover, the following happens:

1. A prerequisites check runs to make sure all of the conditions required for failover are in place.
2. Failover processes the data, so that an Azure VM can be created. If you select the latest recovery point, a recovery point is created from the data.
3. An Azure VM is created by using the data processed in the previous step.

Run the test failover as follows:

1. In **Settings** &gt; **Replicated Items**, select the VM, and then select **+Test Failover**.
2. Select the **Latest processed** recovery point for this tutorial. This option fails over the VM to the latest available point in time. The time stamp is shown. By using this option, no time is spent processing data, so it provides a low RTO (recovery time objective).
3. In **Test Failover**, select the target Azure network to which Azure VMs connect after failover occurs.
4. Select **OK** to begin the failover. You can track progress by selecting the VM to open its properties. Or you can select the **Test Failover** job in vault name &gt; **Settings** &gt; **Jobs** &gt; **Site Recovery jobs**.
5. After the failover finishes, the replica Azure VM appears in the Azure portal &gt; **Virtual Machines**. Check that the VM is the appropriate size, that it's connected to the right network, and that it's running.
6. You should now be able to connect to the replicated VM in Azure.
7. To delete Azure VMs created during the test failover, select **Cleanup test failover** on the VM. In **Notes**, record and save any observations associated with the test failover.

In some scenarios, failover requires additional processing that takes around eight to ten minutes to complete. You might notice longer test failover times for VMware Linux machines, VMware VMs that don't have the DHCP service enabled, and VMware VMs that don't have the following boot drivers: storvsc, vmbus, storflt, intelide, atapi.

## Connect after failover

To connect to Azure VMs by using RDP or SSH after failover, [prepare to connect](site-recovery-test-failover-to-azure#prepare-to-connect-to-azure-vms-after-failover). If you encounter any connectivity problems after failover, follow the [troubleshooting](site-recovery-failover-to-azure-troubleshoot) guide.