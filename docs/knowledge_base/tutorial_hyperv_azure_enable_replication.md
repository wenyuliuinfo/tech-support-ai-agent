# Set up Hyper-V disaster recovery by using Azure Site Recovery - Azure Site Recovery | Microsoft Learn

The [Azure Site Recovery](site-recovery-overview) service contributes to your disaster recovery strategy by managing and orchestrating replication, failover, and failback of on-premises machines and Azure virtual machines (VMs).

This tutorial is the third in a series that shows you how to set up on-premises Hyper-V VMs for disaster recovery to Azure. This tutorial applies to Hyper-V VMs that aren't managed by Microsoft System Center Virtual Machine Manager.

In this tutorial, you learn how to:

- Set up the source replication environment, including on-premises Site Recovery components and the target replication environment.
- Create a replication policy.
- Enable replication for a VM.

Note

We design tutorials to show the simplest deployment path for a scenario. The tutorials use default options when possible, and they don't show all possible settings and paths. For more information about a scenario, see the *How-to Guides* section of the [Site Recovery documentation](./).

## Prerequisites

This tutorial is the third in a series of tutorials. It assumes that you've already completed the tasks in the first two tutorials:

1. [Prepare Azure](tutorial-prepare-azure-for-hyperv)
2. [Prepare on-premises Hyper-V](hyper-v-prepare-on-premises-tutorial)

## Prepare the infrastructure

It's important to prepare the infrastructure before you set up disaster recovery of on-premises Hyper-V VMs to Azure.

### Deployment planning

