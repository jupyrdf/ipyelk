*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}06_SVG_App_Exporter


*** Test Cases ***
06_SVG_App_Exporter
    [Tags]    data:hier_tree.json    data:hier_ports.json    feature:svg
    Example Should Restart-and-Run-All    ${APP EXPORTER}
    Elk Counts Should Be    &{HIER COUNTS}
    Exported SVG should be valid XML    untitled_stylish_example.svg
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}
