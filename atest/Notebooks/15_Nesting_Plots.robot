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
    # The notebook's callback disables the button, starts an async toggle + layout,
    # and re-enables it when that completes; a second click landing while the task
    # is pending is dropped by the notebook's own guard. Waiting only for "enabled"
    # therefore races the kernel: if the disabling update has not reached the
    # browser yet, the button is still enabled and the wait returns immediately.
    # Wait for the disabled state to arrive first, then for it to clear. The
    # elapsed time of the "Not Enabled" wait is the click-to-disabled latency.
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
