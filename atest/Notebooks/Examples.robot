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
${LABEL PLACEMENT}    100_node_label_placement
${TEXT SIZER}     101_text_sizer
${SIMPLE}         simple.json
${FLAT}           flat_graph.json
${HIER_PORTS}     hier_ports.json
${HIER_TREE}      hier_tree.json
@{SUPPORT}        ${IPYELK_EXAMPLES}${/}${SIMPLE}    ${IPYELK_EXAMPLES}${/}${FLAT}
...               ${IPYELK_EXAMPLES}${/}${HIER_PORTS}    ${IPYELK_EXAMPLES}${/}${HIER_TREE}
@{CLEANUP}        ${SIMPLE}    ${FLAT}    ${HIER_PORTS}    ${HIER_TREE}
${SCREENS}        ${SCREENS ROOT}${/}notebooks

*** Test Cases ***
#    TODO:
#    - as these get filled in, they should be migrated to standalone `.robot` files
#    in this directory.
#    - common keywords, variables should move into `../_resources/*/IPyElk.robot`
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

100_node_label_placement
    Set Screenshot Directory    ${SCREENS}${/}100-node-label-placement
    Open IPyElk Notebook    ${LABEL PLACEMENT}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${LABEL PLACEMENT}.ipynb    @{CLEANUP}

101_text_sizer
    Set Screenshot Directory    ${SCREENS}${/}100-node-label-placement
    Open IPyElk Notebook    ${TEXT SIZER}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${TEXT SIZER}.ipynb    @{CLEANUP}