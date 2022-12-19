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
    Elk Counts Should Be    n=${4}    &{HIER COUNTS}
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}