1. In the [Azure portal](https://portal.azure.com), go to **Recovery Services vaults** and select your vault. In the preceding tutorial, you prepared the **ContosoVMVault** vault.
2. On the vault command bar, select **Enable Site Recovery**.
3. On **Site Recovery**, under the **Hyper-V machines to Azure** tile, select **Prepare infrastructure**.
4. On **Prepare infrastructure**, select the **Deployment planning** tab. For **Deployment planning completed?**, select **I will do it later**.

    Tip

    For this tutorial, you don't need to use the Deployment Planner. If you're planning a large deployment, download the Deployment Planner for Hyper-V from the link on the pane. [Learn more](hyper-v-deployment-planner-overview) about Hyper-V deployment planning.

    ![Screenshot that shows the Deployment planning pane.](media/hyper-v-azure-tutorial/deployment-planning.png)
5. Select **Next**.

### Source settings

To set up the source environment, you create a Hyper-V site. You add to the site the Hyper-V hosts that contain VMs you want to replicate. Then, you download and install the Azure Site Recovery provider and the Microsoft Azure Recovery Services (MARS) agent for Azure Site Recovery on each host, and register the Hyper-V site in the vault.

1. On **Prepare infrastructure**, on the **Source settings**tab, complete these steps:
    1. For **Are you Using System Center VMM to manage Hyper-V hosts?**, select **No**.
    2. For **Hyper-V site**, enter a name for the site. You can also use the **Add Hyper-V site** option to add a new Hyper-V site. For example, use **ContosoHyperVSite**.
    3. For **Hyper-V servers**, select **Add Hyper-V server** to add a server.

        ![Screenshot that shows the Source settings pane with links to add a Hyper-V site and servers highlighted.](media/hyper-v-azure-tutorial/source-setting.png)
    4. On **Add Server**, complete these steps:

        1. Download the installer for the Microsoft Azure Site Recovery provider.

            ![Screenshot that shows the Add server pane.](media/hyper-v-azure-tutorial/add-server.png)
        2. Download the vault registration key. You need this key to access the provider. The key is valid for five days. Learn more.
        3. Select the site you created.
2. Select **Next**.

Site Recovery checks for compatible Azure storage accounts and networks in your Azure subscription.

#### Install the provider

Install the downloaded setup file (*AzureSiteRecoveryProvider.exe*) on each Hyper-V host that you want to add to the Hyper-V site. Setup installs the Site Recovery provider and the Recovery Services agent (MARS for Azure Site Recovery) on each Hyper-V host.

1. Run the setup file.
2. In the Azure Site Recovery provider setup wizard, for **Microsoft Update**, opt in to use Microsoft Update to check for provider updates.
3. On **Installation**, accept the default installation location for the provider and agent, and then select **Install**.
4. After installation, in the Microsoft Azure Site Recovery Registration Wizard, for **Vault Settings**, select **Browse**. On **Key File**, select the vault key file that you downloaded.
5. Select the Azure Site Recovery subscription, the vault name (**ContosoVMVault**), and the Hyper-V site (**ContosoHyperVSite**) to which the Hyper-V server belongs.
6. On **Proxy Settings**, select **Connect directly to Azure Site Recovery without a proxy**.
7. On **Registration**, after the server is registered in the vault, select **Finish**.

Metadata from the Hyper-V server is retrieved by Azure Site Recovery, and the server appears in **Site Recovery Infrastructure** &gt; **Hyper-V Hosts**. This process can take up to 30 minutes.

#### Install the provider on a Hyper-V Core server

If you're running a Hyper-V Core server, download the setup file and complete these steps:

1. Extract the files from *AzureSiteRecoveryProvider.exe* to a local directory by running this command:

    `AzureSiteRecoveryProvider.exe /x:. /q`
2. Run `.\setupdr.exe /i`. Results are logged to *%Programdata%\ASRLogs\DRASetupWizard.log*.
3. Register the server by running this command:

    ```cmd
    cd "C:\Program Files\Microsoft Azure Site Recovery Provider"
    "C:\Program Files\Microsoft Azure Site Recovery Provider\DRConfigurator.exe" /r /Friendlyname "FriendlyName of the Server" /Credentials "path to where the credential file is saved"
    ```

### Target settings

Select and verify target resources:

1. On **Prepare infrastructure**, on the **Target settings** tab, complete these steps:

    1. For **Subscription**, select the subscription and the resource group (**ContosoRG**) in which the Azure VMs will be created after failover.
    2. For **Post-failover deployment model**, select the **Resource Manager** deployment model.

    ![Screenshot that shows the Target settings pane.](media/hyper-v-azure-tutorial/target-settings.png)
2. Select **Next**.

### Replication policy

On **Prepare infrastructure**, on the **Replication policy** tab, complete these steps:

1. For **Replication policy**, select the replication policy.

    ![Screenshot that shows the Replication policy tab, with the Create new policy and associate link highlighted.](media/hyper-v-azure-tutorial/replication-policy.png)

    If you don't have a replication policy, select the **Create new policy and associate** link to create a new policy. On the **Create and associate policy** pane, complete these steps:

    1. For **Name**, enter a name for the policy. For example, use **ContosoReplicationPolicy**.
    2. For **Source type**, select the **ContosoHyperVSite** site.
    3. For **Target type**, verify the target (Azure), the vault subscription, and the Resource Manager deployment mode.
    4. For **Copy frequency**, select **5 Minutes**.
    5. For **Recovery point retention in hours**, select **2**.
    6. For **App-consistent snapshot frequency**, select **1**.
    7. For **Initial replication start time**, select **Immediately**.
    8. Select **OK** to create the policy. When you create a new policy, it's automatically associated with the specified Hyper-V site.

    ![Screenshot that shows Create and associate policy pane and options.](media/hyper-v-azure-tutorial/create-policy.png)
2. Select **Next**.
3. On the **Review** tab, review your selections, and then select **Create**.

You can track progress in your Azure portal notifications. When the job finishes, the initial replication is complete, and the VM is ready for failover.

## Enable replication

Note

Hyper-V to Azure disaster recovery doesn't support South Central India and North East US 5 as target regions.

1. In the [Azure portal](https://portal.azure.com), go to **Recovery Services vaults** and select the vault.
2. On the vault command bar, select **Enable Site Recovery**.
3. On **Site Recovery**, under the **Hyper-V machines to Azure** tile, select **Enable replication**.
4. On **Enable replication**, on the **Source environment** tab, select a source location, and then select **Next**.

    ![Screenshot that shows the source environment pane.](media/hyper-v-azure-tutorial/enable-replication-source.png)
5. On the **Target environment** tab, complete these steps:

    1. For **Subscription**, enter or select the subscription.
    2. For **Post-failover resource group**, select the resource group name to fail over to.
    3. For **Post-failover deployment model**, select **Resource Manager**.
    4. For **Storage account**, enter or select the storage account.

    ![Screenshot that shows the target environment pane.](media/hyper-v-azure-tutorial/enable-replication-target.png)
6. Select **Next**.
7. On the **Virtual machine selection** tab, select the VM to replicate, and then select **Next**.
8. On the **Replication settings** tab, select and verify the disk details, and then select **Next**.

    ![Screenshot that shows the replication settings pane.](media/hyper-v-azure-tutorial/enable-replication-settings.png)
9. On the **Replication policy** tab, verify that the correct replication policy is selected, and then select **Next**.

    ![Screenshot that shows the replication policy pane.](media/hyper-v-azure-tutorial/enable-replication-policy.png)
10. On the **Review** tab, review your selections, and then select **Enable Replication**.

## Unmanaged disk deprecation

Azure [retires unmanaged disks](/en-us/azure/virtual-machines/unmanaged-disks-deprecation) and you will no longer be able to start IaaS VMs using unmanaged disks. Any running or allocated VMs with unmanaged disks are stopped and deallocated.

This change impacts Azure Site Recovery (ASR) operations, especially for failover scenarios. If your target disks are configured as unmanaged, failovers fail after unmanaged disks deprecation as ASR attempts to create unmanaged VMs that are no longer supported.

### What’s changing for Hyper-V-to-Azure (H2A)

#### New ASR Enablement

All new ASR configurations for H2A from Azure portal create target disks as Managed disks. When you enable replication of a Hyper-V VM from Azure portal, the target disk is always a Managed disk, regardless of whether the replica is a blob or a Managed disk.

On the Azure portal, during enable replication, **Replica Storage Account** setting is selected as **Managed Disk** by default. In that case, both your replica and target are of Managed disk type. You can also select **Storage Account** from the dropdown menu, where your replica is unmanaged disk type, and target disk is Managed disk type.

![Screenshot of Enable replication page.](media/hyper-v-azure-tutorial/enable-replication.png)

### Existing ASR Configurations

If you have an existing H2A configuration with unmanaged disks as the target, we recommended you update your protection settings to use Managed disks as the target to ensure failover after the deprecation of unmanaged disks.

To do this, navigate to **Protected Items** page &gt; **Compute and Network** and change **Use managed disks** from **No** to **Yes**.

![Screenshot of Compute and Network page.](media/hyper-v-azure-tutorial/compute-network.png)

Note

Changing **Use managed disks** from **No** to **Yes** means disks created after failover are *Managed*, with their type (Standard SSD LRS or Premium SSD LRS) based on the replica's storage account. Standard accounts result in Standard SSD LRS disks; Premium accounts yield Premium SSD LRS disks.

### Failback

Failback from Azure to on-premises is possible when the target disk is Managed, regardless of whether the replica uses unmanaged or managed disks. MARS (Recovery Services agent) version 2.0.9214 or higher is required for failback.

### Update the Microsoft Azure Recovery Services (MARS) Agent

To update the MARS Agent, follow these steps:

1. [Download the latest version of the MARS agent](https://aka.ms/downloadmarsagent).
2. Double-click the downloaded file to run the installer.
3. If the MARS agent is already installed, you are prompted with a dialog box if you want to update the MARS agent. Select **Yes**.

Note

Don't re-register the server, as it is already associated with the vault.

This process updates the existing MARS agent to the latest available version without requiring re-registration.