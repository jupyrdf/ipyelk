*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}${NESTING PLOTS}


*** Test Cases ***
15_Nesting_Plots
    Example Should Restart-and-Run-All    ${NESTING PLOTS}
    Scroll To Notebook Bottom
    ${sel} =    Set Variable    css:[title="expand and center"]
    Click Element    ${sel}
    Sleep    2s
    Capture Page Screenshot    11-expanded.png
    Click Element    ${sel}
    Sleep    2s
    Capture Page Screenshot    12-collapsed.png
