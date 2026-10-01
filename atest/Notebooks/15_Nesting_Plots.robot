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
    Scroll To Last Cell
    BQPlot Figure Count Should Be    ${0}
    ${sel} =    Set Variable    css:[title="expand and center"]
    # the button is disabled while the toggle runs: wait for disabled, then
    # enabled, or the wait can return before the kernel has disabled it
    Click Element    ${sel}
    Wait Until Element Is Not Enabled    ${sel}    timeout=10s
    Wait Until Element Is Enabled    ${sel}    timeout=30s
    Capture Page Screenshot    11-expanded.png
    BQPlot Figure Count Should Be    ${4}
    Click Element    ${sel}
    Wait Until Element Is Not Enabled    ${sel}    timeout=10s
    Wait Until Element Is Enabled    ${sel}    timeout=30s
    Capture Page Screenshot    12-collapsed.png
    BQPlot Figure Count Should Be    ${0}
