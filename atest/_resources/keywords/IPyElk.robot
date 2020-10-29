*** Settings ***
Library           Collections
Resource          ../variables/IPyElk.robot

*** Keywords ***
Get All IPyElk Example File Names
    ${file names} =    List Files in Directory    ${IPYELK_EXAMPLES}
    [Return]    ${file names}

Get All IPyElk Example Paths
    ${file names} =    Get All IPyElk Example File Names
    ${paths} =    Create List
    FOR    ${file}    IN    @{file names}
        Append To List    ${paths}    ${IPYELK_EXAMPLES}${/}${file}
    END
    [Return]    ${paths}

Open IPyElk Notebook
    [Arguments]    ${notebook}    ${path}=${IPYELK_EXAMPLES}
    Set Tags    notebook:${notebook}
    ${full path} =    Normalize Path    ${path}${/}${notebook}.ipynb
    File Should Exist    ${full path}
    ${files} =    Get All IPyElk Example Paths
    Copy Support Files    ${files}
    Open File    ${full path}    ${MENU NOTEBOOK}
    Wait Until Page Contains Element    ${JLAB XP KERNEL IDLE}    timeout=30s
    Ensure Sidebar Is Closed
    Capture Page Screenshot    01-loaded.png

Copy Support Files
    [Arguments]    ${paths}
    FOR    ${path}    IN    @{paths}
        ${parent}    ${name} =    Split Path    ${path}
        Copy File    ${path}    ${OUTPUT DIR}${/}home${/}${name}
    END

Example Should Restart-and-Run-All
    [Arguments]    ${example}
    Set Screenshot Directory    ${SCREENS}${/}${example.lower()}
    Open IPyElk Notebook    ${example}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png

Clean up after Example
    [Arguments]    ${example}
    ${files} =    Get All IPyElk Example File Names
    Clean up after Working with Files    @{files}
