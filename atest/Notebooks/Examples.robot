*** Settings ***
Suite Setup       Setup Suite For Screenshots    notebooks
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot

*** Variables ***
${INTRODUCTION}    00_Introduction
${LINKING}        01_Linking
${TRANSFORMER}    02_Transformer
${APP}            03_App
${INTERACTIVE}    04_Interactive
${SIMPLE}         simple.json
${FLAT}           flat_graph.json
${HIER_PORTS}     hier_ports.json
${HIER_TREE}      hier_tree.json
@{SUPPORT}        ${IPYELK_EXAMPLES}${/}${SIMPLE}    ${IPYELK_EXAMPLES}${/}${FLAT}
...               ${IPYELK_EXAMPLES}${/}${HIER_PORTS}    ${IPYELK_EXAMPLES}${/}${HIER_TREE}
@{CLEANUP}        ${SIMPLE}    ${FLAT}    ${HIER_PORTS}    ${HIER_TREE}
${SCREENS}        ${SCREENS ROOT}${/}notebooks

*** Test Cases ***
00_Introduction
    Set Screenshot Directory    ${SCREENS}${/}00-introduction
    Open IPyElk Notebook    ${INTRODUCTION}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${INTRODUCTION}.ipynb    @{CLEANUP}

01_Linking
    Set Screenshot Directory    ${SCREENS}${/}01-linking
    Open IPyElk Notebook    ${LINKING}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${LINKING}.ipynb    @{CLEANUP}

02_Transformer
    Set Screenshot Directory    ${SCREENS}${/}02-transformer
    Open IPyElk Notebook    ${TRANSFORMER}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${TRANSFORMER}.ipynb    @{CLEANUP}

03_App
    Set Screenshot Directory    ${SCREENS}${/}03-app
    Open IPyElk Notebook    ${APP}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${APP}.ipynb    @{CLEANUP}

04_Interactive
    Set Screenshot Directory    ${SCREENS}${/}04-interactive
    Open IPyElk Notebook    ${APP}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${APP}.ipynb    @{CLEANUP}
