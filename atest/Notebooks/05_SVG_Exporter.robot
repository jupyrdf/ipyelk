*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}05_SVG_Exporter


*** Test Cases ***
05_SVG_Exporter
    [Tags]    data:simple.json    feature:svg
    Example Should Restart-and-Run-All    ${EXPORTER}
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Exported SVG should be valid XML    untitled_example.svg
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}
