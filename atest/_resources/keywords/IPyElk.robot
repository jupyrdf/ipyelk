*** Settings ***
Resource          ../variables/IPyElk.robot

*** Keywords ***
Open IPyElk Notebook
    [Arguments]    ${notebook}    ${path}=${IPYELK_EXAMPLES}    ${support files}=${None}
    Set Tags    notebook:${notebook}
    ${full path} =    Normalize Path    ${path}${/}${notebook}.ipynb
    File Should Exist    ${full path}
    Run Keyword If    ${support files}    Copy Support Files    ${support files}
    Open File    ${full path}    ${MENU NOTEBOOK}
    Wait Until Page Contains Element    ${JLAB XP KERNEL IDLE}    timeout=30s
    Ensure Sidebar Is Closed
    Capture Page Screenshot    01-loaded.png

Copy Support Files
    [Arguments]    ${files}
    FOR    ${file}    IN    @{files}
        ${parent}    ${name} =    Split Path    ${file}
        Copy File    ${file}    ${OUTPUT DIR}${/}home${/}${name}
    END

Example Should Restart-and-Run-All
    [Arguments]    ${example}
    Set Screenshot Directory    ${SCREENS}${/}${example.lower()}
    Open IPyElk Notebook    ${example}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png

Clean up after Example
    [Arguments]    ${example}
    Clean up after Working with Files    ${example}.ipynb    @{CLEANUP}
