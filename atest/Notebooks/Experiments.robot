*** Settings ***
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot
Test Teardown     Clean up after IPyElk Example
Library           Collections

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
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}

101_text_sizer
    Example Should Restart-and-Run-All    ${TEXT SIZER}
    # not worth counting anything, doesn't put any elks on page

102_layout_options
    [Tags]    data:simple.json
    Example Should Restart-and-Run-All    ${LAYOUT OPTIONS}
    Elk Counts Should Be    &{SIMPLE COUNTS}
    Linked Elk Output Counts Should Be    &{SIMPLE COUNTS}

103_transformer_layout_options
    [Tags]    data:flat_graph.json    data:hier_tree.json    data:hier_ports.json
    Example Should Restart-and-Run-All    ${TX LAYOUT OPTIONS}
    Elk Counts Should Be    &{FLAT AND HIER COUNTS}
    Linked Elk Output Counts Should Be    &{FLAT COUNTS}

104_transformer_multi_label
    Example Should Restart-and-Run-All    ${TX MULTI LABEL}
    ${counts} =    Create Dictionary
    ...    nodes=${1}
    ...    labels=${4}
    Elk Counts Should Be    &{counts}
    Linked Elk Output Counts Should Be    &{counts}

105_transformer_ports
    Example Should Restart-and-Run-All    ${TX PORTS}
    ${counts} =    Create Dictionary
    ...    nodes=${1}
    ...    labels=${5}
    ...    ports=${2}
    Elk Counts Should Be    &{counts}
    Linked Elk Output Counts Should Be    &{counts}

106_transformer_edges
    Example Should Restart-and-Run-All    ${TX EDGES}
    ${counts} =    Create Dictionary
    ...    nodes=${2}
    ...    edges=${1}
    ...    labels=${5}
    Elk Counts Should Be    &{counts}
    Linked Elk Output Counts Should Be    &{counts}
