*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}01_Linking


*** Test Cases ***
01_Linking
    [Tags]    data:simple.json    tool:fit
    Example Should Restart-and-Run-All    ${LINKING}
    ${counts} =    Create Dictionary    n=${2}    &{SIMPLE COUNTS}
    Click Elk Tool    Fit
    Click Elk Tool    Fit    1
    Elk Counts Should Be    &{counts}
    Create Linked Elk Output View
    Click Elk Tool    Fit    2
    Click Elk Tool    Fit    3
    Sleep    1s
    Linked Elk Output Counts Should Be    &{counts}    open=${FALSE}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}
