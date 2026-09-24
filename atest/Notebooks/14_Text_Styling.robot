*** Settings ***
Resource            ../_resources/keywords/Browser.robot
Resource            ../_resources/keywords/Lab.robot
Resource            ../_resources/keywords/IPyElk.robot
Library             Collections

Test Teardown       Clean up after IPyElk Example


*** Variables ***
${SCREENS}      ${SCREENS ROOT}${/}examples${/}14_Text_Styling


*** Test Cases ***
14_Text_Styling
    [Tags]    gh:100
    Example Should Restart-and-Run-All    ${TEXT STYLE}
    Wait Until Computed Element Styles Are    5x    1s    .jp-ElkView text.elklabel    fontWeight=700
