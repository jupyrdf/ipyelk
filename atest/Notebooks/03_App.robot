*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}03_App


*** Test Cases ***
03_App
    [Tags]    data:hier_tree.json    data:hier_ports.json    foo:bar
    Example Should Restart-and-Run-All    ${APP}
    Scroll To Notebook Cell    6
    Click Elk Tool    Center    1
    Scroll To Notebook Cell    9
    Click Elk Tool    Center    2
    Scroll To Notebook Cell    12
    Click Elk Tool    Center    3
    Scroll To Notebook Cell    15
    Click Elk Tool    Center    4
    Elk Counts Should Be    n=${4}    &{HIER COUNTS}
    Scroll To Notebook Cell    6
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}
