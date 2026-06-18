# Set up failover of Hyper-V VMs to Azure in Azure Site Recovery - Azure Site Recovery | Microsoft Learn

This tutorial describes how to fail over Hyper-V VMs to Azure with [Azure Site Recovery](site-recovery-overview). After you've failed over, you fail back to your on-premises site when it's available. In this tutorial, you learn how to:

- Verify the Hyper-V VM properties to check conform with Azure requirements.
- Fail over specific VMs to Azure.

This tutorial is the fifth tutorial in a series. It assumes that you have already completed the tasks in the previous tutorials.

1. [Prepare Azure](tutorial-prepare-azure)
2. [Prepare on-premises Hyper-V](hyper-v-prepare-on-premises-tutorial)
3. Set up disaster recovery for [Hyper-V VMs](hyper-v-azure-tutorial), or for [Hyper-V VMs managed in System Center VMM clouds](hyper-v-vmm-azure-tutorial)
4. [Run a disaster recovery drill](tutorial-dr-drill-azure)

[Learn about](failover-failback-overview#types-of-failover) different types of failover. If you want to fail over multiple VMs in a recovery plan, review [this article](site-recovery-failover).

## Prepare for failover

Make sure there are no snapshots on the VM, and that the on-premises VM is turned off during failback. It helps ensure data consistency during replication. Don't turn on on-premises VM during failback.

Failover and failback have three stages:

1. **Failover to Azure**: Failover Hyper-V VMs from the on-premises site to Azure.
2. **Failback to on-premises**: Failover Azure VMs to your on-premises site when the on-premises site is available. It starts synchronizing data from Azure to on-premises and on completion, it brings up the VMs on on-premises.
3. **Reverse replicate on-premises VMs**: After failed back to on-premises, reverse replicate the on-premises VMs to start replicating them to Azure.

## Verify VM properties

Before failover verify the VM properties, and make sure that the VM meets with [Azure requirements](hyper-v-azure-support-matrix#replicated-vms).

In **Protected Items**, click **Replicated Items** &gt; VM.

1. In the **Replicated item** pane, there's a summary of VM information, health status, and the latest available recovery points. Click **Properties** to view more details.
2. In **Compute and Network**, you can modify the Azure name, resource group, target size, [availability set](/en-us/azure/virtual-machines/windows/tutorial-availability-sets), and managed disk settings.
3. You can view and modify network settings, including the network/subnet in which the Azure VM will be located after failover, and the IP address that will be assigned to it.
4. In **Disks**, you can see information about the operating system and data disks on the VM.

## Fail over to Azure

1. In **Settings** &gt; **Replicated items**, click the VM &gt; **Failover**.
2. In **Failover**, select the **Latest** recovery point.
3. Select **Shut down machine before beginning failover**. Site Recovery attempts to do a shutdown of source VMs before triggering the failover. Failover continues even if shutdown fails. You can follow the failover progress on the **Jobs** page.
4. After you verify the failover, click **Commit**. It deletes all the available recovery points.

Warning

**Don't cancel a failover in progress**: If you cancel in progress, failover stops, but the VM won't replicate again.

## Connect to failed-over VM

1. If you want to connect to Azure VMs after failover by using Remote Desktop Protocol (RDP) and Secure Shell (SSH), [verify that the requirements have been met](failover-failback-overview#connect-to-azure-after-failover).
2. After failover, go to the VM and validate by [connecting](/en-us/azure/virtual-machines/windows/connect-logon) to it.
3. Use **Change recovery point** if you want to use a different recovery point after failover. After you commit the failover in the next step, this option will no longer be available.
4. After validation, select **Commit** to finalize the recovery point of the VM after failover.
5. After you commit, all the other available recovery points are deleted. This step completes the failover.

Tip

If you encounter any connectivity issues after failover, follow the [troubleshooting guide](site-recovery-failover-to-azure-troubleshoot).