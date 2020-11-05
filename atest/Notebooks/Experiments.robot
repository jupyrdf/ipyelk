*** Settings ***
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot
Test Teardown     Clean up after IPyElk Example

*** Variables ***
${SCREENS}        ${SCREENS ROOT}${/}notebook-experiments

*** Test Cases ***
#    TODO:
#    - as these get filled in, they should be migrated to standalone `.robot` files
#    in this directory.
#    - common keywords, variables should move into `../_resources/*/IPyElk.robot`
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

104_transformer_multi_label
    Example Should Restart-and-Run-All    ${TX MULTI LABEL}
    Elk Counts Should Be
    ...    nodes=${1}
    ...    labels=${4}

105_transformer_ports
    Example Should Restart-and-Run-All    ${TX PORTS}
    Elk Counts Should Be
    ...    nodes=${1}
    ...    labels=${4}
    ...    ports=${2}

106_transformer_edges
    Example Should Restart-and-Run-All    ${TX EDGES}
    Elk Counts Should Be
    ...    nodes=${2}
    ...    edges=${1}
    ...    labels=${5}
