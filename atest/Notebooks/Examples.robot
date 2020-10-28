*** Settings ***
Resource          ../_resources/keywords/Browser.robot
Resource          ../_resources/keywords/Lab.robot
Resource          ../_resources/keywords/IPyElk.robot

*** Variables ***
${SCREENS}        ${SCREENS ROOT}${/}notebooks

*** Test Cases ***
#    TODO:
#    - as these get filled in, they should be migrated to standalone `.robot` files
#    in this directory.
#    - common keywords, variables should move into `../_resources/*/IPyElk.robot`
00_Introduction
    Example Should Restart-and-Run-All    ${INTRODUCTION}
    [Teardown]    Clean up after Example    ${INTRODUCTION}

01_Linking
    Example Should Restart-and-Run-All    ${LINKING}
    [Teardown]    Clean up after Example    ${LINKING}

02_Transformer
    Example Should Restart-and-Run-All    ${TRANSFORMER}
    [Teardown]    Clean up after Example    ${TRANSFORMER}

03_App
    Example Should Restart-and-Run-All    ${APP}
    [Teardown]    Clean up after Example    ${APP}

04_Interactive
    Example Should Restart-and-Run-All    ${INTERACTIVE}
    [Teardown]    Clean up after Example    ${INTERACTIVE}

100_node_label_placement
    Example Should Restart-and-Run-All    ${LABEL PLACEMENT}
    [Teardown]    Clean up after Example    ${LABEL PLACEMENT}

101_text_sizer
    Example Should Restart-and-Run-All    ${TEXT SIZER}
    [Teardown]    Clean up after Example    ${TEXT SIZER}

102_layout_options
    Example Should Restart-and-Run-All    ${LAYOUT OPTIONS}
    [Teardown]    Clean up after Example    ${LAYOUT OPTIONS}

103_transformer_layout_options
    Example Should Restart-and-Run-All    ${TX LAYOUT OPTIONS}
    [Teardown]    Clean up after Example    ${TX LAYOUT OPTIONS}
