*** Settings ***
Documentation     Introduction
Suite Setup       Setup Suite For Screenshots    notebook-introduction
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot

*** Variables ***
${INTRODUCTION}    00_Introduction
${SIMPLE}         simple.json
@{SUPPORT}        ${IPYELK_EXAMPLES}${/}${SIMPLE}

*** Test Cases ***
Introduction
    Open IPyElk Notebook    ${INTRODUCTION}    support files=@{SUPPORT}
    Restart and Run All
    Wait For All Cells To Run    60s
    Capture All Code Cells
    Page Should Not Contain Contain Standard Errors
    Capture Page Screenshot    99-fin.png
    [Teardown]    Clean up after Working with Files    ${INTRODUCTION}.ipynb    ${SIMPLE}
