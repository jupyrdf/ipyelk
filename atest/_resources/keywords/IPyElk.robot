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
