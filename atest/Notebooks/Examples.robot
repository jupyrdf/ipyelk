*** Settings ***
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot
Test Teardown     Clean up after IPyElk Example

*** Variables ***
${SCREENS}        ${SCREENS ROOT}${/}notebooks

*** Test Cases ***
#    TODO:
#    - as these get filled in, they should be migrated to standalone `.robot` files
#    in this directory.
#    - common keywords, variables should move into `../_resources/*/IPyElk.robot`
00_Introduction
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    Elk Counts Should Be
    ...    nodes=${SIMPLE NODE COUNT}
    ...    edges=${SIMPLE EDGE COUNT}
    ...    labels=${SIMPLE LABEL COUNT}

01_Linking
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${LINKING}
    Elk Counts Should Be
    ...    nodes=${SIMPLE NODE COUNT}
    ...    edges=${SIMPLE EDGE COUNT}
    ...    labels=${SIMPLE LABEL COUNT}
    ...    n=${2}

02_Transformer
    [Tags]    data:flat_graph.json    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${TRANSFORMER}
    Elk Counts Should Be
    ...    nodes=${FLAT NODE COUNT.__add__(${HIER NODE COUNT})}
    ...    edges=${FLAT EDGE COUNT.__add__(${HIER EDGE COUNT})}
    ...    labels=${FLAT LABEL COUNT.__add__(${HIER LABEL COUNT})}
    ...    ports=${HIER PORT COUNT}

03_App
    [Tags]    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${APP}
    Elk Counts Should Be
    ...    nodes=${HIER NODE COUNT}
    ...    edges=${HIER EDGE COUNT}
    ...    labels=${HIER LABEL COUNT}
    ...    ports=${HIER PORT COUNT}
    ...    n=${5}

04_Interactive
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    # not worth counting anything, as is basically non-deterministic

05_SVG_Exporter
    [Tags]    data:simple.json    feature:svg
    Example Should Restart-and-Run-All    ${EXPORTER}
    Elk Counts Should Be
    ...    nodes=${SIMPLE NODE COUNT}
    ...    edges=${SIMPLE EDGE COUNT}
    ...    labels=${SIMPLE LABEL COUNT}
    Exported SVG should be valid XML    untitled_example.svg

06_SVG_App_Exporter
    [Tags]    data:hier_tree.json    data:hier_ports.json    feature:svg
    Example Should Restart-and-Run-All    ${APP EXPORTER}
    Elk Counts Should Be
    ...    nodes=${HIER NODE COUNT}
    ...    edges=${HIER EDGE COUNT}
    ...    labels=${HIER LABEL COUNT}
    ...    ports=${HIER PORT COUNT}
    Exported SVG should be valid XML    untitled_stylish_example.svg

100_node_label_placement
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${LABEL PLACEMENT}
    Elk Counts Should Be
    ...    nodes=${SIMPLE NODE COUNT}
    ...    edges=${SIMPLE EDGE COUNT}
    ...    labels=${SIMPLE LABEL COUNT}

101_text_sizer
    Example Should Restart-and-Run-All    ${TEXT SIZER}
    # not worth counting anything, doesn't put any elks on page

102_layout_options
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${LAYOUT OPTIONS}
    Elk Counts Should Be
    ...    nodes=${SIMPLE NODE COUNT}
    ...    edges=${SIMPLE EDGE COUNT}
    ...    labels=${SIMPLE LABEL COUNT}

103_transformer_layout_options
    [Tags]    data:flat_graph.json    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${TX LAYOUT OPTIONS}
    Elk Counts Should Be
    ...    nodes=${FLAT NODE COUNT.__add__(${HIER NODE COUNT})}
    ...    edges=${FLAT EDGE COUNT.__add__(${HIER EDGE COUNT})}
    ...    labels=${FLAT LABEL COUNT.__add__(${HIER LABEL COUNT})}
    ...    ports=${HIER PORT COUNT}
