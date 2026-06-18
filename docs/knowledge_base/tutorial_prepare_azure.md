# Prepare Azure for on-premises disaster recovery with Azure Site Recovery - Azure Site Recovery | Microsoft Learn

This article describes how to prepare Azure resources and components so that you can set up disaster recovery of on-premises VMware VMs, Hyper-V VMs, or Windows/Linux physical servers to Azure, using the [Azure Site Recovery](site-recovery-overview) service.

This article is the first tutorial in a series that shows you how to set up disaster recovery for on-premises VMs.

In this tutorial, you learn how to:

- Verify that the Azure account has replication permissions.
- Create a Recovery Services vault. A vault holds metadata and configuration information for VMs, and other replication components.
- Set up an Azure virtual network (VNet). When Azure VMs are created after failover, they're joined to this network.

Note

Tutorials show you the simplest deployment path for a scenario. They use default options where possible, and don't show all possible settings and paths. For detailed instructions, review the article in the *How To* section of the Site Recovery Table of Contents.

## Sign in to Azure

If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/pricing/free-trial/) before you begin. Then sign in to the [Azure portal](https://portal.azure.com).

## Prerequisites

**Before you start, do the following:**

- Review the architecture for [VMware](vmware-azure-architecture), [Hyper-V](hyper-v-azure-architecture), and [physical server](physical-azure-architecture) disaster recovery.
- Read common questions for [VMware](vmware-azure-common-questions) and [Hyper-V](hyper-v-azure-common-questions)

### Verify account permissions

If you just created your free Azure account, you're the administrator of your subscription and you have the permissions you need. If you're not the subscription administrator, work with the administrator to assign the permissions you need. To enable replication for a new virtual machine, you must have permission to:

- Create a VM in the selected resource group.
- Create a VM in the selected virtual network.
- Write to an Azure storage account.
- Write to an Azure managed disk.

To complete these tasks your account should be assigned the Virtual Machine Contributor built-in role. In addition, to manage Site Recovery operations in a vault, your account should be assigned the Site Recovery Contributor built-in role.

## Create a recovery services vault

1. In the [Azure portal](https://portal.azure.com), select **Create a resource**.
2. Search the Azure Marketplace for *Recovery Services*.
3. Select **Backup and Site Recovery** from the search results, and in the Backup and Site Recovery page, click **Create**.
4. In the **Create Recovery Services vault** page, under the **Basics** &gt; **Project details** section, do the following:

    1. Under **Subscription**. We're using **Contoso Subscription**.
    2. In **Resource group**, select an existing resource group or create a new one. For example, **contosoRG**.
5. In the **Create Recovery Services vault** page, under **Basics** &gt; **Instance details** section, do the following:

    1. In **Vault name**, enter a friendly name to identify the vault. For example, **ContosoVMVault**.
    2. In **Region**, select the region where the vault should be located. For example, **(Europe) West Europe**.
    3. Select **Review + create** &gt; **Create** to create the recovery vault. ![Screenshot of the Create Recovery Services vault page.](media/tutorial-prepare-azure/new-vault-settings.png)

The new vault will now be listed in **Dashboard** &gt; **All resources**, and on the main **Recovery Services vaults** page.

## Set up an Azure network

On-premises machines are replicated to Azure managed disks. When failover occurs, Azure VMs are created from these managed disks, and joined to the Azure network you specify in this procedure.

1. In the [Azure portal](https://portal.azure.com), select **Create a resource**.
2. Under **Categories**, select **Networking** &gt; **Virtual network**.
3. In **Create virtual network** page, under the **Basics** tab, do the following:

    1. In **Subscription**, select the subscription in which to create the network.
    2. In **Resource group**, select the resource group in which to create the network. For this tutorial, use the existing resource group **contosoRG**.
    3. In **Virtual network name**, enter a network name. The name must be unique within the Azure resource group. For example, **ContosoASRnet**.
    4. In **Region**, choose **(Europe) West Europe**. The network must be in the same region as the Recovery Services vault.

    ![Screenshot of the Create virtual network options.](media/tutorial-prepare-azure/create-network.png)
4. In **Create virtual network** &gt; **IP addresses** tab, do the following:

    1. As there's no subnet for this network, you will first delete the pre-existing address range. To do so, select the ellipsis (...), under available IP address range, then select **Delete address space**.

        ![Screenshot of the delete address space.](media/tutorial-prepare-azure/delete-ip-address.png)
    2. After deleting the pre-existing address range, select **Add an IP address space**.

        ![Screenshot of the adding IP.](media/tutorial-prepare-azure/add-ip-address-space.png)
    3. In **Starting address** enter **10.0.0.0**
    4. Under **Address space size**, select **/24 (256 addresses)**.
    5. Select **Add**.

        ![Screenshot of the add virtual network options.](media/tutorial-prepare-azure/homepage-ip-address.png)
5. Select **Review + create** &gt; **Create** to create a new virtual network.

The virtual network takes a few seconds to create. After it's created, you'll see it in the Azure portal dashboard.