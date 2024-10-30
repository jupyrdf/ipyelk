*** Settings ***
Library     Collections
Library     XML    WITH NAME    XML
Library     OperatingSystem
Resource    ../variables/IPyElk.robot
Resource    Lab.robot


*** Keywords ***
Get All IPyElk Example File Names
    ${file names} =    List Files in Directory    ${IPYELK_EXAMPLES}
    RETURN    ${file names}

Get All IPyElk Example Paths
    ${file names} =    Get All IPyElk Example File Names
    ${paths} =    Create List
    FOR    ${file}    IN    @{file names}
        Append To List    ${paths}    ${IPYELK_EXAMPLES}${/}${file}
    END
    RETURN    ${paths}

Open IPyElk Notebook
    [Arguments]    ${notebook}    ${path}=${IPYELK_EXAMPLES}
    Set Tags    notebook:${notebook}
    ${full path} =    Normalize Path    ${path}${/}${notebook}.ipynb
    File Should Exist    ${full path}
    ${files} =    Get All IPyElk Example Paths
    Copy Support Files    ${files}
    Open File    ${full path}    ${MENU NOTEBOOK}
    Wait Until Element Is Visible    ${JLAB XP KERNEL IDLE}    timeout=30s
    Lab Command    Clear Outputs of All Cells
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
    # nothing should be on the page, yet
    Elk Counts Should Be    # all 0
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture Each Cell Output    09-
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    10-ran-all-without-stderr.png

Capture Each Cell Output
    [Arguments]    ${prefix}=${EMPTY}
    ${cell_count_} =    Get Cell Count
    FOR    ${i}    IN RANGE    ${cell_count}
        ${n} =    Set Variable    ${i.__add__(1)}
        Scroll To Cell    ${n}
        ${outputs} =    Get WebElements    ${JLAB CSS CELL}:nth-child(${n}) ${JLAB CSS OUTPUT AREA}
        IF    ${outputs.__len__()}
            Run Keyword And Ignore Error
            ...    Capture Element Screenshot    ${outputs[0]}    ${prefix}${n}-output.png
        END
    END
    Scroll To First Cell

Clean up after IPyElk Example
    ${files} =    Get All IPyElk Example File Names
    Capture Page Screenshot    99-fin.png
    Clean up after Working with Files    @{files}

Exported SVG should be valid XML
    [Arguments]    ${file}
    ${path} =    Set Variable    ${OUTPUT DIR}${/}home${/}${file}
    Wait Until Created    ${path}
    RETURN    XML.Parse XML    ${file}

Custom Elk Selectors Should Exist
    [Arguments]    @{selectors}
    FOR    ${selector}    IN    @{selectors}
        Page Should Contain Element    ${selector}
    END

Elk Counts Should Be
    [Arguments]
    ...    ${nodes}=${0}
    ...    ${edges}=${0}
    ...    ${labels}=${0}
    ...    ${ports}=${0}
    ...    ${prefix}=${EMPTY}
    ...    ${n}=${1}
    ...    ${screen}=20-counted.png
    Wait Until Keyword Succeeds
    ...    5x
    ...    1s
    ...    Elk Counts Should Really Be
    ...    nodes=${nodes}
    ...    edges=${edges}
    ...    labels=${labels}
    ...    ports=${ports}
    ...    prefix=${prefix}
    ...    n=${n}
    ...    screen=${screen}

Elk Counts Should Really Be
    [Arguments]
    ...    ${nodes}=${0}
    ...    ${edges}=${0}
    ...    ${labels}=${0}
    ...    ${ports}=${0}
    ...    ${prefix}=${EMPTY}
    ...    ${n}=${1}
    ...    ${screen}=20-counted.png
    ${found nodes} =    Get Elk Node Count    prefix=${prefix}
    ${found edges} =    Get Elk Edge Count    prefix=${prefix}
    ${found labels} =    Get Elk Label Count    prefix=${prefix}
    ${found ports} =    Get Elk Port Count    prefix=${prefix}
    Capture Page Screenshot    ${screen}
    Should Be Equal As Strings
    ...    nodes:${found nodes} edges:${found edges} labels:${found labels} ports:${found ports}
    ...    nodes:${nodes.__mul__(${n})} edges:${edges.__mul__(${n})} labels:${labels.__mul__(${n})} ports:${ports.__mul__(${n})}

Create Linked Elk Output View
    Wait Until Element Is Visible    css:${CSS ELK VIEW}
    Click Element    css:${CSS ELK VIEW}
    Open Context Menu    css:${CSS ELK VIEW}
    Wait Until Keyword Succeeds    3x    0.5s    Mouse Over    css:${JLAB CSS CREATE OUTPUT}
    Press Keys    None    RETURN
    Wait Until Element Is Visible    css:${JLAB CSS LINKED OUTPUT} ${CSS ELK VIEW} ${CSS ELK NODE}

Linked Elk Output Counts Should Be
    [Arguments]
    ...    ${nodes}=${0}
    ...    ${edges}=${0}
    ...    ${labels}=${0}
    ...    ${ports}=${0}
    ...    ${n}=${1}
    ...    ${screen}=30-linked.png
    ...    ${open}=${TRUE}
    IF    ${open}    Create Linked Elk Output View
    Elk Counts Should Be    nodes=${nodes}    edges=${edges}    labels=${labels}    ports=${ports}    n=${n}
    ...    prefix=${JLAB CSS LINKED OUTPUT}${SPACE}    screen=${screen}

Get Elk Node Count
    [Arguments]    ${prefix}=${EMPTY}    ${suffix}=${EMPTY}
    ${nodes} =    SeleniumLibrary.Get Element Count    css:${prefix}${CSS ELK NODE}${suffix}
    RETURN    ${nodes}

Get Elk Edge Count
    [Arguments]    ${prefix}=${EMPTY}    ${suffix}=${EMPTY}
    ${edges} =    SeleniumLibrary.Get Element Count    css:${prefix}${CSS ELK EDGE}${suffix}
    RETURN    ${edges}

Get Elk Label Count
    [Arguments]    ${prefix}=${EMPTY}    ${suffix}=${EMPTY}
    ${labels} =    SeleniumLibrary.Get Element Count    css:${prefix}${CSS ELK LABEL}${suffix}
    RETURN    ${labels}

Get Elk Port Count
    [Arguments]    ${prefix}=${EMPTY}    ${suffix}=${EMPTY}
    ${ports} =    SeleniumLibrary.Get Element Count    css:${prefix}${CSS ELK PORT}${suffix}
    RETURN    ${ports}

Click Elk Tool
    [Arguments]    ${label}    ${index}=${1}
    ${elkSelector} =    Set Variable    xpath:(//div[contains(@class,"jp-ElkApp")])[${index}]
    ${buttonSelector} =    Set Variable    ${elkSelector}//button[contains(.,"${label}")]
    ${elkApp} =    Get WebElement    ${elkSelector}
    Log    ${elkApp}
    Mouse Over    ${elkApp}
    Click Element    ${elkApp}
    Sleep    0.3s
    ${tool} =    Get WebElement    ${buttonSelector}
    Log    ${tool}
    Wait Until Element Is Visible    ${tool}
    Click Element    ${tool}
    Sleep    0.3s
    Click Element    ${JLAB CSS NOTEBOOK}
    Sleep    0.3s

BQPlot Figure Count Should Be
    [Arguments]    ${expected}=${0}
    ${bq} =    Get WebElements    css:.bqplot
    Should Be Equal As Integers    ${bq.__len__()}    ${expected}
