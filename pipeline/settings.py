"""Constants for the ALM deploy pipeline. Everything tenant-specific lives here."""

TENANT = "1c5afb69-a82c-4c81-b2cc-743ce7f91dac"
ADMIN_ENV_ID = "f2280ea5-6793-e664-8f21-ea3ba6a4cb5c"
ADMIN = "https://adminorg774eae27.crm17.dynamics.com"
ADMIN_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Admin"

SOLUTION = "ALMPipeline"
PUBLISHER = "almspike"  # exists in ADMIN, prefix alm

DV_API = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
SP_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
DV_KEY = "shared_commondataserviceforapps"
SP_KEY = "shared_sharepointonline"

# ADMIN connections owned by kriall076.
DV_CONN = "shared-commondataser-88f9738e"
SP_CONN = "shared-sharepointonl-a0f00819"

CONN_REFS = {
    "alm_PipelineDataverse": ("ALM Pipeline Dataverse", DV_API, DV_CONN),
    "alm_PipelineSharePoint": ("ALM Pipeline SharePoint", SP_API, SP_CONN),
}
FLOW_REFS = {
    DV_KEY: ("alm_PipelineDataverse", DV_API),
    SP_KEY: ("alm_PipelineSharePoint", SP_API),
}

# ALM-Admin lists. ALMConnections and ALMVariables IDs are filled in by Task 2.
LIST_CONFIG = "049eba5a-700e-44db-9d2b-4e95c3af51b6"
LIST_CONNECTIONS = "bc640935-9503-44de-87d1-699d65c8d351"
LIST_VARIABLES = "1ffc8ca3-1458-423b-81cb-49226b41664f"
LOG_FOLDER = "/DeploymentLogs"

# How the SharePoint connector returns Hyperlink columns from Get items.
# False: plain URL string. True: object with 'Url'. Confirmed by the first live run (Task 5).
URL_AS_OBJECT = False

C1_NAME = "ALM C1 - Deploy (parent)"
C2_NAME = "ALM C2 - Import (child)"
C3_NAME = "ALM C3 - Post-import (child)"
