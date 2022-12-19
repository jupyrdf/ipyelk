*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}02_Transformer


*** Test Cases ***
02_Transformer
    [Tags]    data:flat_graph.json    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${TRANSFORMER}
    Elk Counts Should Be    &{FLAT AND HIER COUNTS}
    Linked Elk Output Counts Should Be    &{FLAT COUNTS}
    Custom Elk Selectors Should Exist    @{FLAT CUSTOM}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}
