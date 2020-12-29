*** Settings ***
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot
Test Teardown     Clean up after IPyElk Example
Library           Collections

*** Variables ***
${SCREENS}        ${SCREENS ROOT}${/}notebook-examples

*** Test Cases ***
#    TODO:
#    - as these get filled in, they should be migrated to standalone `.robot` files
#    in this directory.
#    - common keywords, variables should move into `../_resources/*/IPyElk.robot`
00_Introduction
    [Tags]    data:simple.json    gh:6
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}

01_Linking
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${LINKING}
    ${counts} =    Create Dictionary    n=${2}    &{SIMPLE COUNTS}
    Elk Counts Should Be    &{counts}
    Linked Elk Output Counts Should Be    &{counts}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}

02_Transformer
    [Tags]    data:flat_graph.json    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${TRANSFORMER}
    Elk Counts Should Be    &{FLAT AND HIER COUNTS}
    Linked Elk Output Counts Should Be    &{FLAT COUNTS}
    Custom Elk Selectors Should Exist    @{FLAT CUSTOM}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}

03_App
    [Tags]    data:hier_tree.json    data:hier_ports.json    foo:bar
    Example Should Restart-and-Run-All    ${APP}
    Elk Counts Should Be    n=${5}    &{HIER COUNTS}
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}

04_Interactive
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    # not worth counting anything, as is basically non-deterministic

05_SVG_Exporter
    [Tags]    data:simple.json    feature:svg
    Example Should Restart-and-Run-All    ${EXPORTER}
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Exported SVG should be valid XML    untitled_example.svg
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}
    Custom Elk Selectors Should Exist    @{SIMPLE CUSTOM}

06_SVG_App_Exporter
    [Tags]    data:hier_tree.json    data:hier_ports.json    feature:svg
    Example Should Restart-and-Run-All    ${APP EXPORTER}
    Elk Counts Should Be    &{HIER COUNTS}
    Exported SVG should be valid XML    untitled_stylish_example.svg
    Linked Elk Output Counts Should Be    &{HIER COUNTS}
    Custom Elk Selectors Should Exist    @{HIER PORT CUSTOM}

07_Simulation
    Example Should Restart-and-Run-All    ${SIM PLUMBING}
    # not worth counting anything, as is basically non-deterministic

08_Simulation_App
    [Tags]    gh:48
    Example Should Restart-and-Run-All    ${SIM APP}
    # not worth counting anything, as is basically non-deterministic
    Computed Element Style Should Be    rect.elknode    stroke=rgba(0, 0, 0, 0)
    Computed Element Style Should Be    .down path    strokeDasharray=4px    stroke=rgb(255, 0, 0)
    Computed Element Style Should Be    .sprotty-edge    fontWeight=700
